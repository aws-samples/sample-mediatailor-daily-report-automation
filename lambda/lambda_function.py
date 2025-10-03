import json
import boto3
import os
import logging
import traceback
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

# Setup structured logging
def setup_logging(correlation_id: str):
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level))
    
    # Add correlation ID to all log records
    class CorrelationFilter(logging.Filter):
        def filter(self, record):
            record.correlation_id = correlation_id
            return True
    
    logger.addFilter(CorrelationFilter(correlation_id))
    
    # Reduce AWS SDK noise
    if log_level != 'DEBUG':
        logging.getLogger('boto3').setLevel(logging.WARNING)
        logging.getLogger('botocore').setLevel(logging.WARNING)
    
    return logger

cloudwatch = boto3.client('cloudwatch')
ses = boto3.client('ses')

def lambda_handler(event, context):
    """Main Lambda handler for MediaTailor daily report"""
    
    # Setup logging with correlation ID
    correlation_id = context.aws_request_id
    logger = setup_logging(correlation_id)
    
    logger.info("Report generation started", extra={
        "function_name": context.function_name,
        "memory_limit": context.memory_limit_in_mb
    })
    
    try:
        # Load configuration
        config = json.loads(os.environ.get('REPORT_CONFIG', '{}'))
        logger.info("Configuration loaded", extra={
            "config_count": len(config.get('mediatailor_configs', [])),
            "recipient_count": len(config.get('recipients', []))
        })
        
        # Check if this is a test invocation
        test_mode = event.get('test', False)
        if test_mode:
            logger.info("Running in test mode")
    
        # Get metrics for all configurations
        report_data = {}
        for config_name in config.get('mediatailor_configs', []):
            logger.info("Processing configuration", extra={"config_name": config_name})
            metrics = get_mediatailor_metrics(config_name, config.get('metrics', []), logger)
            report_data[config_name] = metrics
        
        # Generate PDF and send email
        logger.info("Generating PDF report")
        pdf_data = generate_pdf_report(report_data)
        
        logger.info("Sending email report", extra={"recipient_count": len(config.get('recipients', []))})
        send_email_with_pdf(pdf_data, config.get('recipients', []), logger)
        
        logger.info("Report generation completed successfully")
        return {
            'statusCode': 200, 
            'body': 'Report sent successfully',
            'reportData': report_data
        }
    
    except Exception as e:
        logger.error("Report generation failed", extra={
            "error": str(e),
            "stack_trace": traceback.format_exc()
        })
        raise

def get_mediatailor_metrics(config_name: str, metrics: List[str], logger) -> Dict:
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
            logger.error("Failed to get metric", extra={
                "metric_name": metric_name,
                "config_name": config_name,
                "error": str(e),
                "stack_trace": traceback.format_exc()
            })
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
                logging.getLogger().warning("Large fill rate discrepancy detected", extra={
                    "avg_fill_rate_percent": avg_fill_rate_percent,
                    "weighted_fill_rate": weighted_fill_rate,
                    "discrepancy": abs(avg_fill_rate_percent - weighted_fill_rate)
                })
    
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
    

    
    # Main title with professional styling
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#232F3E'),
        alignment=1,  # Center
        spaceAfter=10,
        borderWidth=2,
        borderColor=colors.HexColor('#FF9900'),
        borderPadding=10,
        backColor=colors.HexColor('#F8F9FA')
    )
    

    
    title = Paragraph("MediaTailor Daily Report", title_style)
    
    story.append(title)
    story.append(Spacer(1, 0.2*inch))
    
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
    
    # Single reporting period statement
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=1)
    
    period_style = ParagraphStyle(
        'Period',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#495057'),
        alignment=1,
        spaceAfter=20,
        borderWidth=1,
        borderColor=colors.HexColor('#E5E5E5'),
        borderPadding=10,
        backColor=colors.HexColor('#F8F9FA')
    )
    
    period_text = f"24-Hour Report: {start_time.strftime('%B %d, %Y %H:%M UTC')} to {end_time.strftime('%B %d, %Y %H:%M UTC')}"
    period = Paragraph(period_text, period_style)
    story.append(period)
    story.append(Spacer(1, 0.25*inch))
    
    # Generate sections for each configuration
    for i, (config_name, metrics) in enumerate(report_data.items()):
        if i > 0:
            story.append(Spacer(1, 0.3*inch))
        
        story.extend(generate_pdf_config_section(config_name, metrics, styles))
        
        if i < len(report_data) - 1:
            story.append(Spacer(1, 0.25*inch))
    
    # Add metrics descriptions at the bottom
    story.extend(generate_metrics_descriptions_table(styles))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#6C757D'),
        alignment=1  # Center
    )
    
    story.append(Spacer(1, 0.3*inch))
    footer = Paragraph("AWS Elemental MediaTailor Monitoring System | Confidential", footer_style)
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
        fontSize=14,
        textColor=colors.HexColor('#232F3E'),
        spaceAfter=10,
        borderWidth=1,
        borderColor=colors.HexColor('#E5E5E5'),
        borderPadding=6,
        backColor=colors.HexColor('#F8F9FA')
    )
    
    elements.append(Paragraph(f"Configuration: {config_name}", config_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Define metric groups by priority
    metric_groups = {
        'Critical Performance Metrics': [
            'Avail.FillRate (Avg)', 'Avail.FillRate (Weighted)', 
            'AdDecisionServer.FillRate', 'AdDecisionServer.Latency'
        ],
        'Volume & Duration Metrics': [
            'Avail.Duration', 'Avail.FilledDuration', 'Avail.Impression',
            'AdDecisionServer.Ads', 'AdDecisionServer.Duration'
        ],
        'Error & Health Metrics': [
            'AdDecisionServer.Errors', 'AdDecisionServer.Timeouts',
            'GetManifest.Errors', 'Origin.Errors'
        ]
    }
    
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
    
    # Generate tables for each metric group
    for group_name, metric_list in metric_groups.items():
        # Group header
        group_style = ParagraphStyle(
            'GroupHeader',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#495057'),
            spaceAfter=8,
            spaceBefore=12
        )
        elements.append(Paragraph(group_name, group_style))
        
        # Create table for this group
        table_data = [['Metric', 'Value', 'Status']]
        
        for metric in metric_list:
            if metric not in display_metrics:
                continue
                
            data = display_metrics[metric]
            
            if 'error' in data:
                table_data.append([metric, f"Error: {data['error'][:30]}...", "Error"])
                continue
                
            # Format value based on metric type
            avg = data.get('average', 0)
            sum_val = data.get('sum', 0)
            
            if metric in RATE_METRICS:
                if metric in ['Avail.FillRate (Avg)', 'AdDecisionServer.FillRate']:
                    display_value = avg * 100
                    value = f"{display_value:.1f}%"
                else:
                    value = f"{avg:.1f}%"
            elif metric in LATENCY_METRICS:
                value = f"{avg:.0f}ms"
            elif metric in DURATION_METRICS:
                seconds = sum_val / 1000
                if seconds >= 3600:
                    value = f"{seconds/3600:.1f}h"
                elif seconds >= 60:
                    value = f"{seconds/60:.1f}min"
                else:
                    value = f"{seconds:.1f}s"
            elif metric in COUNT_METRICS:
                if sum_val >= 1000000:
                    value = f"{sum_val/1000000:.1f}M"
                elif sum_val >= 1000:
                    value = f"{sum_val/1000:.1f}K"
                else:
                    value = f"{int(sum_val)}"
            else:
                value = str(avg)
            
            # Status determination
            status_text = "✓ Good"
            
            if 'FillRate' in metric:
                if metric in ['Avail.FillRate (Avg)', 'AdDecisionServer.FillRate']:
                    rate_percent = avg * 100
                else:
                    rate_percent = avg
                    
                if rate_percent == 0:
                    status_text = "⚪ No Data"
                elif rate_percent < 70:
                    status_text = "🔴 Critical"
                elif rate_percent < 80:
                    status_text = "🟡 Low"
            elif metric in LATENCY_METRICS:
                if avg == 0:
                    status_text = "⚪ No Data"
                elif avg > 500:
                    status_text = "🔴 High Latency"
                elif avg > 300:
                    status_text = "🟡 Slow Response"
            elif metric in COUNT_METRICS:
                if sum_val == 0:
                    status_text = "⚪ No Data"
                elif 'Errors' in metric and sum_val > 100:
                    status_text = "🔴 High Errors"
                elif 'Timeouts' in metric and sum_val > 50:
                    status_text = "🟡 Timeouts"
            
            table_data.append([metric, value, status_text])
        
        if len(table_data) > 1:  # Only create table if has data
            table = Table(table_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
            
            table_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#495057')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E5E5')),
                ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
                ('ALIGN', (2, 1), (2, -1), 'CENTER'),
            ]
            
            # Add status colors
            for i, row in enumerate(table_data[1:], 1):
                status = row[2]
                if "Good" in status:
                    table_style.append(('TEXTCOLOR', (2, i), (2, i), colors.HexColor('#28A745')))
                elif "Low" in status:
                    table_style.append(('TEXTCOLOR', (2, i), (2, i), colors.HexColor('#FFC107')))
                elif "Critical" in status:
                    table_style.append(('TEXTCOLOR', (2, i), (2, i), colors.HexColor('#DC3545')))
                elif "No Data" in status:
                    table_style.append(('TEXTCOLOR', (2, i), (2, i), colors.HexColor('#6C757D')))
            
            table.setStyle(TableStyle(table_style))
            elements.append(table)
            elements.append(Spacer(1, 0.15*inch))
    
    return elements

def generate_metrics_descriptions_table(styles) -> List:
    """Generate metrics descriptions table for bottom of PDF"""
    
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
        'Avail.Impression': 'Number of ad impressions (increments when first segment requested)',
        'GetManifest.Errors': 'Number of errors while MediaTailor was generating manifests',
        'Origin.Errors': 'Origin server connectivity problems'
    }
    
    elements = []
    
    # Section header
    header_style = ParagraphStyle(
        'DescHeader',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#232F3E'),
        spaceAfter=10,
        spaceBefore=20
    )
    elements.append(Paragraph("Metrics Definitions", header_style))
    
    # Create descriptions table
    table_data = [['Metric', 'Description']]
    
    for metric, description in metric_descriptions.items():
        desc_para = Paragraph(description, styles['Normal'])
        table_data.append([metric, desc_para])
    
    table = Table(table_data, colWidths=[2.2*inch, 4.3*inch])
    
    table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6C757D')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E5E5')),
    ]
    
    table.setStyle(TableStyle(table_style))
    elements.append(table)
    
    return elements



def send_email_with_pdf(pdf_data: bytes, recipients: List[str], logger):
    """Send email with PDF attachment via SES"""
    
    if not recipients:
        logger.warning("No recipients configured for email")
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
        
        logger.info("Email sent successfully", extra={
            "recipients": recipients,
            "sender": sender_email,
            "pdf_size_bytes": len(pdf_data)
        })
    except Exception as e:
        logger.error("Failed to send email", extra={
            "recipients": recipients,
            "sender": sender_email,
            "error": str(e),
            "stack_trace": traceback.format_exc()
        })
        raise

