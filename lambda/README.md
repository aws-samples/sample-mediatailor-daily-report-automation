# MediaTailor Report Lambda Function

This Lambda function generates daily PDF reports for AWS MediaTailor ad fill rate metrics and sends them via email.

## Overview

The function is triggered daily by EventBridge and performs the following operations:
1. Queries CloudWatch for MediaTailor metrics
2. Processes and calculates derived metrics
3. Generates a PDF report with AWS design system
4. Sends the report via Amazon SES

## Files

- `lambda_function.py` - Main Lambda handler and business logic
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container configuration for Lambda

## Dependencies

### Core Libraries
- `boto3` - AWS SDK for Python
- `reportlab` - PDF generation library

### Email Libraries
- `email.mime.multipart` - Email composition
- `email.mime.text` - Text email content
- `email.mime.application` - PDF attachments

## Function Structure

### Main Handler
```python
lambda_handler(event, context)
```
- Entry point for Lambda execution
- Loads configuration from environment variables
- Orchestrates the report generation process

### Core Functions

#### `get_mediatailor_metrics(config_name, metrics)`
- Queries CloudWatch for MediaTailor metrics
- Retrieves 24-hour aggregated data
- Returns structured metric data with averages and sums

#### `calculate_derived_metrics(metric_data)`
- Calculates weighted fill rate
- Formula: (Avail.FilledDuration / Avail.Duration) × 100
- More accurate than simple average fill rate

#### `generate_pdf_report(report_data)`
- Creates PDF using ReportLab library
- Implements AWS CloudScape design colors
- Generates tables with metric descriptions and status indicators

#### `send_email_with_pdf(pdf_data, recipients)`
- Composes multipart MIME email
- Attaches PDF report
- Sends via Amazon SES

## Configuration

The function reads configuration from the `REPORT_CONFIG` environment variable:

```json
{
  "mediatailor_configs": ["config-1", "config-2"],
  "metrics": [
    "Avail.FillRate",
    "Avail.Duration", 
    "Avail.FilledDuration",
    "AdDecisionServer.FillRate"
  ],
  "recipients": ["email@example.com"],
  "schedule": {
    "hour": "16",
    "minute": "0"
  }
}
```

## Metrics Processing

### Supported Metrics
- **Avail.FillRate**: Average fill rate across all ad avails (%)
- **Avail.Duration**: Total planned ad time (milliseconds)
- **Avail.FilledDuration**: Total filled ad time (milliseconds)
- **AdDecisionServer.FillRate**: Fill rate from Ad Decision Server (%)

### Calculated Metrics
- **Avail.FillRate (Weighted)**: Duration-weighted fill rate for more accurate reporting

### Metric Display Order
1. Avail.FillRate (Avg)
2. Avail.FillRate (Weighted)
3. Avail.Duration
4. Avail.FilledDuration
5. AdDecisionServer.FillRate

## PDF Report Features

### Design System
- AWS CloudScape color scheme
- Professional table formatting
- Status indicators (✅ Good, ⚠️ Low, ❌ Critical)

### Content Structure
- Report header with date
- Configuration sections
- Summary cards for key metrics
- Detailed metrics table with descriptions

### Status Logic
- **Good**: Fill rate ≥ 80%
- **Low**: Fill rate < 80%
- **Critical**: Fill rate < 70%

## Error Handling

### CloudWatch API Errors
- Graceful handling of missing metrics
- Error logging for debugging
- Continues processing other configurations

### Email Delivery Errors
- SES error handling and logging
- Detailed error messages for troubleshooting

### PDF Generation Errors
- ReportLab exception handling
- Fallback error reporting

## Testing

### Test Mode
The function supports a test mode when invoked with `{"test": true}`:
- Enables additional logging
- Returns metric data in response
- Useful for debugging and validation

### Manual Testing Methods

#### 1. Basic Function Test
```bash
# Test report generation and email delivery
aws lambda invoke --function-name MediaTailorReportStack-MediaTailorReportFunction output.json
```

#### 2. Debug Mode Test
```bash
# Test with additional logging and response data
aws lambda invoke --function-name MediaTailorReportStack-MediaTailorReportFunction \
  --payload '{"test": true}' output.json
```

#### 3. Configuration Validation Test
```bash
# Test specific configuration
aws lambda invoke --function-name MediaTailorReportStack-MediaTailorReportFunction \
  --payload '{"test": true, "config_override": ["specific-config"]}' output.json
```

### Test Scenarios

#### Single Configuration Test
- Update `config.json` with one MediaTailor config
- Run basic test to validate single config processing
- Verify PDF contains correct configuration data

#### Multiple Configuration Test
- Configure multiple MediaTailor configs
- Validate each config appears in report
- Check metric aggregation across configs

#### Error Handling Test
- Configure non-existent MediaTailor config
- Verify graceful error handling
- Ensure other configs still process correctly

### Validation Steps

1. **Function Execution**: Check `output.json` for success status
2. **CloudWatch Logs**: Review execution logs for errors
3. **Email Delivery**: Verify report received by recipients
4. **PDF Content**: Validate metrics, formatting, and calculations
5. **Metric Accuracy**: Compare with CloudWatch console data

## Monitoring

### CloudWatch Logs
- Function execution logs
- Error tracking and debugging
- Performance metrics

### Key Log Messages
- Configuration loading status
- Metric retrieval results
- PDF generation success/failure
- Email delivery confirmation

## Performance

### Resource Allocation
- **Memory**: 512 MB
- **Timeout**: 5 minutes
- **Runtime**: Python 3.9+ (Docker)

### Optimization
- Efficient CloudWatch API usage
- Minimal memory footprint for PDF generation
- Batch processing of multiple configurations

## Security

### IAM Permissions Required
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:ListMetrics"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow", 
      "Action": [
        "ses:SendEmail",
        "ses:SendRawEmail"
      ],
      "Resource": "arn:aws:ses:*:*:identity/*"
    }
  ]
}
```

### Data Handling
- No sensitive data stored in function
- Metrics data processed in memory only
- Email content encrypted in transit

## Troubleshooting

### Common Issues

#### No Metrics Data
- Verify MediaTailor configuration names
- Check CloudWatch metrics availability
- Ensure proper time range (24 hours)

#### Email Delivery Failures
- Verify SES email identity
- Check recipient email addresses
- Review SES sending limits

#### PDF Generation Errors
- Check ReportLab dependencies
- Verify memory allocation
- Review CloudWatch logs for details

### Debug Steps
1. Check CloudWatch logs for error messages
2. Verify configuration format and values
3. Test with simplified metric set
4. Validate SES setup and permissions

### Performance Testing

#### Load Testing
- Test with maximum number of MediaTailor configs
- Monitor Lambda memory usage and execution time
- Validate function completes within timeout

#### Metric Volume Testing
- Test with configs having high metric volumes
- Verify CloudWatch API rate limiting handling
- Check PDF generation performance

### Integration Testing

#### End-to-End Flow
1. MediaTailor generates metrics
2. CloudWatch stores metric data
3. EventBridge triggers Lambda
4. Lambda processes and generates report
5. SES delivers email successfully

#### Component Testing
- **CloudWatch Integration**: Verify metric retrieval
- **PDF Generation**: Test ReportLab functionality
- **Email Delivery**: Validate SES integration
- **Error Handling**: Test failure scenarios