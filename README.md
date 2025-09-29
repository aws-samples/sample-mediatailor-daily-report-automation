# MediaTailor Daily Report

Automated daily email reports for MediaTailor ad-fill rate metrics.

## Quick Start

1. **Install CDK**: `npm install -g aws-cdk`
2. **Verify SES Email**: Verify your sender email in AWS SES console
3. **Update Configuration**: Copy `config/config.json.example` to `config/config.json` and edit with your settings
4. **Deploy**: Run `./deploy.sh [region]`

## Documentation

- [📋 Configuration Guide](docs/CONFIGURATION.md) - Setup and configuration options
- [📊 Metrics Reference](docs/METRICS.md) - Available metrics and their meanings
- [🧪 Testing Guide](docs/TESTING.md) - How to test the system
- [🏗️ Architecture](ARCHITECTURE.md) - System architecture details

## Configuration Example

```json
{
  "mediatailor_configs": ["config-1", "config-2"],
  "recipients": ["email@example.com"],
  "sender_email": "noreply@example.com"
}
```

## CDK Commands

```bash
cdk deploy [--region us-east-1]    # Deploy
cdk destroy [--region us-east-1]   # Remove
```

## Quick Test

```bash
aws lambda invoke --function-name MediaTailorReportStack-MediaTailorReportFunction output.json
```