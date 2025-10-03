# MediaTailor Metrics Guide

## Quick Reference Card

### 🚨 **Alert Thresholds**
```
CRITICAL ALERTS:
- Avail.FillRate (Avg) < 70%
- Avail.FillRate (Weighted) < 70%
- AdDecisionServer.Errors > 100 count
- GetManifest.Errors > 100 count

WARNING ALERTS:
- Avail.FillRate (Avg) < 85%
- AdDecisionServer.Duration > 500ms
- AdDecisionServer.Timeouts > 50 count
```

### 📊 **Daily KPIs**
1. **Avail.FillRate (Avg)** - Simple average across all ad breaks
2. **Avail.FillRate (Weighted)** - Duration-weighted fill rate (revenue metric)
3. **AdDecisionServer.FillRate** - ADS response success rate
4. **Error Counts** - System health indicators

## Metric Deep Dive

### **Revenue Metrics**

#### Fill Rate Analysis
- **Avail.FillRate (Avg)**: Simple average across all ad breaks (includes many unfilled micro-breaks)
- **Avail.FillRate (Weighted)**: Duration-weighted calculation = (FilledDuration / TotalDuration) × 100
- **Business Impact**: Weighted fill rate directly correlates to revenue

#### When Fill Rates Differ (>20% gap)
```
If Weighted > Average:
→ MediaTailor creates many micro ad opportunities
→ Successfully fills valuable longer slots
→ Good monetization despite low per-break average

If Average > Weighted:
→ Short breaks filling well, long breaks struggling
→ Review ad decisioning for longer content
```

### **Operational Metrics**

#### Error Monitoring
- **AdDecisionServer.Errors**: Failed ADS requests (count)
- **AdDecisionServer.Timeouts**: ADS timeout events (count)
- **GetManifest.Errors**: Manifest generation failures (count)
- **Origin.Errors**: Content origin server issues (count)

#### Performance Metrics
- **AdDecisionServer.Duration**: ADS response time (milliseconds)
- **AdDecisionServer.FillRate**: ADS success rate percentage
- **AdDecisionServer.Ads**: Total ads returned by ADS (count)

#### Traffic & Inventory
- **Avail.Duration**: Total ad inventory available (milliseconds)
- **Avail.FilledDuration**: Monetized ad time (milliseconds)
- **Avail.ObservedDuration**: Actual measured ad break time
- **Avail.Impression**: Total ad impressions served (count)

## Troubleshooting Playbook

### **Scenario 1: Low Weighted Fill Rate (<70%)**
```
Step 1: Compare Fill Rates
├─ If Avg FillRate also low:
│  ├─ Check AdDecisionServer.FillRate
│  ├─ Review AdDecisionServer.Errors count
│  └─ Verify ADS inventory levels
└─ If Avg FillRate normal (>20% gap):
   ├─ Normal - many micro-breaks unfilled
   └─ Focus on weighted rate for revenue
```

### **Scenario 2: High Error Counts (>100)**
```
Step 1: Identify Primary Error Source
├─ AdDecisionServer.Errors High:
│  ├─ Check AdDecisionServer.Duration (>500ms)
│  ├─ Review AdDecisionServer.Timeouts
│  └─ Verify ADS server health
├─ GetManifest.Errors High:
│  ├─ Check MediaTailor service status
│  └─ Review manifest complexity
└─ Origin.Errors High:
   └─ Check content origin server health
```

### **Scenario 3: Performance Issues**
```
Step 1: Check Response Times
├─ AdDecisionServer.Duration > 500ms:
│  ├─ Review ADS server performance
│  ├─ Check network latency
│  └─ Consider timeout adjustments
└─ High Timeout Count (>50):
   ├─ Increase ADS timeout threshold
   └─ Investigate ADS capacity
```

## Business Intelligence

### **Revenue Analysis**
- **Primary KPI**: Avail.FillRate (Weighted) - direct revenue correlation
- **Inventory Utilization**: FilledDuration / TotalDuration ratio
- **Content Hours**: TotalDuration ÷ 8 = estimated content hours (12-15% ad load)
- **Revenue Minutes**: FilledDuration ÷ 60,000 = billable ad minutes

### **Operational Monitoring**
- **Error Thresholds**: >100 errors require investigation
- **Performance SLA**: ADS response <500ms
- **Fill Rate SLA**: Weighted fill rate >85%
- **Timeout Monitoring**: <50 timeouts per day

### **Data Validation Alerts**
- **Suspicious Data**: Large gap between avg/weighted fill rates
- **ADS Mismatch**: Impressions without ADS ads
- **Zero Data**: Missing metrics indicate collection issues

## Metric Calculations

### **Derived Metrics**
```python
# Weighted Fill Rate (calculated in Lambda)
weighted_fill_rate = (filled_duration_sum / total_duration_sum) * 100

# Content Hours Estimation
content_hours = total_duration_ms / 1000 / 3600 / 0.125  # 12.5% ad load

# Fill Efficiency
fill_efficiency = (filled_duration / total_duration) * 100
```

### **Status Indicators**
- **✓ Good**: Metrics within normal ranges
- **🟡 Warning**: Needs attention (slow response, low fill)
- **🔴 Critical**: Immediate action required (<70% fill, >100 errors)
- **⚪ No Data**: Missing data points
- **⚠️ Check**: Data validation warnings

## Report Insights

### **Automated Analysis**
The system generates contextual insights:
- **Fill Rate Gaps**: Explains >20% difference between avg/weighted rates
- **Inventory Context**: Converts durations to business-friendly units
- **Efficiency Ratings**: Categorizes fill performance (>90% excellent, <60% needs review)
- **Revenue Summary**: Bottom-line monetization effectiveness

### **Key Relationships**
- **Avail.Impression** should correlate with **AdDecisionServer.Ads**
- **High AdDecisionServer.Duration** often leads to **Timeouts**
- **Large Avg/Weighted gap** indicates many micro ad opportunities
- **Zero ADS ads** with **positive Impressions** suggests data issues