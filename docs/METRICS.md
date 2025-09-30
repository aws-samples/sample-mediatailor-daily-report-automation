# MediaTailor Metrics Reference

## Core Fill Rate Metrics

### Avail.FillRate
- **Description**: Average across all ad breaks (many unfilled)
- **Type**: Percentage
- **Interpretation**: Simple average that includes many short unfilled breaks

### Avail.FillRate (Weighted)
- **Description**: Actual revenue performance (time-weighted)
- **Type**: Percentage (calculated)
- **Interpretation**: More accurate revenue indicator as it weights by duration

### Avail.Duration
- **Description**: Total ad inventory available
- **Type**: Duration (milliseconds)
- **Interpretation**: Total time allocated for ads across all sessions

### Avail.FilledDuration
- **Description**: Total ad time that generated revenue
- **Type**: Duration (milliseconds)
- **Interpretation**: Actual monetized ad time

## Ad Decision Server (ADS) Metrics

### AdDecisionServer.FillRate
- **Description**: ADS response rate per ad request
- **Type**: Percentage
- **Interpretation**: How often ADS successfully returns ads

### AdDecisionServer.Ads
- **Description**: Number of ads returned by ADS
- **Type**: Count
- **Interpretation**: Total ad responses from your ad server

### AdDecisionServer.Duration
- **Description**: ADS response time (milliseconds)
- **Type**: Duration (milliseconds)
- **Interpretation**: Latency of ad decision requests

### AdDecisionServer.Errors
- **Description**: ADS error count
- **Type**: Count
- **Interpretation**: Failed requests to ad decision server

### AdDecisionServer.Timeouts
- **Description**: ADS timeout count
- **Type**: Count
- **Interpretation**: Requests that exceeded timeout threshold

## Session & Playback Metrics

### Session.Duration
- **Description**: Total session time
- **Type**: Duration (milliseconds)
- **Interpretation**: Combined viewing time across all sessions

### Avail.Impression
- **Description**: Ad impression count
- **Type**: Count
- **Interpretation**: Number of ad impressions served

### Avail.ObservedDuration
- **Description**: Actual observed ad break time
- **Type**: Duration (milliseconds)
- **Interpretation**: Real ad break duration as measured

### Avail.ExpectedDuration
- **Description**: Expected ad break duration
- **Type**: Duration (milliseconds)
- **Interpretation**: Planned ad break duration from configuration

## Error Monitoring Metrics

### GetManifest.Errors
- **Description**: Manifest request failures
- **Type**: Count
- **Interpretation**: Errors when requesting video manifests

### Origin.Errors
- **Description**: Origin server errors
- **Type**: Count
- **Interpretation**: Failures from content origin servers

## Status Indicators

The report uses color-coded status indicators:

- **✓ Good**: Metric is performing within expected ranges
- **🟡 Low/Slow/High**: Metric needs attention but not critical
- **🔴 Critical/High Errors**: Immediate attention required
- **⚪ No Data**: No data available for the metric
- **⚠️ Check Data/ADS**: Data validation warning

## Key Relationships

1. **Fill Rate Comparison**: Compare Avail.FillRate vs Avail.FillRate (Weighted) to understand break distribution
2. **ADS Performance**: AdDecisionServer.Duration + Errors + Timeouts indicate ADS health
3. **Revenue Efficiency**: Avail.FilledDuration / Avail.Duration shows monetization rate
4. **System Health**: GetManifest.Errors + Origin.Errors show infrastructure issues