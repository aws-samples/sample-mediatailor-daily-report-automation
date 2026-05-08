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
from botocore.config import Config

# Initialize AWS clients at module level for Lambda container reuse
# Adaptive retry mode handles throttling and transient errors automatically
boto_config = Config(retries={'max_attempts': 3, 'mode': 'adaptive'})
cloudwatch = boto3.client('cloudwatch', config=boto_config)
ses = boto3.client('ses', config=boto_config)

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
        send_email_with_pdf(pdf_data, config.get('recipients', []), logger, ses, sender_email=config.get('sender_email'))
        
        logger.info("Report generation completed successfully")
        
        response = {
            'statusCode': 200, 
            'body': 'Report sent successfully',
            'configCount': len(report_data),
            'recipientCount': len(config.get('recipients', []))
        }
        
        # Include report data only in test mode for validation
        if test_mode:
            response['reportData'] = report_data
        
        return response
    
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
    
    # Calculate derived metrics (only if explicitly requested in config)
    derived_metrics = calculate_derived_metrics(metric_data, metrics, logger, config_name)
    metric_data.update(derived_metrics)
    
    return metric_data

def calculate_derived_metrics(metric_data: Dict, requested_metrics: List[str], logger, config_name: str) -> Dict:
    """Calculate weighted fill rates and observed fill rate.

    Only calculates derived metrics if they are explicitly requested in the config.
    This prevents auto-calculation of fill rates for workflows where they're not relevant
    (e.g., direct campaigns without programmatic backfill).

    Args:
        metric_data: Dictionary of fetched CloudWatch metrics
        requested_metrics: List of metrics explicitly requested in config.json
        logger: Logger instance
        config_name: MediaTailor configuration name

    Returns:
        Dictionary of calculated derived metrics (only those requested)
    """

    derived_metrics = {}

    try:
        # Calculate Avail.FillRate (weighted - override simple average from CloudWatch)
        # Only calculate if explicitly requested in config
        has_duration = 'Avail.Duration' in metric_data
        has_filled_duration = 'Avail.FilledDuration' in metric_data
        duration_sum = metric_data.get('Avail.Duration', {}).get('sum', 0)
        fill_rate_requested = 'Avail.FillRate' in requested_metrics

        if fill_rate_requested and has_duration and has_filled_duration and duration_sum > 0:
            total_duration = metric_data['Avail.Duration']['sum']
            filled_duration = metric_data['Avail.FilledDuration']['sum']
            
            # Validate data before calculation
            if total_duration <= 0:
                logger.warning("Invalid total duration for weighted fill rate calculation", extra={
                    "config_name": config_name,
                    "total_duration": total_duration,
                    "filled_duration": filled_duration
                })
            else:
                # Override Avail.FillRate with weighted calculation
                weighted_avail_fill_rate = (filled_duration / total_duration) * 100
                derived_metrics['Avail.FillRate'] = {
                    'average': round(weighted_avail_fill_rate, 1),
                    'sum': round(weighted_avail_fill_rate, 1)
                }

                logger.debug("Calculated weighted Avail.FillRate", extra={
                    "total_duration": total_duration,
                    "filled_duration": filled_duration,
                    "weighted_fill_rate": weighted_avail_fill_rate
                })
        
        # Calculate AdDecisionServer.FillRate (weighted)
        # Only calculate if explicitly requested in config
        has_ads_duration = 'AdDecisionServer.Duration' in metric_data
        ads_fill_rate_requested = 'AdDecisionServer.FillRate' in requested_metrics

        if ads_fill_rate_requested and has_duration and has_ads_duration and duration_sum > 0:
            total_duration = metric_data['Avail.Duration']['sum']
            ads_duration = metric_data['AdDecisionServer.Duration']['sum']
            
            if total_duration > 0:
                # Override AdDecisionServer.FillRate with weighted calculation
                weighted_ads_fill_rate = (ads_duration / total_duration) * 100
                derived_metrics['AdDecisionServer.FillRate'] = {
                    'average': round(weighted_ads_fill_rate, 1),
                    'sum': round(weighted_ads_fill_rate, 1)
                }

                logger.debug("Calculated weighted AdDecisionServer.FillRate", extra={
                    "total_duration": total_duration,
                    "ads_duration": ads_duration,
                    "weighted_fill_rate": weighted_ads_fill_rate
                })
        
        # Calculate Avail.ObservedFillRate (works for both HLS and DASH)
        # Only calculate if explicitly requested in config
        has_observed_duration = 'Avail.ObservedDuration' in metric_data
        has_observed_filled = 'Avail.ObservedFilledDuration' in metric_data
        observed_duration_sum = metric_data.get('Avail.ObservedDuration', {}).get('sum', 0)
        observed_fill_rate_requested = 'Avail.ObservedFillRate' in requested_metrics

        if observed_fill_rate_requested and has_observed_duration and has_observed_filled and observed_duration_sum > 0:
            observed_duration = metric_data['Avail.ObservedDuration']['sum']
            observed_filled_duration = metric_data['Avail.ObservedFilledDuration']['sum']
            
            if observed_duration > 0:
                observed_fill_rate = (observed_filled_duration / observed_duration) * 100
                derived_metrics['Avail.ObservedFillRate'] = {
                    'average': round(observed_fill_rate, 1),
                    'sum': round(observed_fill_rate, 1)
                }
                
                logger.debug("Calculated Avail.ObservedFillRate", extra={
                    "observed_duration": observed_duration,
                    "observed_filled_duration": observed_filled_duration,
                    "observed_fill_rate": observed_fill_rate
                })
        elif observed_fill_rate_requested:
            # Only log if metric was requested but couldn't be calculated
            logger.debug("Insufficient data for observed fill rate calculation", extra={
                "config_name": config_name,
                "has_observed_duration": has_observed_duration,
                "has_observed_filled": has_observed_filled,
                "observed_duration_sum": observed_duration_sum
            })
    
    except Exception as e:
        logger.error("Failed to calculate derived metrics", extra={
            "config_name": config_name,
            "error": str(e)
        }, exc_info=True)
    
    return derived_metrics

def calculate_config_status(metrics: Dict) -> tuple:
    """Calculate overall status for a configuration.

    Returns:
        tuple: (status_level, status_text, issue_count)
            status_level: 0=Healthy, 1=Info, 2=Warning, 3=Critical, 4=No Data
            status_text: Human-readable status
            issue_count: Number of warning/critical metrics
    """

    critical_count = 0
    warning_count = 0
    has_data = False

    # Metrics that should trigger status (not informational)
    STATUS_METRICS = [
        'Avail.FillRate', 'AdDecisionServer.FillRate', 'Avail.ObservedFillRate',
        'AdDecisionServer.Latency', 'GetManifest.Latency',
        'AdDecisionServer.Errors', 'AdDecisionServer.Timeouts',
        'GetManifest.Errors', 'Origin.Errors', 'Origin.Timeouts'
    ]

    for metric_name, data in metrics.items():
        if metric_name not in STATUS_METRICS:
            continue

        if 'error' in data:
            continue

        avg = data.get('average', 0)
        sum_val = data.get('sum', 0)

        if avg > 0 or sum_val > 0:
            has_data = True

        # Check fill rates
        if 'FillRate' in metric_name:
            if avg == 0:
                continue  # No data
            elif avg < 70:
                critical_count += 1
            elif avg < 80:
                warning_count += 1

        # Check latencies
        elif metric_name == 'AdDecisionServer.Latency':
            if avg == 0:
                continue
            elif avg > 2000:
                critical_count += 1
            elif avg > 1000:
                warning_count += 1

        elif metric_name == 'GetManifest.Latency':
            if avg == 0:
                continue
            elif avg > 500:
                critical_count += 1
            elif avg > 200:
                warning_count += 1

        # Check error counts
        elif 'Errors' in metric_name or 'Timeouts' in metric_name:
            if sum_val == 0:
                continue
            elif sum_val >= 1000:
                critical_count += 1
            elif sum_val >= 100:
                warning_count += 1

    # Determine overall status
    if not has_data:
        return (4, "⚪ No Data", 0)
    elif critical_count > 0:
        return (3, f"🔴 Critical ({critical_count})", critical_count)
    elif warning_count > 0:
        return (2, f"🟡 Warning ({warning_count})", warning_count)
    else:
        return (0, "✓ Healthy", 0)

def generate_pdf_report(report_data: Dict, start_time, end_time) -> bytes:
    """Generate PDF report with executive summary for large deployments.

    For deployments with many channels (>10), generates:
    - Page 1: Executive summary table showing all channels with overall status
    - Following pages: Detailed metrics only for channels with issues (Warning/Critical)
    - Healthy channels: Summary only (no detailed tables)

    This keeps reports actionable and manageable even with 100+ channels.
    """

    from io import BytesIO
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter, 
        topMargin=1*inch, 
        bottomMargin=0.75*inch,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch,
        title='MediaTailor Daily Report',
        author='AWS MediaTailor Monitoring',
        subject='Daily Ad-Fill Rate Metrics Report'
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

    # Calculate status for all configs
    config_statuses = {}
    for config_name, metrics in report_data.items():
        status_level, status_text, issue_count = calculate_config_status(metrics)
        config_statuses[config_name] = {
            'level': status_level,
            'text': status_text,
            'issues': issue_count
        }

    # Executive summary for large deployments (>10 channels)
    if len(report_data) > 10:
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

        critical_count = sum(1 for s in config_statuses.values() if s['level'] == 3)
        warning_count = sum(1 for s in config_statuses.values() if s['level'] == 2)
        healthy_count = sum(1 for s in config_statuses.values() if s['level'] == 0)

        summary_text = (f"<b>Executive Summary:</b> {len(report_data)} channels monitored. "
                       f"{critical_count} critical, {warning_count} warnings, {healthy_count} healthy. "
                       f"Detailed metrics shown below for channels with issues.")
        summary = Paragraph(summary_text, summary_style)
        story.append(summary)
        story.append(Spacer(1, 0.15*inch))

        # Executive summary table
        exec_header_style = ParagraphStyle(
            'ExecHeader',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#232F3E'),
            spaceAfter=8
        )
        story.append(Paragraph("Channel Status Overview", exec_header_style))

        # Build summary table
        exec_table_data = [['Channel', 'Status', 'Issues']]
        for config_name in sorted(config_statuses.keys(), key=lambda x: (-config_statuses[x]['level'], x)):
            status_info = config_statuses[config_name]
            exec_table_data.append([
                config_name,
                status_info['text'],
                str(status_info['issues']) if status_info['issues'] > 0 else '-'
            ])

        exec_table = Table(exec_table_data, colWidths=[3*inch, 1.5*inch, 1*inch])
        exec_table_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#232F3E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E5E5')),
        ]

        # Color-code status column
        for i, row in enumerate(exec_table_data[1:], 1):
            status = row[1]
            if "Critical" in status:
                exec_table_style.append(('TEXTCOLOR', (1, i), (1, i), colors.HexColor('#DC3545')))
            elif "Warning" in status:
                exec_table_style.append(('TEXTCOLOR', (1, i), (1, i), colors.HexColor('#FFC107')))
            elif "Healthy" in status:
                exec_table_style.append(('TEXTCOLOR', (1, i), (1, i), colors.HexColor('#28A745')))

        exec_table.setStyle(TableStyle(exec_table_style))
        story.append(exec_table)
        story.append(Spacer(1, 0.25*inch))

    elif len(report_data) > 1:
        # Brief summary for small deployments
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

    # For large deployments, show detailed metrics only for channels with issues
    show_all_details = len(report_data) <= 10

    if not show_all_details:
        detail_header_style = ParagraphStyle(
            'DetailHeader',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#232F3E'),
            spaceAfter=10,
            spaceBefore=10
        )
        story.append(Paragraph("Detailed Metrics (Issues Only)", detail_header_style))

        note_style = ParagraphStyle(
            'Note',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#6C757D'),
            leftIndent=10,
            spaceAfter=15
        )
        story.append(Paragraph(
            "For readability, only channels with warnings or critical issues are shown below. "
            "Healthy channels are listed in the summary table above.",
            note_style
        ))

    # Generate sections for each configuration
    configs_shown = 0
    for config_name, metrics in sorted(report_data.items(), key=lambda x: -config_statuses[x[0]]['level']):
        status_info = config_statuses[config_name]

        # For large deployments, skip healthy channels in details
        if not show_all_details and status_info['level'] == 0:
            continue

        if configs_shown > 0:
            story.append(Spacer(1, 0.3*inch))

        story.extend(generate_pdf_config_section(config_name, metrics, styles, status_info['text']))
        configs_shown += 1
        
        if i < len(report_data) - 1:
            story.append(Spacer(1, 0.25*inch))
    
    # Footnote about locally calculated metrics
    footnote_style = ParagraphStyle(
        'Footnote',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.HexColor('#6C757D'),
        leftIndent=10,
        rightIndent=10,
        spaceBefore=10,
        spaceAfter=5,
        borderWidth=0.5,
        borderColor=colors.HexColor('#E5E5E5'),
        borderPadding=6,
        backColor=colors.HexColor('#F8F9FA')
    )
    footnote_text = (
        "Note: Fill rate metrics (Avail.FillRate, AdDecisionServer.FillRate, Avail.ObservedFillRate) use weighted "
        "(sum-based) calculations for revenue accuracy: (total filled duration ÷ total duration) × 100. This differs "
        "from CloudWatch's simple per-avail averages. Avail.ObservedFillRate is calculated locally from CloudWatch "
        "component metrics to support both HLS and DASH (CloudWatch only emits it for HLS at CUE-IN). "
        "For detailed metric definitions, see: https://docs.aws.amazon.com/mediatailor/latest/ug/monitoring-cloudwatch-metrics.html"
    )
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(footnote_text, footnote_style))

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

def generate_pdf_config_section(config_name: str, metrics: Dict, styles, overall_status: str = None) -> List:
    """Generate PDF section for each configuration"""

    elements = []

    # Configuration header with professional styling and status
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

    header_text = f"Configuration: {config_name}"
    if overall_status:
        header_text += f"  —  {overall_status}"

    elements.append(Paragraph(header_text, config_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Define metric groups organized by troubleshooting scenario
    # Groups are displayed in order, with inline descriptions for context
    metric_groups = {
        'Ad Decision Server Health': {
            'description': 'Your ad server responsiveness and error rates. High latency (>1000ms) or errors indicate ADS configuration or network issues.',
            'metrics': [
                'AdDecisionServer.Latency',
                'AdDecisionServer.Errors',
                'AdDecisionServer.Timeouts',
                'AdDecisionServer.Ads'
            ]
        },
        'Ad Insertion Performance': {
            'description': 'Fill rate and duration metrics showing how effectively ads are being inserted into breaks.',
            'metrics': [
                'Avail.FillRate',
                'AdDecisionServer.FillRate',
                'Avail.Duration',
                'Avail.FilledDuration',
                'AdDecisionServer.Duration'
            ]
        },
        'Manifest Generation': {
            'description': 'Performance metrics for manifest personalization. High latency (>200ms) affects playback startup time.',
            'metrics': [
                'GetManifest.Latency',
                'GetManifest.Errors'
            ]
        },
        'Origin Server Health': {
            'description': 'Content origin server connectivity and performance. Errors indicate origin availability issues.',
            'metrics': [
                'Origin.Errors',
                'Origin.Timeouts'
            ]
        },
        'Observed Playback Metrics': {
            'description': 'Actual playback behavior vs. planned. Differences indicate early CUE-IN (common in live content).',
            'metrics': [
                'Avail.ObservedDuration',
                'Avail.ObservedFilledDuration',
                'Avail.ObservedFillRate'
            ]
        },
        'Volume & Impression Metrics': {
            'description': 'Informational metrics showing ad impression counts and total ad volume.',
            'metrics': [
                'Avail.Impression'
            ]
        }
    }
    
    # Use metrics as-is (no renaming needed)
    display_metrics = metrics
    
    # Define metric types
    RATE_METRICS = ['Avail.FillRate', 'AdDecisionServer.FillRate', 'Avail.ObservedFillRate']
    DURATION_METRICS = ['Avail.Duration', 'Avail.FilledDuration', 'Avail.ObservedDuration', 'Avail.ObservedFilledDuration', 'AdDecisionServer.Duration']
    LATENCY_METRICS = ['AdDecisionServer.Latency', 'GetManifest.Latency']
    COUNT_METRICS = ['AdDecisionServer.Ads', 'AdDecisionServer.Errors', 'AdDecisionServer.Timeouts', 'Avail.Impression', 'GetManifest.Errors', 'Origin.Errors', 'Origin.Timeouts']
    
    # Generate tables for each metric group (only show groups with metrics present)
    for group_name, group_config in metric_groups.items():
        metric_list = group_config['metrics']
        group_description = group_config['description']

        # Check if any metrics in this group are present in the data
        has_metrics = any(metric in display_metrics for metric in metric_list)
        if not has_metrics:
            continue  # Skip empty groups

        # Group header
        group_style = ParagraphStyle(
            'GroupHeader',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#495057'),
            spaceAfter=4,
            spaceBefore=12
        )
        elements.append(Paragraph(group_name, group_style))

        # Group description (inline context)
        desc_style = ParagraphStyle(
            'GroupDesc',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#6C757D'),
            spaceAfter=8,
            leftIndent=10
        )
        elements.append(Paragraph(group_description, desc_style))

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
                # All fill rate metrics are now percentages (weighted calculations)
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
            
            # Status determination with simplified categories
            status_text = "✓ Healthy"
            
            if metric in ['Avail.FillRate', 'AdDecisionServer.FillRate', 'Avail.ObservedFillRate']:
                # Fill rate metrics - these should be high (70-100%)
                rate_percent = avg
                    
                if rate_percent == 0:
                    status_text = "⚪ No Data"
                elif rate_percent < 70:
                    status_text = "🔴 Critical"
                elif rate_percent < 80:
                    status_text = "🟡 Warning"
                # else: ✓ Healthy (default)
            elif metric in DURATION_METRICS or metric == 'Avail.Impression':
                # Duration and volume metrics are informational only
                if sum_val == 0:
                    status_text = "⚪ No Data"
                else:
                    status_text = "ℹ️ Info"
            elif metric in LATENCY_METRICS:
                if avg == 0:
                    status_text = "⚪ No Data"
                elif metric == 'AdDecisionServer.Latency':
                    # ADS timeout is 3s; AWS recommends <1000ms
                    if avg > 2000:
                        status_text = "🔴 Critical"
                    elif avg > 1000:
                        status_text = "🟡 Warning"
                    # else: ✓ Healthy (default)
                elif metric == 'GetManifest.Latency':
                    # AWS recommends <200ms for manifest generation
                    if avg > 500:
                        status_text = "🔴 Critical"
                    elif avg > 200:
                        status_text = "🟡 Warning"
                    # else: ✓ Healthy (default)
            elif metric in ['AdDecisionServer.Errors', 'AdDecisionServer.Timeouts', 
                           'GetManifest.Errors', 'Origin.Errors', 'Origin.Timeouts']:
                # All error metrics use absolute thresholds
                if sum_val == 0:
                    status_text = "⚪ No Data"
                elif sum_val >= 1000:
                    status_text = "🔴 Critical"
                elif sum_val >= 100:
                    status_text = "🟡 Warning"
                # else: ✓ Healthy (default)
            elif metric == 'AdDecisionServer.Ads':
                # Volume metric is informational only
                if sum_val == 0:
                    status_text = "⚪ No Data"
                else:
                    status_text = "ℹ️ Info"
            
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
            
            # Add status colors for simplified categories
            for i, row in enumerate(table_data[1:], 1):
                status = row[2]
                if "Healthy" in status:
                    table_style.append(('TEXTCOLOR', (2, i), (2, i), colors.HexColor('#28A745')))
                elif "Info" in status:
                    table_style.append(('TEXTCOLOR', (2, i), (2, i), colors.HexColor('#17A2B8')))
                elif "Warning" in status:
                    table_style.append(('TEXTCOLOR', (2, i), (2, i), colors.HexColor('#FFC107')))
                elif "Critical" in status:
                    table_style.append(('TEXTCOLOR', (2, i), (2, i), colors.HexColor('#DC3545')))
                elif "No Data" in status:
                    table_style.append(('TEXTCOLOR', (2, i), (2, i), colors.HexColor('#6C757D')))
            
            table.setStyle(TableStyle(table_style))
            elements.append(table)
            elements.append(Spacer(1, 0.15*inch))
    
    return elements


def send_email_with_pdf(pdf_data: bytes, recipients: List[str], logger, ses_client, sender_email: str = None):
    """Send email with PDF attachment via SES"""
    
    if not recipients:
        logger.warning("No recipients configured for email")
        return
    
    # Use provided sender_email or fall back to deriving from recipients
    if not sender_email:
        if recipients and '@' in recipients[0]:
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
        logger.warning("Email sending failed, propagating error", extra={"recipient_count": len(recipients), "error": str(e)})
        raise Exception(f"Failed to send email to {len(recipients)} recipient(s): {str(e)}") from e

