# MediaTailor Daily Report

Automated daily email reports for MediaTailor ad-fill rate metrics.

## Key Features

✅ **Config-Driven Metrics** - Only calculate and display metrics you explicitly configure (no unwanted alerts)  
✅ **Scales to 200+ Channels** - Executive summary + issues-only filtering keeps reports manageable  
✅ **Smart Alerting** - Configurable thresholds based on AWS recommendations and industry standards  
✅ **Workflow-Specific** - Pre-configured metric sets for different ad delivery patterns  
✅ **Comprehensive Docs** - Threshold rationale, troubleshooting workflows, and scaling best practices

## Quick Start

1. **Install CDK**: `npm install -g aws-cdk`
2. **Update Configuration**: Copy `config/config.json.example` to `config/config.json` and edit with your settings
3. **Deploy**: Run `./deploy.sh up` or `./deploy.sh up --region us-east-1`
4. **Verify Email**: Check your sender email inbox and click the AWS SES verification link

## Documentation

### Getting Started
- [📖 Installation Guide](docs/INSTALLATION_GUIDE.md) - Complete installation and setup instructions
- [📋 Configuration Guide](docs/CONFIGURATION.md) - Setup and configuration options

### Understanding Metrics & Alerts
- [📊 Metrics Reference](docs/METRICS.md) - Available metrics and their meanings
- [🎯 Thresholds Guide](docs/THRESHOLDS_GUIDE.md) - Why these alert thresholds? (NEW)
- [🔧 Troubleshooting Workflows](docs/TROUBLESHOOTING_WORKFLOWS.md) - Metric configs by scenario (NEW)

### Scaling & Performance
- [📈 Scaling Guide](docs/SCALING_GUIDE.md) - Managing 100+ channels efficiently (NEW)
- [📋 Executive Summary Example](docs/EXECUTIVE_SUMMARY_EXAMPLE.md) - Visual examples (NEW)

### Advanced
- [🧪 Testing Guide](docs/TESTING.md) - How to test the system
- [🏗️ Architecture](docs/ARCHITECTURE.md) - System architecture details
- [🔒 Security](docs/SECURITY.md) - Security measures and best practices

## Configuration Example

```json
{
  "mediatailor_configs": ["config-1", "config-2"],
  "recipients": ["recipient@yourdomain.com"],
  "sender_email": "mediatailor-reports@yourdomain.com"
}
```

## Deployment Commands

```bash
./deploy.sh up                     # Deploy stack
./deploy.sh down                   # Destroy stack
./deploy.sh up --region us-west-2  # Deploy to specific region
./deploy.sh down --region us-west-2 # Destroy from specific region
```

## Direct CDK Commands

```bash
cdk deploy                         # Deploy
cdk destroy                        # Remove
```

## Logging & Monitoring

**Log Levels**: Control via `LOG_LEVEL` environment variable in CDK stack
- `INFO`: Production (default)
- `DEBUG`: Development/troubleshooting
- `WARNING`: Issues only
- `ERROR`: Errors only

**Log Retention**: 30 days (automatic cleanup)

**Structured Logging**: All logs include correlation IDs for request tracing

## Quick Test

```bash
aws lambda invoke --function-name MediaTailorReportStack-MediaTailorReportFunction output.json
```

## Sample Report

A sample PDF report is available at [samples/mediatailor-report-year-month-date.pdf](samples/mediatailor-report-year-month-date.pdf) showing the expected output format with:
- Configuration-specific metrics tables
- Fill rate percentages with status indicators
- Duration metrics (hours/minutes/seconds)
- Error counts and latency measurements
- Simplified status categories (✓ Healthy, ℹ️ Info, 🟡 Warning, 🔴 Critical, ⚪ No Data)
- Professional formatting with AWS branding

Use this sample to understand the report structure before deploying.

## Security Features

- AWS security best practices validation
- Structured logging with correlation IDs
- Comprehensive error handling
- 30-day log retention for cost control
- Deployment automation scripts
- Input validation and sanitization
- Least privilege IAM permissions
- Container security (pinned base images, non-root user, health checks)