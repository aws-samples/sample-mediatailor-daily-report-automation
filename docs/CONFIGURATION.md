# Configuration Guide

## Prerequisites

**Required:** Verify your sender email in AWS SES console before deployment.

## Configuration File

Edit `config.json`:

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
  "sender_email": "noreply@example.com",
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
- `sender_email`: Email address to send reports from (must be verified in SES)
- `schedule`: Cron schedule for daily reports

## Schedule Examples

- `"hour": "16", "minute": "0"` = 4:00 PM UTC
- `"hour": "8", "minute": "0"` = 8:00 AM UTC
- `"hour": "0", "minute": "30"` = 12:30 AM UTC

## Report Insights

The daily report helps you:
- **Monitor Revenue**: Track fill rate trends and revenue impact
- **Identify Issues**: Quickly spot ADS vs MediaTailor problems
- **Plan Capacity**: Understand ad inventory utilization
- **Maintain Quality**: Monitor error rates and system health