# MediaTailor Metrics Reference

## Core Fill Rate Metrics

### Avail.FillRate
- **Description**: Duration-weighted fill rate (revenue-focused)
- **Type**: Percentage (calculated)
- **Calculation**: (Total FilledDuration ÷ Total Duration) × 100
- **Example**: 2000sec filled ÷ 3800sec total = 52.6%
- **Use Case**: Revenue performance and business reporting
- **Advantage**: Reflects actual monetization effectiveness
- **Note**: This is the weighted calculation, which is more accurate than simple averages for revenue analysis

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
- **Description**: Duration-weighted fill rate for ADS responses
- **Type**: Percentage (calculated)
- **Calculation**: (AdDecisionServer.Duration ÷ Avail.Duration) × 100
- **Interpretation**: How effectively ADS fills available ad inventory
- **Note**: Uses weighted calculation for accuracy, not simple average

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

## Observed Duration Metrics (Actual vs Planned)

These metrics capture what actually happened during playback, as opposed to what MediaTailor planned based on SCTE-35 markers. The difference between planned and observed metrics is critical for accurate revenue calculation and understanding viewer experience.

### Avail.ObservedDuration
- **Description**: Actual duration of ad avails that occurred during playback
- **Type**: Duration (milliseconds)
- **Source**: Measured from manifest segment timing and SCTE CUE-IN timing
- **Example**: CUE-IN arrives at 25 seconds → 25,000ms observed (even if 30 seconds was planned)
- **Use Case**: Actual viewer experience and revenue calculation
- **Common Scenario**: Live content returns early (early CUE-IN), cutting break short

### Avail.ObservedFilledDuration
- **Description**: Actual duration of ads that were observed during playback
- **Type**: Duration (milliseconds)
- **Source**: Sum of ad creative durations that actually played
- **Example**: If 25 seconds of a 30-second break played, this shows actual ad duration served
- **Revenue Impact**: Direct correlation to actual billable ad time (not planned)
- **Use Case**: Calculate true revenue earned vs planned revenue

### Avail.ObservedFillRate
- **Description**: Observed fill rate calculated from actual playback data
- **Type**: Percentage (calculated locally — not fetched from CloudWatch)
- **Calculation**: (Avail.ObservedFilledDuration ÷ Avail.ObservedDuration) × 100
- **Advantage**: Works for both HLS and DASH (unlike CloudWatch's pre-calculated metric which is HLS-only)
- **Use Case**: Validate actual performance vs planned performance
- **Note**: This is calculated locally, not retrieved from CloudWatch

> **Important — Locally Calculated Metric**
>
> AWS CloudWatch emits `Avail.ObservedFillRate` natively only for HLS manifests, at the first `CUE-IN` tag. If there is no `CUE-IN` tag, CloudWatch does not emit this metric. It is not emitted for DASH streams at all.
>
> This report calculates `Avail.ObservedFillRate` locally using the sum of `Avail.ObservedFilledDuration` divided by the sum of `Avail.ObservedDuration`. This provides coverage for both HLS and DASH streams.
>
> For HLS streams, the locally calculated value may differ slightly from the CloudWatch-native metric because CloudWatch uses a simple average of per-avail fill rates, while this report uses a weighted (sum-based) average. The weighted approach is more accurate for revenue analysis but will produce a different number than the CloudWatch console.
>
> Reference: [AWS MediaTailor CloudWatch Metrics](https://docs.aws.amazon.com/mediatailor/latest/ug/monitoring-cloudwatch-metrics.html)

**Key Distinction:**
- **Planned metrics** (`Avail.Duration`, `Avail.FilledDuration`) = What MediaTailor expected based on SCTE-35 markers
- **Observed metrics** (`Avail.ObservedDuration`, `Avail.ObservedFilledDuration`) = What actually happened during playback

**Why this matters:**
In live sports, early CUE-IN (game resumes before break ends) causes observed duration to be less than planned duration, resulting in revenue loss that planned metrics don't capture.

## Manifest Performance Metrics

### GetManifest.Latency
- **Description**: Response time in milliseconds for manifest generation
- **Type**: Duration (milliseconds)
- **Source**: Time MediaTailor takes to generate and return manifests
- **Use Case**: User experience monitoring and performance optimization
- **Threshold**: Should be < 100ms for good user experience
- **Business Impact**: High latency can cause buffering and poor viewer experience

## Session & Playback Metrics

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

### Planned vs Observed Duration Analysis
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

## Error Monitoring Metrics

### GetManifest.Errors
- **Description**: Number of errors while MediaTailor was generating manifests
- **Type**: Count
- **Interpretation**: Errors during manifest generation process

### Origin.Errors
- **Description**: Origin server connectivity problems
- **Type**: Count
- **Interpretation**: Failures from content origin servers

### Origin.Timeouts
- **Description**: Number of timed-out requests to origin server
- **Type**: Count
- **Interpretation**: Requests to origin that exceeded timeout threshold
- **Use Case**: Separate timeout issues from general errors for better troubleshooting
- **Note**: Consistent with AdDecisionServer.Timeouts metric

## Status Indicators

The report uses simplified, consistent status categories across all metrics:

### Status Level Definitions
| Status | Meaning |
|--------|---------|
| **✓ Healthy** | Metrics within expected ranges |
| **ℹ️ Info** | Informational only (no threshold applies) |
| **🟡 Warning** | Approaching concerning levels |
| **🔴 Critical** | Requires immediate attention |
| **⚪ No Data** | Insufficient data to determine status |

### Fill Rate Metrics (Avail.FillRate, AdDecisionServer.FillRate, Avail.ObservedFillRate)
- **✓ Healthy**: ≥80% fill rate
- **🟡 Warning**: 70-79% fill rate
- **🔴 Critical**: <70% fill rate
- **⚪ No Data**: 0% (no data available)

### Latency Metrics

#### AdDecisionServer.Latency
AWS MediaTailor has a 3-second ADS timeout ([source](https://docs.aws.amazon.com/mediatailor/latest/ug/quotas.html)) and recommends ADS latency under 1000ms ([source](https://docs.aws.amazon.com/mediatailor/latest/ug/cdn-monitoring.html)).
- **✓ Healthy**: ≤1000ms response time
- **🟡 Warning**: 1001-2000ms response time
- **🔴 Critical**: >2000ms response time (approaching 3s timeout)
- **⚪ No Data**: 0ms (no data available)

#### GetManifest.Latency
AWS recommends manifest generation under 200ms ([source](https://docs.aws.amazon.com/mediatailor/latest/ug/cdn-monitoring.html)).
- **✓ Healthy**: ≤200ms response time
- **🟡 Warning**: 201-500ms response time
- **🔴 Critical**: >500ms response time
- **⚪ No Data**: 0ms (no data available)

### Error Count Metrics (Absolute Thresholds)
- **✓ Healthy**: <100 errors/timeouts
- **🟡 Warning**: 100-999 errors/timeouts
- **🔴 Critical**: ≥1,000 errors/timeouts
- **⚪ No Data**: 0 events (no data available)
- **Applies to**: AdDecisionServer.Errors, AdDecisionServer.Timeouts, GetManifest.Errors, Origin.Errors, Origin.Timeouts
- **Note**: Absolute thresholds are used because MediaTailor does not expose the necessary denominator metrics to calculate accurate error rates. AdDecisionServer.Ads counts ads returned (not requests), so it cannot be used as a denominator.

### Duration Metrics (Informational)
- **ℹ️ Info**: All non-zero values (informational only, no thresholds)
- **⚪ No Data**: 0 duration (no data available)
- **Applies to**: Avail.Duration, Avail.FilledDuration, Avail.ObservedDuration, Avail.ObservedFilledDuration, AdDecisionServer.Duration

### Volume Metrics (Informational)
- **ℹ️ Info**: All non-zero values (informational only, no thresholds)
- **⚪ No Data**: 0 count (no data available)
- **Applies to**: Avail.Impression, AdDecisionServer.Ads

## Business Impact Analysis

### Revenue Calculations
- **Planned Revenue**: Based on Avail.Duration (what was expected)
- **Actual Revenue**: Based on Avail.ObservedDuration (what actually happened)
- **Planned Monetized Time**: Avail.FilledDuration
- **Actual Monetized Time**: Avail.ObservedFilledDuration
- **Revenue Efficiency**: ObservedFilledDuration ÷ ObservedDuration

### Performance Indicators
1. **Fill Rate Performance**: Avail.FillRate and AdDecisionServer.FillRate show monetization effectiveness
2. **Planned vs Actual Variance**: Duration vs ObservedDuration shows SCTE timing accuracy and early CUE-IN frequency
3. **Revenue Impact**: Compare planned vs observed metrics to quantify revenue loss from early breaks
4. **Actual Revenue Efficiency**: ObservedFilledDuration ÷ ObservedDuration shows true monetization
5. **Inventory Utilization**: FilledDuration ÷ Duration shows planned fill performance
6. **ADS Performance**: AdDecisionServer.FillRate + Errors + Timeouts + Latency indicate ADS health
7. **Manifest Performance**: GetManifest.Latency + Errors show user experience quality
8. **Origin Health**: Origin.Errors + Timeouts show content delivery infrastructure issues