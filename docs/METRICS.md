# MediaTailor Metrics Reference

## Core Fill Rate Metrics

### Avail.FillRate (Avg)
- **Description**: Simple average fill rate percentage for individual ad avails
- **Type**: Percentage
- **Calculation**: Sum of individual break fill rates ÷ number of breaks
- **Example**: 1000 breaks: 900×2sec (0% filled) + 100×20sec (100% filled) = 10% average
- **Use Case**: Break-level performance analysis
- **Limitation**: Skewed by many unfilled micro-breaks

### Avail.FillRate (Weighted)
- **Description**: Duration-weighted fill rate (revenue-focused)
- **Type**: Percentage (calculated)
- **Calculation**: (Total FilledDuration ÷ Total Duration) × 100
- **Example**: Same scenario = (2000sec filled ÷ 3800sec total) = 53%
- **Use Case**: Revenue performance and business reporting
- **Advantage**: Reflects actual monetization effectiveness

## Core Duration Metrics

### Avail.Duration
- **Description**: Planned ad break duration from SCTE-35 or configuration
- **Type**: Duration (milliseconds)
- **Source**: SCTE CUE-OUT message duration or MediaTailor config
- **Example**: SCTE message says "30-second ad break" → 30,000ms
- **Use Case**: Inventory planning and capacity forecasting
- **Business Impact**: Represents total sellable ad inventory

### Avail.FilledDuration
- **Description**: Actual duration of ad breaks that were filled with ads
- **Type**: Duration (milliseconds)
- **Source**: Sum of all ad creative durations served
- **Example**: 30sec break with 2×15sec ads = 30,000ms filled
- **Revenue Impact**: Direct correlation to billable ad time
- **Calculation Base**: Used for weighted fill rate calculation

## Ad Decision Server (ADS) Metrics

### AdDecisionServer.FillRate
- **Description**: Simple average of fill rate percentages returned by ADS
- **Type**: Percentage
- **Interpretation**: How often ADS successfully returns ads

### AdDecisionServer.Ads
- **Description**: Number of ads returned by ADS
- **Type**: Count
- **Interpretation**: Total ad responses from your ad server

### AdDecisionServer.Duration
- **Description**: Total duration of ads returned by ADS
- **Type**: Duration (milliseconds)
- **Interpretation**: Total ad content duration from ADS responses

### AdDecisionServer.Latency
- **Description**: Response time in milliseconds for requests MediaTailor makes to ADS
- **Type**: Duration (milliseconds)
- **Interpretation**: Network latency for ad decision requests

### AdDecisionServer.Errors
- **Description**: Number of non-HTTP 200, empty, and timed-out responses from ADS
- **Type**: Count
- **Interpretation**: Failed requests to ad decision server

### AdDecisionServer.Timeouts
- **Description**: Number of timed-out requests to ADS
- **Type**: Count
- **Interpretation**: Requests that exceeded timeout threshold

## Session & Playback Metrics

### Session.Duration
- **Description**: Total session time
- **Type**: Duration (milliseconds)
- **Interpretation**: Combined viewing time across all sessions

### Avail.Impression
- **Description**: Number of ad impressions (increments when first segment requested)
- **Type**: Count
- **Interpretation**: Number of ad impressions served

### Avail.ObservedDuration
- **Description**: Actual duration of ad avails that occurred based on manifest segments
- **Type**: Duration (milliseconds)
- **Source**: Measured from manifest segment timing and SCTE CUE-IN timing
- **Example**: CUE-IN arrives at 25 seconds → 25,000ms observed
- **Use Case**: Actual viewer experience and revenue calculation
- **SCTE Scenario**: Live content returns early, cutting break short

## SCTE-35 Duration Scenarios

### Normal Operation
```
SCTE CUE-OUT: "Start 30-second break"
Avail.Duration: 30,000ms (planned)
SCTE CUE-IN: Arrives at 30 seconds
Avail.ObservedDuration: 30,000ms (actual)
Result: Perfect timing
```

### Early Return (Common in Live)
```
SCTE CUE-OUT: "Start 30-second break"
Avail.Duration: 30,000ms (planned)
SCTE CUE-IN: Arrives at 25 seconds (live sports resumes)
Avail.ObservedDuration: 25,000ms (actual)
Result: 5 seconds of ads cut off
```

### Extended Break (Technical Issues)
```
SCTE CUE-OUT: "Start 30-second break"
Avail.Duration: 30,000ms (planned)
SCTE CUE-IN: Delayed to 35 seconds (buffering/loading)
Avail.ObservedDuration: 35,000ms (actual)
Result: Poor viewer experience
```

## Duration Analysis

### Key Relationships
```
If ObservedDuration < Duration:
→ Breaks ending early (SCTE CUE-IN, live content)
→ Potential revenue loss from cut-off ads
→ Common in live sports, breaking news

If ObservedDuration > Duration:
→ Breaks running long (buffering, slow ad load)
→ Poor viewer experience
→ Technical delivery issues

If ObservedDuration ≈ Duration:
→ Optimal scenario - breaks running as planned
```

### Fill Rate Comparison
```
Large gap between Avg and Weighted (>20%):
→ Many micro ad opportunities unfilled
→ Longer breaks successfully monetized
→ Normal MediaTailor behavior

Similar Avg and Weighted rates:
→ Consistent break sizes
→ Uniform fill performance across all breaks
```

### Avail.ExpectedDuration
- **Description**: Expected ad break duration
- **Type**: Duration (milliseconds)
- **Interpretation**: Planned ad break duration from configuration

## Error Monitoring Metrics

### GetManifest.Errors
- **Description**: Number of errors while MediaTailor was generating manifests
- **Type**: Count
- **Interpretation**: Errors during manifest generation process

### Origin.Errors
- **Description**: Origin server connectivity problems
- **Type**: Count
- **Interpretation**: Failures from content origin servers

## Status Indicators

The report uses color-coded status indicators with specific thresholds:

### Fill Rate Metrics
- **✓ Good**: ≥85% fill rate
- **🟡 Low**: 70-84% fill rate
- **🔴 Critical**: <70% fill rate
- **⚪ No Data**: 0% (no data available)
- **⚠️ Check Data**: >20% discrepancy between average and weighted rates

### Latency Metrics (AdDecisionServer.Latency)
- **✓ Good**: ≤300ms response time
- **🟡 Slow Response**: 301-500ms response time
- **🔴 High Latency**: >500ms response time
- **⚪ No Data**: 0ms (no data available)

### Error Count Metrics
- **✓ Good**: Minimal errors/timeouts
- **🟡 Timeouts**: >50 timeout events
- **🔴 High Errors**: >100 error events
- **⚪ No Data**: 0 events (no data available)

### Duration Metrics
- **✓ Good**: Normal duration ranges
- **🟡 High Volume**: >2 hours total duration (high traffic)
- **⚪ No Data**: 0 duration (no data available)

### Count Metrics (Ads, Impressions)
- **✓ Good**: Positive counts with normal activity
- **⚪ No Data**: 0 count (no data available)
- **⚠️ Check ADS**: Impressions without corresponding ADS ads

## Business Impact Analysis

### Revenue Calculations
- **Planned Revenue**: Based on Avail.Duration
- **Actual Revenue**: Based on Avail.ObservedDuration
- **Monetized Time**: Avail.FilledDuration
- **Efficiency**: FilledDuration ÷ ObservedDuration

### Performance Indicators
1. **Fill Rate Comparison**: Avg vs Weighted shows break distribution patterns
2. **Duration Variance**: Duration vs ObservedDuration shows SCTE timing accuracy
3. **Revenue Efficiency**: FilledDuration ÷ ObservedDuration shows actual monetization
4. **Inventory Utilization**: FilledDuration ÷ Duration shows planned vs delivered
5. **ADS Performance**: AdDecisionServer.Duration + Errors + Timeouts indicate ADS health
6. **System Health**: GetManifest.Errors + Origin.Errors show infrastructure issues