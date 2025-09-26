# MediaTailor Metrics Guide

## Quick Reference Card

### 🚨 **Alert Thresholds**
```
CRITICAL ALERTS:
- Avail.FillRate < 70%
- AdDecisionServer.Errors > 10%
- ErrorRate > 5%

WARNING ALERTS:
- Avail.FillRate < 80%
- AdDecisionServer.Errors > 5%
- ErrorRate > 2%
```

### 📊 **Daily KPIs**
1. **Fill Rate** - Primary revenue metric
2. **Weighted Fill Rate** - More accurate business metric  
3. **Error Rate** - System health indicator
4. **ADS Fill Rate** - Root cause analysis

## Metric Deep Dive

### **Revenue Metrics**

#### Fill Rate Analysis
- **Simple Average** (`Avail.FillRate`): Average across all avails
- **Weighted Average** (`WeightedFillRate`): Duration-weighted (more accurate)
- **Business Impact**: 1% fill rate = ~1% revenue change

#### When Fill Rates Differ
```
If WeightedFillRate > Avail.FillRate:
→ Longer avails performing better
→ Focus on optimizing short avails

If WeightedFillRate < Avail.FillRate:  
→ Shorter avails performing better
→ Review long-form content ad strategy
```

### **Operational Metrics**

#### Error Rate Breakdown
- **ADS Errors**: Upstream ad server issues
- **Manifest Errors**: MediaTailor processing issues
- **Combined Error Rate**: Overall system health

#### Traffic Patterns
- **Requests**: Concurrent viewer load
- **Duration Metrics**: Ad inventory utilization

## Troubleshooting Playbook

### **Scenario 1: Low Fill Rate**
```
Step 1: Check AdDecisionServer.FillRate
├─ If Low (< 80%):
│  ├─ Review ad inventory levels
│  ├─ Check targeting criteria  
│  └─ Verify ADS configuration
└─ If High (> 80%):
   ├─ Check AdDecisionServer.Errors
   ├─ Review transcoding issues
   └─ Check GetManifest.Errors
```

### **Scenario 2: High Error Rate**
```
Step 1: Identify Error Source
├─ AdDecisionServer.Errors High:
│  ├─ Check ADS server health
│  ├─ Review network connectivity
│  └─ Verify ADS response times
└─ GetManifest.Errors High:
   ├─ Check MediaTailor service status
   ├─ Review origin server health
   └─ Check manifest complexity
```

### **Scenario 3: Performance Degradation**
```
Step 1: Compare Metrics
├─ Fill Rate Trending Down:
│  └─ Check if ADS or MediaTailor issue
├─ Error Rate Trending Up:
│  └─ Identify error source and pattern
└─ Request Volume Changes:
   └─ Check if capacity-related issue
```

## Business Intelligence

### **Revenue Optimization**
- Monitor fill rate trends by time of day
- Compare weekday vs weekend performance  
- Track seasonal patterns
- Identify high-value vs low-value inventory

### **Operational Excellence**
- Set up automated alerts for threshold breaches
- Track error rate trends to prevent issues
- Monitor ADS performance for SLA compliance
- Use weighted metrics for accurate reporting

### **Capacity Planning**
- Use duration metrics for inventory forecasting
- Monitor request patterns for scaling decisions
- Track fill rate vs traffic correlation
- Plan for peak traffic events

## Integration with Business Systems

### **Revenue Reporting**
```sql
-- Example: Calculate daily revenue impact
SELECT 
  date,
  avail_duration_ms / 1000 / 60 as total_ad_minutes,
  filled_duration_ms / 1000 / 60 as filled_ad_minutes,
  (filled_duration_ms / avail_duration_ms) * 100 as weighted_fill_rate,
  filled_ad_minutes * avg_cpm / 1000 as estimated_revenue
FROM daily_metrics;
```

### **SLA Monitoring**
- Fill Rate SLA: Typically 85-90%
- Error Rate SLA: Typically <2%
- ADS Response Time: Typically <500ms
- System Availability: Typically 99.9%

## Advanced Analytics

### **Correlation Analysis**
- Fill Rate vs Time of Day
- Error Rate vs Traffic Volume  
- ADS Performance vs Fill Rate
- Seasonal Trends and Patterns

### **Predictive Insights**
- Forecast fill rate based on historical trends
- Predict capacity needs based on traffic patterns
- Identify potential issues before they impact revenue
- Optimize ad inventory based on performance data