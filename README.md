# MediaTailor Daily Report

Automated daily email reports for MediaTailor ad-fill rate metrics.

## Setup

1. **Install CDK**: `npm install -g aws-cdk`
2. **Verify SES Email**: Verify your sender email in AWS SES console
3. **Update Configuration**: Edit `config.json` with your MediaTailor configurations
4. **Deploy**: Run `./deploy.sh`

## Configuration

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
  "recipients": ["email@example.com"]
}
```

## Available Metrics

**Core Fill Rate Metrics:**
- `Avail.FillRate` - Average fill rate across all ad avails (%)
- `Avail.Duration` - Total planned ad time (milliseconds)
- `Avail.FilledDuration` - Total filled ad time (milliseconds)
- `AdDecisionServer.FillRate` - Fill rate from Ad Decision Server (%)

**Calculated Metrics:**
- **WeightedFillRate** = (Avail.FilledDuration / Avail.Duration) × 100 - Duration-weighted Avail fill rate

## Metrics Documentation

### **Fill Rate Metrics (Revenue Impact)**

#### `Avail.FillRate` 🎯 **CRITICAL**
- **What**: Simple average of fill rates across all ad avails
- **Why Important**: Direct revenue impact - unfilled avails = lost revenue
- **Good Range**: >85% (varies by industry)
- **Alert If**: <80% or trending downward

#### `AdDecisionServer.FillRate` 🔍 **DIAGNOSTIC**
- **What**: Fill rate from your Ad Decision Server (ADS)
- **Why Important**: Identifies if low fill is ADS or MediaTailor issue
- **Troubleshooting**: 
  - If ADS fill rate is low → ADS not returning enough ads
  - If ADS fill rate is high but Avail fill rate is low → MediaTailor processing issue

#### `WeightedFillRate` 📊 **CALCULATED**
- **Formula**: (Avail.FilledDuration / Avail.Duration) × 100
- **Why Better**: Accounts for different avail durations (longer avails get more weight)
- **Use Case**: More accurate than simple average for business reporting

### **Duration Metrics (Capacity Planning)**

#### `Avail.Duration` ⏱️
- **What**: Total planned ad time in milliseconds
- **Why Important**: Shows your total ad inventory capacity
- **Use Case**: Capacity planning and revenue forecasting

#### `Avail.FilledDuration` ✅
- **What**: Actual ad time filled in milliseconds
- **Why Important**: Shows monetized inventory
- **KPI**: FilledDuration / Duration = utilization efficiency

### **Error Metrics (System Health)**

#### `AdDecisionServer.Errors` 🚨 **CRITICAL**
- **What**: Non-200 responses, timeouts from ADS
- **Why Important**: ADS failures directly impact fill rates
- **Alert If**: >5% of requests or sudden spikes
- **Action**: Check ADS health, network connectivity

#### `GetManifest.Errors` 📋 **OPERATIONAL**
- **What**: Errors during manifest generation
- **Why Important**: Affects player experience and ad delivery
- **Alert If**: >1% of requests
- **Action**: Check MediaTailor service health

#### `ErrorRate` 📈 **CALCULATED**
- **Formula**: (Total Errors / Total Requests) × 100
- **Why Important**: Overall system health indicator
- **Target**: <2% for healthy operations

### **Traffic Metrics (Load Monitoring)**

#### `Requests` 🌐
- **What**: Concurrent transactions per second
- **Why Important**: Shows system load and viewer engagement
- **Use Case**: Scaling decisions and performance monitoring

## Metric Relationships & Troubleshooting

### **Low Fill Rate Diagnosis**
```
If Avail.FillRate < 80%:
  ├─ Check AdDecisionServer.FillRate
  │   ├─ If ADS Fill Rate < 80% → ADS Issue
  │   │   ├─ Check ad inventory levels
  │   │   ├─ Review targeting criteria
  │   │   └─ Verify ADS configuration
  │   └─ If ADS Fill Rate > 80% → MediaTailor Issue
  │       ├─ Check AdDecisionServer.Errors
  │       ├─ Check GetManifest.Errors
  │       └─ Review transcoding issues
  └─ Compare Simple vs Weighted Fill Rate
      └─ Large difference indicates duration variance
```

### **Performance Benchmarks**
| Metric | Excellent | Good | Needs Attention | Critical |
|--------|-----------|------|-----------------|----------|
| Fill Rate | >90% | 80-90% | 70-80% | <70% |
| Error Rate | <1% | 1-2% | 2-5% | >5% |
| ADS Errors | <2% | 2-5% | 5-10% | >10% |

### **Business Impact**
- **1% Fill Rate Drop** = ~1% revenue loss
- **High Error Rates** = Poor viewer experience
- **ADS Issues** = Immediate revenue impact
- **Duration Metrics** = Inventory optimization opportunities

## Report Insights

The daily report helps you:
- **Monitor Revenue**: Track fill rate trends and revenue impact
- **Identify Issues**: Quickly spot ADS vs MediaTailor problems
- **Plan Capacity**: Understand ad inventory utilization
- **Maintain Quality**: Monitor error rates and system health

## Schedule

Reports are sent daily at 8 AM UTC. Modify the cron expression in `template.yaml` to change timing.

## Manual Testing

```bash
# Get function name from CDK output
aws lambda invoke --function-name MediaTailorReportStack-MediaTailorReportFunction output.json
```

## CDK Commands

```bash
# Synthesize CloudFormation template
cdk synth

# Deploy stack
cdk deploy

# Destroy stack
cdk destroy
```