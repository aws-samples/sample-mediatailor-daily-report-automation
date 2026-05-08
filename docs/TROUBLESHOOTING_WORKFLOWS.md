# MediaTailor Troubleshooting Workflows

This guide maps real-world failure scenarios to the metrics needed for diagnosis. Use this to configure your `config.json` for your specific monitoring needs.

---

## Quick Reference: Failure Scenarios

| **Scenario** | **Symptoms** | **Required Metrics** |
|-------------|-------------|---------------------|
| ADS Failures | Ads not inserting | `AdDecisionServer.Errors`, `AdDecisionServer.Timeouts`, `AdDecisionServer.Latency`, `AdDecisionServer.Ads` |
| Ad Insertion Failures | Low revenue despite ADS health | `Avail.FillRate`, `Avail.Duration`, `Avail.FilledDuration` |
| Transcoding Failures | Ads unavailable | `AdNotReady`, `SkippedReason.TranscodeInProgress`, `SkippedReason.TranscodeError` |
| Origin Issues | Manifest/playback failures | `Origin.Errors`, `Origin.Timeouts` |
| Manifest Generation Issues | Player buffering | `GetManifest.Errors`, `GetManifest.Latency` |
| Early Ad Break Termination | Revenue loss in live content | `Avail.ObservedDuration`, `Avail.ObservedFilledDuration`, `Avail.Duration` |

---

## Scenario 1: ADS Failures (Ad Decision Server Issues)

### What It Is
Your ad server (Google Ad Manager, FreeWheel, etc.) is failing to respond or returning errors.

### Symptoms
- Ads not inserting at all
- Slate content playing instead of ads
- Inconsistent ad playback

### Required Metrics
```json
{
  "metrics": [
    "AdDecisionServer.Errors",      // Non-200 responses and empty responses
    "AdDecisionServer.Timeouts",    // Requests exceeding 3s timeout
    "AdDecisionServer.Latency",     // Response time (should be <1000ms)
    "AdDecisionServer.Ads",         // Number of ads returned (volume check)
    "Avail.Duration"                // Context: total inventory available
  ]
}
```

### Diagnosis Pattern
| **Condition** | **Root Cause** | **Action** |
|--------------|---------------|-----------|
| High `Errors` + Normal `Latency` | ADS returning 4xx/5xx errors | Check ADS logs, verify campaign targeting |
| High `Timeouts` + High `Latency` | ADS too slow (>3s) | Optimize ADS performance, check network |
| Low `Ads` count + Low `Errors` | No campaigns targeting | Check campaign schedules and targeting rules |
| All metrics = 0 | ADS unreachable | Verify ADS URL, check network/firewall |

### Thresholds
- **🔴 Critical**: `Errors` or `Timeouts` ≥1000/day, `Latency` >2000ms
- **🟡 Warning**: `Errors` or `Timeouts` 100-999/day, `Latency` 1000-2000ms

### Optional Metrics (For Context)
- `Avail.Impression` — To see if ANY ads are playing
- `Avail.FillRate` — Only if you want revenue impact visibility

---

## Scenario 2: Ad Insertion Failures (MediaTailor Issues)

### What It Is
ADS is healthy and returning ads, but MediaTailor can't insert them.

### Symptoms
- ADS showing successful responses
- Low fill rates despite ads available
- Specific ads not playing

### Required Metrics
```json
{
  "metrics": [
    "Avail.FillRate",               // Overall insertion success
    "Avail.Duration",               // Total inventory
    "Avail.FilledDuration",         // Actual filled time
    "AdDecisionServer.FillRate",    // What ADS provided
    "AdDecisionServer.Duration",    // Total ad duration from ADS
    "AdDecisionServer.Ads",         // Number of ads from ADS
    "AdNotReady",                   // Transcode not complete
    "SkippedReason.TranscodeInProgress",
    "SkippedReason.TranscodeError",
    "SkippedReason.DurationExceeded"
  ]
}
```

### Diagnosis Pattern
| **Condition** | **Root Cause** | **Action** |
|--------------|---------------|-----------|
| `AdDecisionServer.FillRate` high but `Avail.FillRate` low | MediaTailor insertion issues | Check transcoding, variant matching |
| High `AdNotReady` or `TranscodeInProgress` | Transcode lag | Pre-cache ads, optimize transcode |
| High `DurationExceeded` | ADS returning ads longer than avail | Fix ADS configuration, check avail durations |

### Thresholds
- **🔴 Critical**: `Avail.FillRate` <70%
- **🟡 Warning**: `Avail.FillRate` 70-80%

### Note
If you use **direct campaigns without programmatic backfill** (direct-sold inventory), low `Avail.FillRate` is EXPECTED and does NOT indicate failure. Remove fill rate metrics from your config.

---

## Scenario 3: Transcoding Failures

### What It Is
Ads can't play because transcoding hasn't completed or failed.

### Symptoms
- First ad playback often fails
- Ads play successfully after first request
- Specific ad creatives never play

### Required Metrics
```json
{
  "metrics": [
    "AdNotReady",                   // Primary indicator
    "SkippedReason.TranscodeInProgress",  // Still transcoding
    "SkippedReason.TranscodeError",       // Transcode failed
    "SkippedReason.NewCreative",          // First-time ad request
    "SkippedReason.NoVariantMatch",       // Bitrate mismatch
    "AdDecisionServer.Ads",         // Context: total ads requested
    "Avail.FillRate"                // Impact: revenue loss
  ]
}
```

### Diagnosis Pattern
| **Condition** | **Root Cause** | **Action** |
|--------------|---------------|-----------|
| High `TranscodeInProgress` | Slow transcode or high volume | Pre-cache popular ads, scale transcode |
| High `TranscodeError` | Invalid ad creative format | Check ad creative specs vs. content specs |
| High `NoVariantMatch` | Bitrate/codec mismatch | Configure transcode profiles to match content |
| High `NewCreative` | No pre-caching | Implement ad pre-warming strategy |

### Thresholds
- **🔴 Critical**: Any `TranscodeError` count
- **🟡 Warning**: `TranscodeInProgress` >10% of `AdDecisionServer.Ads`

---

## Scenario 4: Origin Server Issues

### What It Is
MediaTailor can't fetch manifests or segments from your content origin.

### Symptoms
- Playback failures
- Manifest generation errors
- Intermittent content availability

### Required Metrics
```json
{
  "metrics": [
    "Origin.Errors",                // Non-200 responses
    "Origin.Timeouts",              // Origin too slow
    "GetManifest.Errors",           // Manifest generation failures
    "GetManifest.Latency"           // Context: performance
  ]
}
```

### Diagnosis Pattern
| **Condition** | **Root Cause** | **Action** |
|--------------|---------------|-----------|
| High `Origin.Errors` + Normal `Timeouts` | Origin returning errors | Check origin health, CDN cache |
| High `Origin.Timeouts` | Origin too slow | Optimize origin, check network path |
| High `GetManifest.Errors` but low `Origin.*` | Manifest format issues | Validate manifest format, check MediaTailor compatibility |

### Thresholds
- **🔴 Critical**: `Origin.Errors` or `Timeouts` ≥1000/day
- **🟡 Warning**: `Origin.Errors` or `Timeouts` 100-999/day

### Special Case: WAF False Positives
If using AWS WAF or CDN with security features, `Origin.Errors` may show false positives from security blocks. Consider removing if noisy.

---

## Scenario 5: Manifest Generation Issues

### What It Is
MediaTailor is slow or failing to generate personalized manifests.

### Symptoms
- Player buffering at startup
- Slow channel changes
- Manifest request failures

### Required Metrics
```json
{
  "metrics": [
    "GetManifest.Latency",          // Response time (should be <200ms)
    "GetManifest.Errors",           // Generation failures
    "Origin.Errors",                // Context: is origin the bottleneck?
    "Origin.Timeouts"
  ]
}
```

### Diagnosis Pattern
| **Condition** | **Root Cause** | **Action** |
|--------------|---------------|-----------|
| High `GetManifest.Latency` + High `Origin.*` | Origin bottleneck | Optimize origin, enable CDN caching |
| High `GetManifest.Latency` + Normal `Origin.*` | MediaTailor processing delay | Simplify manifest, reduce personalization complexity |
| High `GetManifest.Errors` | Manifest format issues | Check manifest compatibility |

### Thresholds
- **🔴 Critical**: `GetManifest.Latency` >500ms
- **🟡 Warning**: `GetManifest.Latency` 200-500ms

---

## Scenario 6: Early Ad Break Termination (Live Content)

### What It Is
Live content (sports, news) returns early via SCTE CUE-IN, cutting ad breaks short.

### Symptoms
- Revenue lower than expected
- Ads cut off mid-play
- Inconsistent break durations

### Required Metrics
```json
{
  "metrics": [
    "Avail.Duration",               // Planned break duration
    "Avail.ObservedDuration",       // Actual break duration
    "Avail.FilledDuration",         // Planned filled time
    "Avail.ObservedFilledDuration", // Actual filled time
    "Avail.ObservedFillRate"        // Actual vs planned fill rate
  ]
}
```

### Diagnosis Pattern
| **Condition** | **Root Cause** | **Action** |
|--------------|---------------|-----------|
| `ObservedDuration` < `Duration` | Early CUE-IN (game resumes) | Coordinate with content provider on SCTE timing |
| `ObservedFilledDuration` < `FilledDuration` | Ads cut off | Front-load shorter ads in live content |

### Calculation
```
Revenue Loss = (Avail.Duration - Avail.ObservedDuration) 
               × (Avail.FilledDuration / Avail.Duration)
```

### Thresholds
- **🟡 Warning**: `ObservedDuration` <90% of `Duration` consistently

---

## Recommended Configuration by Workflow

### 1. Direct Campaigns (No Programmatic Backfill)

**Use Case**: GAM direct campaigns, ads only insert during campaign windows.

```json
{
  "metrics": [
    "AdDecisionServer.Ads",
    "AdDecisionServer.Latency",
    "AdDecisionServer.Errors",
    "AdDecisionServer.Timeouts",
    "Avail.Impression",
    "Avail.Duration",
    "Avail.FilledDuration",
    "Origin.Errors",
    "Origin.Timeouts"
  ]
}
```

**Why No Fill Rates?**
- Most breaks have no campaign targeting → structurally low fill rates
- `Avail.FillRate` 14-39% is NORMAL, not failure
- Focus on ADS health and insertion success when ads ARE available

---

### 2. Programmatic with Backfill

**Use Case**: Direct + programmatic, all breaks should fill.

```json
{
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
    "GetManifest.Errors",
    "GetManifest.Latency",
    "Origin.Errors",
    "Origin.Timeouts"
  ]
}
```

**Why Include Fill Rates?**
- With programmatic backfill, 90%+ fill rates are achievable
- Low fill rates indicate ADS configuration or inventory issues
- Fill rates directly correlate to revenue

---

### 3. Live Sports/News with Early CUE-IN

**Use Case**: Live content where breaks often end early.

```json
{
  "metrics": [
    "Avail.Duration",
    "Avail.ObservedDuration",
    "Avail.FilledDuration",
    "Avail.ObservedFilledDuration",
    "Avail.ObservedFillRate",
    "AdDecisionServer.Ads",
    "AdDecisionServer.Latency",
    "AdDecisionServer.Errors",
    "AdDecisionServer.Timeouts",
    "GetManifest.Latency",
    "GetManifest.Errors"
  ]
}
```

**Focus**: Track planned vs observed to quantify revenue loss from early breaks.

---

### 4. Minimal Monitoring (System Health Only)

**Use Case**: Don't care about revenue, just system uptime.

```json
{
  "metrics": [
    "AdDecisionServer.Errors",
    "AdDecisionServer.Timeouts",
    "GetManifest.Errors",
    "Origin.Errors",
    "Origin.Timeouts"
  ]
}
```

**Focus**: Only track failures, ignore fill rates and durations.

---

## Metrics That Are Always Auto-Calculated

These metrics are **derived** from other metrics. If you include their component metrics, the Lambda will auto-calculate them:

| **Derived Metric** | **Requires These Metrics** | **Calculation** |
|-------------------|---------------------------|----------------|
| `Avail.FillRate` | `Avail.Duration` + `Avail.FilledDuration` | (FilledDuration ÷ Duration) × 100 |
| `AdDecisionServer.FillRate` | `AdDecisionServer.Duration` + `Avail.Duration` | (ADS.Duration ÷ Avail.Duration) × 100 |
| `Avail.ObservedFillRate` | `Avail.ObservedDuration` + `Avail.ObservedFilledDuration` | (ObservedFilledDuration ÷ ObservedDuration) × 100 |

**IMPORTANT**: After our fix, these will only be calculated if you **explicitly include them** in the `metrics` array. If you don't want them, don't add them.

---

## AWS Documentation References

- [CloudWatch Metrics](https://docs.aws.amazon.com/mediatailor/latest/ug/monitoring-cloudwatch-metrics.html)
- [CDN Monitoring Best Practices](https://docs.aws.amazon.com/mediatailor/latest/ug/cdn-monitoring.html)
- [Troubleshooting Playback](https://docs.aws.amazon.com/mediatailor/latest/ug/troubleshooting.html)
- [MediaTailor Quotas](https://docs.aws.amazon.com/mediatailor/latest/ug/quotas.html)

---

## Decision Tree: What Metrics Do I Need?

```
START
  |
  ├─> Are ads NOT inserting at all?
  |     YES → Use "Scenario 1: ADS Failures"
  |     NO  → Continue
  |
  ├─> Are ads inserting but fill rates low?
  |     YES → Do you use programmatic backfill?
  |           YES → Use "Scenario 2: Ad Insertion Failures"
  |           NO  → Use "Direct Campaigns" config (remove fill rates)
  |     NO  → Continue
  |
  ├─> Are specific ads failing to play?
  |     YES → Use "Scenario 3: Transcoding Failures"
  |     NO  → Continue
  |
  ├─> Is playback failing entirely?
  |     YES → Use "Scenario 4: Origin Issues" + "Scenario 5: Manifest Issues"
  |     NO  → Continue
  |
  ├─> Is revenue lower than expected (live content)?
  |     YES → Use "Scenario 6: Early Ad Break Termination"
  |     NO  → Use "Minimal Monitoring" config
```

---

## Summary

**Key Principle**: Only monitor metrics relevant to YOUR workflow. Don't cargo-cult the example config.

- **Direct campaigns without backfill** → Remove fill rates, focus on ADS health
- **Programmatic with backfill** → Include fill rates, they indicate revenue
- **Live content** → Track observed vs planned to measure early break impact
- **System health only** → Just track errors and timeouts

**After our fix**, the report will only show metrics you explicitly list in `config.json` — giving you full control.
