import json
import boto3
import os
from datetime import datetime, timedelta
from typing import Dict, List
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

cloudwatch = boto3.client('cloudwatch')
ses = boto3.client('ses')

def lambda_handler(event, context):
    """Main Lambda handler for MediaTailor daily report"""
    
    # Load configuration
    config = json.loads(os.environ.get('REPORT_CONFIG', '{}'))
    
    # Get metrics for all configurations
    report_data = {}
    for config_name in config.get('mediatailor_configs', []):
        metrics = get_mediatailor_metrics(config_name, config.get('metrics', []))
        report_data[config_name] = metrics
    
    # Generate PDF and send email
    pdf_data = generate_pdf_report(report_data)
    send_email_with_pdf(pdf_data, config.get('recipients', []))
    
    return {'statusCode': 200, 'body': 'Report sent successfully'}

def get_mediatailor_metrics(config_name: str, metrics: List[str]) -> Dict:
    """Query CloudWatch metrics for a MediaTailor configuration"""
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=1)
    
    metric_data = {}
    
    for metric_name in metrics:
        try:
            response = cloudwatch.get_metric_statistics(
                Namespace='AWS/MediaTailor',
                MetricName=metric_name,
                Dimensions=[
                    {'Name': 'ConfigurationName', 'Value': config_name}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,  # 24 hours
                Statistics=['Average', 'Sum']
            )
            
            if response['Datapoints']:
                datapoint = response['Datapoints'][0]
                metric_data[metric_name] = {
                    'average': round(datapoint.get('Average', 0), 2),
                    'sum': round(datapoint.get('Sum', 0), 2)
                }
            else:
                metric_data[metric_name] = {'average': 0, 'sum': 0}
                
        except Exception as e:
            print(f"Error getting metric {metric_name} for {config_name}: {e}")
            metric_data[metric_name] = {'error': str(e)}
    
    # Calculate derived metrics
    metric_data.update(calculate_derived_metrics(metric_data))
    
    return metric_data

def calculate_derived_metrics(metric_data: Dict) -> Dict:
    """Calculate weighted fill rate"""
    
    derived = {}
    
    # Calculate Weighted Fill Rate (more accurate than simple average)
    if ('Avail.Duration' in metric_data and 'Avail.FilledDuration' in metric_data and 
        metric_data['Avail.Duration'].get('sum', 0) > 0):
        
        total_duration = metric_data['Avail.Duration']['sum']
        filled_duration = metric_data['Avail.FilledDuration']['sum']
        weighted_fill_rate = (filled_duration / total_duration) * 100
        
        derived['Avail.FillRate (Weighted)'] = {
            'average': round(weighted_fill_rate, 2),
            'sum': round(weighted_fill_rate, 2)
        }
    
    return derived

def generate_pdf_report(report_data: Dict) -> bytes:
    """Generate PDF report"""
    
    from io import BytesIO
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#232F3E'),
        alignment=1  # Center
    )
    
    title = Paragraph(f"MediaTailor Daily Report - {datetime.now().strftime('%Y-%m-%d')}", title_style)
    story.append(title)
    story.append(Spacer(1, 0.3*inch))
    
    # Generate sections for each configuration
    for config_name, metrics in report_data.items():
        story.extend(generate_pdf_config_section(config_name, metrics, styles))
        story.append(Spacer(1, 0.2*inch))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def generate_pdf_config_section(config_name: str, metrics: Dict, styles) -> List:
    """Generate PDF section for each configuration"""
    
    elements = []
    
    # Configuration header
    config_style = ParagraphStyle(
        'ConfigHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1976d2')
    )
    
    elements.append(Paragraph(f"Configuration: {config_name}", config_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Metric descriptions
    metric_descriptions = {
        'Avail.FillRate (Avg)': 'Average fill rate across all ad avails (%)',
        'Avail.FillRate (Weighted)': 'Duration-weighted fill rate - More accurate than simple average (%)',
        'Avail.Duration': 'Total planned ad time (milliseconds)',
        'Avail.FilledDuration': 'Total filled ad time (milliseconds)',
        'AdDecisionServer.FillRate': 'Fill rate from Ad Decision Server (%)',

    }
    
    # Create table data
    table_data = [['Metric', 'Description', 'Value', 'Status']]
    
    # Process metrics in specific order
    metric_order = ['Avail.FillRate', 'Avail.FillRate (Weighted)', 'Avail.Duration', 'Avail.FilledDuration', 'AdDecisionServer.FillRate']
    
    # Rename Avail.FillRate to Avail.FillRate (Avg) for display
    display_metrics = {}
    for metric, data in metrics.items():
        if metric == 'Avail.FillRate':
            display_metrics['Avail.FillRate (Avg)'] = data
        else:
            display_metrics[metric] = data
    
    for metric in metric_order:
        if metric not in display_metrics:
            continue
            
        data = display_metrics[metric]
        
        if 'error' in data:
            table_data.append([metric, metric_descriptions.get(metric, ''), f"Error: {data['error']}", "❌ Error"])
            continue
            
        # Format value based on metric type
        RATE_METRICS = ['Avail.FillRate (Avg)', 'Avail.FillRate (Weighted)', 'AdDecisionServer.FillRate']
        DURATION_METRICS = ['Avail.Duration', 'Avail.FilledDuration']
        
        avg = data.get('average', 0)
        sum_val = data.get('sum', 0)
        
        if metric in RATE_METRICS:
            value = f"{avg}%"
        elif metric in DURATION_METRICS:
            value = f"{sum_val:,.0f} ms"
        else:
            value = str(avg)
        
        # Status
        status = "✅ Good"
        if 'FillRate' in metric and avg < 80:
            status = "⚠️ Low"
        elif 'FillRate' in metric and avg < 70:
            status = "❌ Critical"
        
        description = metric_descriptions.get(metric, '')
        table_data.append([metric, description, value, status])
    
    # Create and style table
    table = Table(table_data, colWidths=[2*inch, 2.5*inch, 1*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    return elements



def send_email_with_pdf(pdf_data: bytes, recipients: List[str]):
    """Send email with PDF attachment via SES"""
    
    if not recipients:
        print("No recipients configured")
        return
    
    try:
        # Create multipart message
        msg = MIMEMultipart()
        msg['Subject'] = f'MediaTailor Daily Report - {datetime.now().strftime("%Y-%m-%d")}'
        msg['From'] = os.environ.get('FROM_EMAIL')
        msg['To'] = ', '.join(recipients)
        
        # Email body
        body = f"""
        Please find attached the MediaTailor Daily Report for {datetime.now().strftime("%Y-%m-%d")}.
        
        This report contains:
        - Fill rate performance metrics
        - Error rate analysis
        - Traffic volume statistics
        - System health indicators
        
        Best regards,
        MediaTailor Monitoring System
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach PDF
        pdf_attachment = MIMEApplication(pdf_data, _subtype='pdf')
        pdf_attachment.add_header('Content-Disposition', 'attachment', 
                                filename=f'mediatailor-report-{datetime.now().strftime("%Y-%m-%d")}.pdf')
        msg.attach(pdf_attachment)
        
        # Send via SES
        ses.send_raw_email(
            Source=os.environ.get('FROM_EMAIL'),
            Destinations=recipients,
            RawMessage={'Data': msg.as_string()}
        )
        
        print(f"PDF report sent to {recipients}")
    except Exception as e:
        print(f"Error sending email: {e}")
        raise