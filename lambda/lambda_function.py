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
    
    # Check if this is a test invocation
    test_mode = event.get('test', False)
    if test_mode:
        print("Running in test mode - report will be generated and sent")
    
    # Get metrics for all configurations
    report_data = {}
    for config_name in config.get('mediatailor_configs', []):
        metrics = get_mediatailor_metrics(config_name, config.get('metrics', []))
        report_data[config_name] = metrics
    
    # Generate PDF and send email
    pdf_data = generate_pdf_report(report_data)
    send_email_with_pdf(pdf_data, config.get('recipients', []))
    
    return {
        'statusCode': 200, 
        'body': 'Report sent successfully',
        'reportData': report_data
    }

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
            'average': round(weighted_fill_rate, 1),
            'sum': round(weighted_fill_rate, 1)
        }
        
        # Add validation note if there's a significant discrepancy
        if 'Avail.FillRate' in metric_data:
            avg_fill_rate_percent = metric_data['Avail.FillRate']['average'] * 100
            if abs(avg_fill_rate_percent - weighted_fill_rate) > 20:
                print(f"WARNING: Large discrepancy between average fill rate ({avg_fill_rate_percent:.1f}%) and weighted fill rate ({weighted_fill_rate:.1f}%)")
    
    return derived

def generate_pdf_report(report_data: Dict) -> bytes:
    """Generate PDF report"""
    
    from io import BytesIO
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter, 
        topMargin=1*inch, 
        bottomMargin=0.75*inch,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch
    )
    styles = getSampleStyleSheet()
    story = []
    
    # Professional header with proper spacing
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#6C757D'),
        alignment=2,  # Right align
        spaceAfter=20
    )
    
    header = Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p UTC')}", header_style)
    story.append(header)
    story.append(Spacer(1, 0.2*inch))
    
    # Main title with professional styling
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=22,
        textColor=colors.HexColor('#232F3E'),
        alignment=1,  # Center
        spaceAfter=12,
        borderWidth=2,
        borderColor=colors.HexColor('#FF9900'),
        borderPadding=12,
        backColor=colors.HexColor('#F8F9FA')
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#6C757D'),
        alignment=1,  # Center
        spaceAfter=20
    )
    
    title = Paragraph("MediaTailor Daily Report", title_style)
    subtitle = Paragraph(f"Performance Metrics for {datetime.now().strftime('%A, %B %d, %Y')}", subtitle_style)
    
    story.append(title)
    story.append(Spacer(1, 0.15*inch))
    story.append(subtitle)
    story.append(Spacer(1, 0.25*inch))
    
    # Executive summary if multiple configurations
    if len(report_data) > 1:
        summary_style = ParagraphStyle(
            'Summary',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#495057'),
            leftIndent=20,
            rightIndent=20,
            spaceAfter=15,
            borderWidth=1,
            borderColor=colors.HexColor('#E5E5E5'),
            borderPadding=10,
            backColor=colors.HexColor('#F8F9FA')
        )
        
        summary_text = f"This report covers {len(report_data)} MediaTailor configuration(s). Each section provides detailed metrics including fill rates, ad duration statistics, and system health indicators."
        summary = Paragraph(summary_text, summary_style)
        story.append(summary)
        story.append(Spacer(1, 0.2*inch))
    
    # Generate sections for each configuration
    for i, (config_name, metrics) in enumerate(report_data.items()):
        if i > 0:  # Add page break between configurations if multiple
            story.append(Spacer(1, 0.3*inch))
        
        story.extend(generate_pdf_config_section(config_name, metrics, styles))
        
        if i < len(report_data) - 1:  # Not the last configuration
            story.append(Spacer(1, 0.25*inch))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#6C757D'),
        alignment=1  # Center
    )
    
    story.append(Spacer(1, 0.3*inch))
    footer = Paragraph("AWS MediaTailor Monitoring System | Confidential", footer_style)
    story.append(footer)
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def generate_pdf_config_section(config_name: str, metrics: Dict, styles) -> List:
    """Generate PDF section for each configuration"""
    
    elements = []
    
    # Configuration header with professional styling
    config_style = ParagraphStyle(
        'ConfigHeader',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#232F3E'),
        spaceAfter=12,
        borderWidth=1,
        borderColor=colors.HexColor('#E5E5E5'),
        borderPadding=8,
        backColor=colors.HexColor('#F8F9FA')
    )
    
    elements.append(Paragraph(f"Configuration: {config_name}", config_style))
    elements.append(Spacer(1, 0.15*inch))
    
    # Metric descriptions with clearer explanations
    metric_descriptions = {
        'Avail.FillRate (Avg)': 'Simple average fill rate percentage for individual ad avails',
        'Avail.FillRate (Weighted)': 'Weighted average fill rate: (FilledDuration/Duration) × 100',
        'Avail.Duration': 'Planned ad avail time from origin manifest',
        'Avail.FilledDuration': 'Actual duration of ad breaks that were filled with ads',
        'AdDecisionServer.FillRate': 'Simple average of fill rate percentages returned by ADS',
        'AdDecisionServer.Ads': 'Number of ads returned by ADS',
        'AdDecisionServer.Duration': 'Total duration of ads returned by ADS',
        'AdDecisionServer.Latency': 'Response time in milliseconds for requests MediaTailor makes to ADS',
        'AdDecisionServer.Errors': 'Number of non-HTTP 200, empty, and timed-out responses from ADS',
        'AdDecisionServer.Timeouts': 'Number of timed-out requests to ADS',
        'Session.Duration': 'Total session time',
        'Avail.Impression': 'Number of ad impressions (increments when first segment requested)',
        'Avail.ObservedDuration': 'Actual duration of ad avails that occurred based on manifest segments',
        'Avail.ExpectedDuration': 'Expected ad break duration',
        'GetManifest.Errors': 'Number of errors while MediaTailor was generating manifests',
        'Origin.Errors': 'Origin server connectivity problems'
    }
    
    # Create table data with wrapped descriptions
    table_data = [['Metric', 'Description', 'Value', 'Status']]
    
    # Process metrics in logical relationship order
    metric_order = [
        # Duration metrics (foundation)
        'Avail.Duration', 'Avail.ObservedDuration', 'Avail.FilledDuration',
        # Fill rate metrics (calculated from durations)
        'Avail.FillRate (Avg)', 'Avail.FillRate (Weighted)',
        # ADS performance (affects fill rates)
        'AdDecisionServer.FillRate', 'AdDecisionServer.Ads', 'AdDecisionServer.Duration', 'AdDecisionServer.Latency',
        # ADS errors (root cause analysis)
        'AdDecisionServer.Errors', 'AdDecisionServer.Timeouts',
        # Delivery metrics
        'Avail.Impression',
        # System errors (infrastructure)
        'GetManifest.Errors', 'Origin.Errors'
    ]
    
    # Rename Avail.FillRate to Avail.FillRate (Avg) for display
    display_metrics = {}
    for metric, data in metrics.items():
        if metric == 'Avail.FillRate':
            display_metrics['Avail.FillRate (Avg)'] = data
        else:
            display_metrics[metric] = data
    
    # Define metric types
    RATE_METRICS = ['Avail.FillRate (Avg)', 'Avail.FillRate (Weighted)', 'AdDecisionServer.FillRate']
    DURATION_METRICS = ['Avail.Duration', 'Avail.FilledDuration', 'Avail.ObservedDuration', 'AdDecisionServer.Duration']
    LATENCY_METRICS = ['AdDecisionServer.Latency']
    COUNT_METRICS = ['AdDecisionServer.Ads', 'AdDecisionServer.Errors', 'AdDecisionServer.Timeouts', 'Avail.Impression', 'GetManifest.Errors', 'Origin.Errors']
    
    for metric in metric_order:
        if metric not in display_metrics:
            continue
            
        data = display_metrics[metric]
        
        if 'error' in data:
            error_desc = Paragraph(f"Error: {data['error'][:50]}...", styles['Normal'])
            table_data.append([metric, metric_descriptions.get(metric, ''), error_desc, "Error"])
            continue
            
        # Format value based on metric type
        avg = data.get('average', 0)
        sum_val = data.get('sum', 0)
        
        if metric in RATE_METRICS:
            # CloudWatch returns fill rates as decimals (0.74 = 74%)
            if metric in ['Avail.FillRate (Avg)', 'AdDecisionServer.FillRate']:
                display_value = avg * 100  # Convert decimal to percentage
                value = f"{display_value:.1f}%"
            else:
                # Weighted fill rate is already calculated as percentage
                value = f"{avg:.1f}%"
        elif metric in LATENCY_METRICS:
            # ADS latency in milliseconds
            value = f"{avg:.0f}ms"
        elif metric in DURATION_METRICS:
            # Convert milliseconds to more appropriate units
            if metric == 'AdDecisionServer.Duration':
                # ADS duration is total ad content duration, not latency
                seconds = sum_val / 1000
                if seconds >= 3600:
                    hours = seconds / 3600
                    value = f"{hours:.1f}h ({seconds/60:.0f}min)"
                elif seconds >= 60:
                    value = f"{seconds/60:.1f}min"
                else:
                    value = f"{seconds:.1f}s"
            else:
                # Other durations - convert from milliseconds
                seconds = sum_val / 1000
                if seconds >= 3600:
                    hours = seconds / 3600
                    value = f"{hours:.1f}h ({seconds/60:.0f}min)"
                elif seconds >= 60:
                    value = f"{seconds/60:.1f}min"
                else:
                    value = f"{seconds:.1f}s"
        elif metric in COUNT_METRICS:
            # Format count metrics appropriately
            if sum_val >= 1000000:
                value = f"{sum_val/1000000:.1f}M"
            elif sum_val >= 1000:
                value = f"{sum_val/1000:.1f}K"
            else:
                value = f"{int(sum_val)}"
        else:
            value = str(avg)
        
        # Status determination with better logic
        status_text = "✓ Good"
        
        if 'FillRate' in metric:
            # Adjust thresholds based on metric type
            if metric in ['Avail.FillRate (Avg)', 'AdDecisionServer.FillRate']:
                # These are decimal values from CloudWatch (0.74 = 74%)
                rate_percent = avg * 100
            else:
                # Weighted fill rate is already a percentage
                rate_percent = avg
                
            if rate_percent == 0:
                status_text = "⚪ No Data"
            elif rate_percent < 70:
                status_text = "🔴 Critical"
            elif rate_percent < 85:
                status_text = "🟡 Low"
        elif metric in LATENCY_METRICS:
            if avg == 0:
                status_text = "⚪ No Data"
            elif avg > 500:
                status_text = "🔴 High Latency"
            elif avg > 300:
                status_text = "🟡 Slow Response"
        elif metric in DURATION_METRICS:
            if sum_val == 0:
                status_text = "⚪ No Data"
            elif metric == 'AdDecisionServer.Duration':
                # ADS duration is ad content duration - compare with available inventory
                ads_duration_sec = sum_val / 1000
                avail_duration_sec = display_metrics.get('Avail.Duration', {}).get('sum', 0) / 1000
                if avail_duration_sec > 0 and ads_duration_sec > avail_duration_sec * 1.5:
                    status_text = "🟡 High Ad Volume"
            elif metric == 'Avail.Duration':
                seconds = sum_val / 1000 if metric != 'AdDecisionServer.Duration' else avg / 1000
                if seconds > 7200:  # >2 hours seems high
                    status_text = "🟡 High Volume"
        elif metric in COUNT_METRICS:
            if sum_val == 0:
                status_text = "⚪ No Data"
            elif 'Errors' in metric and sum_val > 100:
                status_text = "🔴 High Errors"
            elif 'Timeouts' in metric and sum_val > 50:
                status_text = "🟡 Timeouts"
        
        # Add data validation warnings for suspicious values
        if metric == 'Avail.FillRate (Avg)' and 'Avail.FillRate (Weighted)' in display_metrics:
            # Convert avg fill rate to percentage for comparison
            avg_rate_percent = avg * 100
            weighted_rate = display_metrics['Avail.FillRate (Weighted)'].get('average', 0)
            
            # Check for large discrepancy between average and weighted rates
            if abs(avg_rate_percent - weighted_rate) > 20:  # >20% difference suggests data issue
                status_text = "⚠️ Check Data"
        elif metric == 'AdDecisionServer.Ads' and sum_val == 0 and 'Avail.Impression' in display_metrics:
            impressions = display_metrics['Avail.Impression'].get('sum', 0)
            if impressions > 0:  # Impressions without ADS ads suggests issue
                status_text = "⚠️ Check ADS"
        
        # Wrap description in Paragraph for better formatting
        description = Paragraph(metric_descriptions.get(metric, ''), styles['Normal'])
        table_data.append([metric, description, value, status_text])
    
    # Create table with optimized column widths to prevent overflow
    table = Table(table_data, colWidths=[1.8*inch, 2.8*inch, 1.2*inch, 1.2*inch])
    
    # Professional table styling
    table_style = [
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#232F3E')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        
        # Body styling
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E5E5')),
        ('OUTLINE', (0, 0), (-1, -1), 1, colors.HexColor('#232F3E')),
        
        # Value column alignment
        ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
        ('ALIGN', (3, 1), (3, -1), 'CENTER'),
    ]
    
    # Add color coding for status column with better styling
    for i, row in enumerate(table_data[1:], 1):  # Skip header row
        status = row[3]
        if "Good" in status:
            table_style.append(('TEXTCOLOR', (3, i), (3, i), colors.HexColor('#28A745')))
            table_style.append(('FONTNAME', (3, i), (3, i), 'Helvetica-Bold'))
        elif "Low" in status:
            table_style.append(('TEXTCOLOR', (3, i), (3, i), colors.HexColor('#FFC107')))
            table_style.append(('FONTNAME', (3, i), (3, i), 'Helvetica-Bold'))
        elif "Critical" in status:
            table_style.append(('TEXTCOLOR', (3, i), (3, i), colors.HexColor('#DC3545')))
            table_style.append(('FONTNAME', (3, i), (3, i), 'Helvetica-Bold'))
        elif "No Data" in status:
            table_style.append(('TEXTCOLOR', (3, i), (3, i), colors.HexColor('#6C757D')))
        elif "Error" in status:
            table_style.append(('TEXTCOLOR', (3, i), (3, i), colors.HexColor('#DC3545')))
            table_style.append(('FONTNAME', (3, i), (3, i), 'Helvetica-Bold'))
    
    table.setStyle(TableStyle(table_style))
    
    elements.append(table)
    
    return elements



def send_email_with_pdf(pdf_data: bytes, recipients: List[str]):
    """Send email with PDF attachment via SES"""
    
    if not recipients:
        print("No recipients configured")
        return
    
    # Load configuration
    config = json.loads(os.environ.get('REPORT_CONFIG', '{}'))
    sender_email = config.get('sender_email', f"noreply@{recipients[0].split('@')[1]}")
    
    try:
        # Create multipart message
        msg = MIMEMultipart()
        msg['Subject'] = f'MediaTailor Daily Report - {datetime.now().strftime("%Y-%m-%d")}'
        msg['From'] = f"MediaTailor Reports <{sender_email}>"
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
        
        # Send via SES using configured sender
        ses.send_raw_email(
            Source=sender_email,
            Destinations=recipients,
            RawMessage={'Data': msg.as_string()}
        )
        
        print(f"PDF report sent to {recipients}")
    except Exception as e:
        print(f"Error sending email: {e}")
        raise

