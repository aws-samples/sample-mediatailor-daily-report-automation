# Configuration Guide

## Prerequisites

**Email Verification:** CDK will automatically create the SES email identity during deployment. You must verify the email by clicking the verification link sent by AWS SES to complete the setup.

## Configuration File

Edit `config.json`:

```json
{
  "mediatailor_configs": ["config-1", "config-2"],
  "metrics": [
    "Avail.FillRate",
    "Avail.Duration", 
    "Avail.FilledDuration",
    "AdDecisionServer.FillRate",
    "AdDecisionServer.Ads",
    "AdDecisionServer.Duration",
    "AdDecisionServer.Latency",
    "AdDecisionServer.Errors",
    "AdDecisionServer.Timeouts",
    "Avail.Impression",
    "Avail.ObservedDuration",
    "Avail.ObservedFilledDuration",
    "GetManifest.Errors",
    "GetManifest.Latency",
    "Origin.Errors",
    "Origin.Timeouts"
  ],
  "recipients": ["recipient@yourdomain.com"],
  "sender_email": "mediatailor-reports@yourdomain.com",
  "schedule": {
    "hour": "16",
    "minute": "0"
  }
}
```

## Parameters

- `mediatailor_configs`: List of MediaTailor configuration names
- `metrics`: CloudWatch metrics to include in reports
- `recipients`: Email addresses to receive reports
- `sender_email`: Email address to send reports from (CDK creates identity, you verify via email link)
- `schedule`: Cron schedule for daily reports

## Schedule Examples

- `"hour": "16", "minute": "0"` = 4:00 PM UTC
- `"hour": "8", "minute": "0"` = 8:00 AM UTC
- `"hour": "0", "minute": "30"` = 12:30 AM UTC

## Logging Configuration

**Environment Variables** (set in CDK stack):
- `LOG_LEVEL`: Controls logging verbosity
  - `INFO`: Production (default)
  - `DEBUG`: Development/troubleshooting
  - `WARNING`: Issues only
  - `ERROR`: Errors only

**Log Features**:
- Structured JSON logging with correlation IDs
- 30-day automatic retention
- Full stack traces for errors
- CloudWatch integration for monitoring

## Report Insights

The daily report helps you:
- **Monitor Revenue**: Track fill rate trends and revenue impact
- **Identify Issues**: Quickly spot ADS vs MediaTailor problems
- **Plan Capacity**: Understand ad inventory utilization
- **Maintain Quality**: Monitor error rates and system health