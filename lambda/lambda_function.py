import json
import boto3
import os
import logging
import traceback
from datetime import datetime, timedelta, timezone
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

class CorrelationFilter(logging.Filter):
    """Logging filter that adds correlation ID to all log records."""
    
    def __init__(self, correlation_id: str) -> None:
        super().__init__()
        self.correlation_id = correlation_id
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = self.correlation_id
        return True

# Setup structured logging
def setup_logging(correlation_id=None):
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    logger = logging.getLogger()
    
    # Validate log level
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if log_level not in valid_levels:
        log_level = 'INFO'
    
    try:
        numeric_level = getattr(logging, log_level.upper())
        if not isinstance(numeric_level, int):
            raise AttributeError("Invalid log level")
        logger.setLevel(numeric_level)
    except (AttributeError, TypeError):
        logger.setLevel(logging.INFO)
    
    # Add correlation filter if provided
    if correlation_id:
        # Remove existing correlation filters to prevent accumulation
        logger.filters = [f for f in logger.filters if not isinstance(f, CorrelationFilter)]
        logger.addFilter(CorrelationFilter(correlation_id))
    
    # Reduce AWS SDK noise
    if log_level != 'DEBUG':
        boto3_logger = logging.getLogger('boto3')
        botocore_logger = logging.getLogger('botocore')
        boto3_logger.setLevel(logging.WARNING)
        botocore_logger.setLevel(logging.WARNING)
    
    return logger

def lambda_handler(event, context):
    """Main Lambda handler for MediaTailor daily report"""
    
    # Setup logging with correlation ID
    correlation_id = context.aws_request_id
    logger = setup_logging(correlation_id)
    
    # Initialize AWS clients with error handling
    try:
        global cloudwatch, ses
        cloudwatch = boto3.client('cloudwatch')
        ses = boto3.client('ses')
    except Exception as e:
        logger.error("Failed to initialize AWS clients", extra={"error": str(e)}, exc_info=True)
        return {'statusCode': 500, 'body': 'AWS client initialization failed'}
    
    # Sanitize event source to prevent log injection
    event_source = 'unknown'
    if event and isinstance(event, dict) and 'source' in event:
        raw_source = str(event['source'])[:50]
        # Remove potentially dangerous characters
        event_source = ''.join(c for c in raw_source if c.isalnum() or c in '.-_')
        if not event_source:
            event_source = 'sanitized'
    
    logger.info("Lambda function invoked", extra={
        "function_name": context.function_name,
        "log_level": os.environ.get('LOG_LEVEL', 'INFO'),
        "event_source": event_source
    })
    
    logger.info("Report generation started", extra={
        "function_name": context.function_name,
        "memory_limit": context.memory_limit_in_mb,
        "remaining_time_ms": context.get_remaining_time_in_millis(),
        "event_keys": list(event.keys()) if event else []
    })
    
    try:
        # Load configuration
        config_str = os.environ.get('REPORT_CONFIG', '{}')
        if len(config_str) > 10000:  # Prevent excessive config size
            raise ValueError("Configuration too large")
        logger.debug("Loading configuration from environment", extra={"config_length": len(config_str)})
        
        try:
            config = json.loads(config_str)
            if not isinstance(config, dict):
                raise ValueError("Configuration must be a JSON object")
        except json.JSONDecodeError:
            raise ValueError("Invalid configuration JSON")
        logger.info("Configuration loaded", extra={
            "config_count": len(config.get('mediatailor_configs', [])),
            "recipient_count": len(config.get('recipients', []))
        })
        
        # Validate configuration
        if not config.get('mediatailor_configs'):
            logger.warning("No MediaTailor configurations found")
        if not config.get('recipients'):
            logger.warning("No email recipients configured")
        
        # Check if this is a test invocation
        test_mode = event.get('test', False)
        if test_mode:
            logger.info("Running in test mode")
    
        # Calculate reporting period once
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=1)
    
        # Get metrics for all configurations
        report_data = {}
        mediatailor_configs = config.get('mediatailor_configs', [])
        if not isinstance(mediatailor_configs, list):
            raise ValueError("mediatailor_configs must be a list")
        
        for config_name in mediatailor_configs:
            if not isinstance(config_name, str) or len(config_name) > 100:
                logger.warning("Skipping invalid config name", extra={"config_type": type(config_name).__name__})
                continue
            # Sanitize config name
            safe_config_name = ''.join(c for c in config_name if c.isalnum() or c in '.-_')
            if not safe_config_name:
                logger.warning("Skipping config with invalid characters")
                continue
            
            logger.info("Processing configuration", extra={"config_name": safe_config_name})
            metrics = get_mediatailor_metrics(safe_config_name, config.get('metrics', []), logger, cloudwatch, start_time, end_time)
            report_data[safe_config_name] = metrics
        
        # Generate PDF and send email
        logger.info("Generating PDF report")
        pdf_data = generate_pdf_report(report_data, start_time, end_time)
        
        logger.info("Sending email report", extra={
            "recipient_count": len(config.get('recipients', []))
        })
        send_email_with_pdf(pdf_data, config.get('recipients', []), logger, ses)
        
        logger.info("Report generation completed successfully")
        return {
            'statusCode': 200, 
            'body': 'Report sent successfully',
            'reportData': report_data
        }
    
    except json.JSONDecodeError as e:
        logger.error("Invalid configuration JSON", extra={"error": str(e)}, exc_info=True)
        return {'statusCode': 500, 'body': 'Configuration error'}
    except KeyError as e:
        logger.error("Missing configuration key", extra={"key": str(e)}, exc_info=True)
        return {'statusCode': 500, 'body': 'Configuration error'}
    except Exception as e:
        logger.error("Report generation failed", extra={"error": str(e)}, exc_info=True)
        return {'statusCode': 500, 'body': 'Internal error'}

def get_mediatailor_metrics(config_name: str, metrics: List[str], logger, cloudwatch_client, start_time, end_time) -> Dict:
    """Query CloudWatch metrics for a MediaTailor configuration"""
    
    metric_data = {}
    
    for metric_name in metrics:
        try:
            response = cloudwatch_client.get_metric_statistics(
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
            
            if not isinstance(response, dict):
                raise ValueError(f"Invalid CloudWatch response type: {type(response)}")
            if 'Datapoints' not in response:
                raise KeyError(f"Missing 'Datapoints' in CloudWatch response for metric {metric_name}")
            
            if response['Datapoints']:
                datapoint = response['Datapoints'][0]
                # Don't round Sum for duration metrics to preserve precision for weighted calculations
                avg_value = datapoint.get('Average', 0)
                sum_value = datapoint.get('Sum', 0)
                
                metric_data[metric_name] = {
                    'average': round(avg_value, 2),
                    'sum': sum_value if metric_name in ['Avail.Duration', 'Avail.FilledDuration'] else round(sum_value, 2)
                }
            else:
                metric_data[metric_name] = {'average': 0, 'sum': 0}
                
        except Exception as e:
            logger.error("Failed to get metric", extra={
                "metric_name": metric_name,
                "config_name": config_name,
                "error": str(e)
            }, exc_info=True)
            metric_data[metric_name] = {'error': 'Data unavailable'}
    
    # Calculate derived metrics
    derived_metrics = calculate_derived_metrics(metric_data, logger, config_name)
    metric_data.update(derived_metrics)
    
    return metric_data

def calculate_derived_metrics(metric_data: Dict, logger, config_name: str) -> Dict:
    """Calculate weighted fill rate and return derived metrics"""
    
    derived_metrics = {}
    
    try:
        # Calculate Weighted Fill Rate (more accurate than simple average)
        has_duration = 'Avail.Duration' in metric_data
        has_filled_duration = 'Avail.FilledDuration' in metric_data
        duration_sum = metric_data.get('Avail.Duration', {}).get('sum', 0)
        
        if has_duration and has_filled_duration and duration_sum > 0:
            
            total_duration = metric_data['Avail.Duration']['sum']
            filled_duration = metric_data['Avail.FilledDuration']['sum']
            
            # Validate data before calculation
            if total_duration <= 0:
                logger.warning("Invalid total duration for weighted fill rate calculation", extra={
                    "config_name": config_name,
                    "total_duration": total_duration,
                    "filled_duration": filled_duration
                })
                return derived_metrics
            
            weighted_fill_rate = (filled_duration / total_duration) * 100
            
            derived_metrics['Avail.FillRate (Weighted)'] = {
                'average': round(weighted_fill_rate, 1),
                'sum': round(weighted_fill_rate, 1)
            }
            
            logger.debug("Calculated weighted fill rate", extra={
                "total_duration": total_duration,
                "filled_duration": filled_duration,
                "weighted_fill_rate": weighted_fill_rate
            })
            
            # Add validation note if there's a significant discrepancy
            if 'Avail.FillRate' in metric_data and metric_data['Avail.FillRate'].get('average') is not None:
                avg_fill_rate_percent = metric_data['Avail.FillRate']['average'] * 100
                discrepancy = abs(avg_fill_rate_percent - weighted_fill_rate)
                
                if discrepancy > 20:
                    logger.warning("Large fill rate discrepancy detected", extra={
                        "config_name": config_name,
                        "avg_fill_rate_percent": avg_fill_rate_percent,
                        "weighted_fill_rate": weighted_fill_rate,
                        "discrepancy": discrepancy
                    })
        else:
            logger.debug("Insufficient data for weighted fill rate calculation", extra={
                "has_duration": 'Avail.Duration' in metric_data,
                "has_filled_duration": 'Avail.FilledDuration' in metric_data,
                "duration_sum": metric_data.get('Avail.Duration', {}).get('sum', 0)
            })
    
    except Exception as e:
        logger.error("Failed to calculate derived metrics", extra={
            "config_name": config_name,
            "error": str(e)
        }, exc_info=True)
    
    return derived_metrics

def generate_pdf_report(report_data: Dict, start_time, end_time) -> bytes:
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
        
        summary_text = ("This report covers " + f"{len(report_data)}" + " MediaTailor "
                        "configuration(s). Each section provides detailed metrics "
                        "including fill rates, ad duration statistics, and system "
                        "health indicators.")
        summary = Paragraph(summary_text, summary_style)
        story.append(summary)
        story.append(Spacer(1, 0.2*inch))
    
    # Single reporting period statement
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
    
    date_format = '%B %d, %Y %H:%M UTC'
    period_text = (f"24-Hour Report: {start_time.strftime(date_format)} "
                   f"to {end_time.strftime(date_format)}")
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
    if 'Avail.FillRate' in metrics:
        display_metrics = metrics.copy()
        display_metrics['Avail.FillRate (Avg)'] = display_metrics.pop('Avail.FillRate')
    else:
        display_metrics = metrics
    
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
                if metric == 'Avail.FillRate (Avg)':
                    # Avail.FillRate is a decimal (0.99 = 99%)
                    display_value = avg * 100
                    value = f"{display_value:.1f}%"
                else:
                    # AdDecisionServer.FillRate and Weighted are already percentages
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
            
            if metric == 'Avail.FillRate (Avg)' or metric == 'Avail.FillRate (Weighted)':
                # Avail.FillRate metrics - these should be high (70-100%)
                if metric == 'Avail.FillRate (Avg)':
                    rate_percent = avg * 100
                else:
                    rate_percent = avg
                    
                if rate_percent == 0:
                    status_text = "■ No Data"
                elif rate_percent < 70:
                    status_text = "🔴 Critical"
                elif rate_percent < 80:
                    status_text = "🟡 Low"
            elif metric == 'AdDecisionServer.FillRate':
                # AdDecisionServer.FillRate - informational only, no status thresholds
                if avg == 0:
                    status_text = "■ No Data"
            elif metric in DURATION_METRICS:
                if sum_val == 0:
                    status_text = "■ No Data"
            elif metric in LATENCY_METRICS:
                if avg == 0:
                    status_text = "■ No Data"
                elif avg > 500:
                    status_text = "🔴 High Latency"
                elif avg > 300:
                    status_text = "🟡 Slow Response"
            elif metric in COUNT_METRICS:
                if sum_val == 0:
                    status_text = "■ No Data"
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
    """Generate metrics descriptions table for bottom of PDF.
    
    Args:
        styles: ReportLab StyleSheet object containing paragraph styles
                for formatting the table content
    
    Returns:
        List: List of ReportLab elements (Paragraph and Table) that make up
              the metrics definitions section of the PDF report
    """
    
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
    
    # Create descriptions table with optimized performance
    normal_style = styles['Normal']  # Cache style lookup
    table_data = [['Metric', 'Description']] + [
        [metric, Paragraph(description, normal_style)]
        for metric, description in metric_descriptions.items()
    ]
    
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

def send_email_with_pdf(pdf_data: bytes, recipients: List[str], logger, ses_client):
    """Send email with PDF attachment via SES"""
    
    if not recipients:
        logger.warning("No recipients configured for email")
        return
    
    # Load configuration
    config = json.loads(os.environ.get('REPORT_CONFIG', '{}'))
    
    # Safer fallback for sender email
    if 'sender_email' in config:
        sender_email = config['sender_email']
    elif recipients and '@' in recipients[0]:
        sender_email = f"noreply@{recipients[0].split('@')[1]}"
    else:
        sender_email = "noreply@example.com"
    
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
        ses_client.send_raw_email(
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
            "recipient_count": len(recipients),
            "error": str(e)
        }, exc_info=True)
        raise

