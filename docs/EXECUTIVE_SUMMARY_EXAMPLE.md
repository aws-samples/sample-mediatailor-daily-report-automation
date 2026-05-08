# Executive Summary - Visual Examples

## Overview

For deployments with >10 MediaTailor channels, the report automatically generates an **Executive Summary** showing all channels with their overall status.

---

## Real Example from Testing (3 Channels)

This example shows the executive summary as it appears in actual PDF reports:

### Channel Status Overview Table

![Executive Summary Table](../samples/executive-summary-example.png)

```
┌──────────────────────────┬────────────┬────────┐
│ Channel                  │ Status     │ Issues │
├──────────────────────────┼────────────┼────────┤
│ emt-demo-group           │ ⚪ No Data │   -    │
│ workshop-ssai            │ ⚪ No Data │   -    │
│ fastbite-cooking-ssai    │ ✓ Healthy  │   -    │
└──────────────────────────┴────────────┴────────┘
```

**Status Legend:**
- **⚪ No Data** - Channel has no traffic/activity in monitoring period
- **✓ Healthy** - All metrics within healthy thresholds
- **🟡 Warning (N)** - N metrics in warning range
- **🔴 Critical (N)** - N metrics in critical range

---

## How Channels Are Sorted

Channels appear in **severity order** (most critical first):
1. 🔴 Critical channels (sorted by issue count, then name)
2. 🟡 Warning channels (sorted by issue count, then name)
3. ✓ Healthy channels (alphabetical)
4. ⚪ No Data channels (alphabetical)

This puts **actionable issues at the top** for quick morning health checks.

---

## Scaling Example: 130 Channels

For large deployments, the summary provides instant visibility:

```
Executive Summary: 130 channels monitored.
3 critical, 5 warnings, 122 healthy.
Detailed metrics shown below for channels with issues.

Channel Status Overview
┌──────────────────────────┬─────────────────┬────────┐
│ Channel                  │ Status          │ Issues │
├──────────────────────────┼─────────────────┼────────┤
│ premium-sports-main      │ 🔴 Critical (2) │   2    │  ← Latency + Errors
│ news-live-feed           │ 🔴 Critical (1) │   1    │  ← High errors
│ entertainment-hd         │ 🔴 Critical (1) │   1    │  ← Timeout issues
│                          │                 │        │
│ cooking-channel          │ 🟡 Warning (1)  │   1    │  ← Moderate latency
│ travel-shows             │ 🟡 Warning (2)  │   2    │  ← Minor issues
│ kids-classics            │ 🟡 Warning (1)  │   1    │
│ documentary-hd           │ 🟡 Warning (1)  │   1    │
│ music-videos             │ 🟡 Warning (1)  │   1    │
│                          │                 │        │
│ kids-animation           │ ✓ Healthy       │   -    │
│ sports-replays           │ ✓ Healthy       │   -    │
│ comedy-central           │ ✓ Healthy       │   -    │
│ ... (119 more healthy)   │                 │        │
└──────────────────────────┴─────────────────┴────────┘
```

**Immediate Insights:**
- **3 channels need immediate attention** (Critical)
- **5 channels to review today** (Warning)
- **122 channels operating normally** (Healthy)
- **Scan time: 30 seconds** (vs 30+ minutes without summary)

---

## Detailed Metrics Section

After the executive summary, **only channels with issues** get full metric tables:

```
══════════════════════════════════════════════════════
Detailed Metrics (Issues Only)
──────────────────────────────────────────────────────
For readability, only channels with warnings or critical
issues are shown below. Healthy channels are listed in
the summary table above.

Configuration: premium-sports-main  —  🔴 Critical (2)

  Ad Decision Server Health
  Your ad server responsiveness and error rates...

  ┌───────────────────────────┬─────────┬──────────────┐
  │ Metric                    │ Value   │ Status       │
  ├───────────────────────────┼─────────┼──────────────┤
  │ AdDecisionServer.Latency  │ 2500ms  │ 🔴 Critical  │
  │ AdDecisionServer.Errors   │ 1200    │ 🔴 Critical  │
  │ AdDecisionServer.Ads      │ 450     │ ℹ️ Info      │
  └───────────────────────────┴─────────┴──────────────┘

  Origin Server Health
  ...
```

**122 healthy channels** appear ONLY in the summary table (no detailed sections).

---

## When Does Executive Summary Appear?

| Channel Count | Executive Summary | Detailed Metrics |
|--------------|-------------------|------------------|
| 1-10 channels | ❌ Not shown | All channels (traditional report) |
| 11+ channels | ✅ Shown | Issues only (healthy = summary only) |

**Threshold:** 10 channels (configurable in code if needed)

**Rationale:** 
- Small deployments (≤10): Traditional detailed report works fine
- Large deployments (>10): Summary + filtering prevents information overload

---

## Status Calculation Logic

A channel's overall status is determined by checking **all configured metrics**:

### Metrics That Affect Status

**Health-Critical Metrics:**
- Fill rates: `Avail.FillRate`, `AdDecisionServer.FillRate`, `Avail.ObservedFillRate`
- Latencies: `AdDecisionServer.Latency`, `GetManifest.Latency`
- Errors/Timeouts: `AdDecisionServer.Errors`, `AdDecisionServer.Timeouts`, `GetManifest.Errors`, `Origin.Errors`, `Origin.Timeouts`

**Informational Metrics (Don't Affect Status):**
- Duration metrics: `Avail.Duration`, `Avail.FilledDuration`, etc.
- Volume metrics: `Avail.Impression`, `AdDecisionServer.Ads`

### Thresholds

| Metric Type | Critical | Warning | Healthy |
|------------|----------|---------|---------|
| **Fill Rates** | <70% | 70-79% | ≥80% |
| **ADS Latency** | >2000ms | 1000-2000ms | ≤1000ms |
| **Manifest Latency** | >500ms | 200-500ms | ≤200ms |
| **Error Counts** | ≥1000/day | 100-999/day | <100/day |

### Status Priority (Worst Wins)

```
🔴 Critical (ANY metric critical)
    ↓
🟡 Warning (NO criticals, but has warnings)
    ↓
✓ Healthy (ALL metrics healthy)
    ↓
⚪ No Data (NO metrics have data)
```

---

## Real-World Testing Results

**Test Environment:** 3 MediaTailor channels

**Test Configuration:**
```json
{
  "mediatailor_configs": ["workshop-ssai", "emt-demo-group", "fastbite-cooking-ssai"],
  "metrics": [
    "AdDecisionServer.Ads",
    "AdDecisionServer.Latency",
    "AdDecisionServer.Errors",
    "Avail.Impression",
    "Avail.Duration",
    "Avail.FilledDuration",
    "Origin.Errors",
    "Origin.Timeouts"
  ]
}
```

**Test Results:**
```
Channel: workshop-ssai
├─ AdDecisionServer.Latency: 0ms (no activity)
├─ AdDecisionServer.Errors: 0 (no activity)
├─ Origin.Errors: 0 (no activity)
└─ Status: ⚪ No Data

Channel: emt-demo-group
├─ AdDecisionServer.Latency: 0ms (no activity)
├─ AdDecisionServer.Errors: 0 (no activity)
├─ Origin.Errors: 0 (no activity)
└─ Status: ⚪ No Data

Channel: fastbite-cooking-ssai
├─ AdDecisionServer.Latency: 52.9ms ✓ (< 1000ms)
├─ AdDecisionServer.Errors: 0 ✓ (< 100)
├─ Origin.Errors: 1 ✓ (< 100)
├─ Origin.Timeouts: 1 ✓ (< 100)
└─ Status: ✓ Healthy
```

**PDF Report:**
- Executive summary table: ✅ Appeared correctly
- All 3 channels shown: ✅ In severity order
- Status colors: ✅ Gray for No Data, Green for Healthy
- Issues column: ✅ Shows "-" for channels without issues

---

## Customization

### Change Executive Summary Threshold

**Default:** Executive summary appears for >10 channels

**To Change:** Edit `lambda/lambda_function.py` line ~489:
```python
# Show summary for >50 channels (instead of 10)
if len(report_data) > 50:
    # Executive summary
```

**Recommendation:** Keep at 10 for optimal experience

### Force Executive Summary for Testing

To test with <10 channels, temporarily lower threshold:
```python
# TEMPORARY: For testing
if len(report_data) > 2:
```

**Remember to change back to 10 before production deployment!**

### Show All Details (Disable Issues-Only Filtering)

**To Show Detailed Metrics for ALL Channels (Even >10):**

Edit `lambda/lambda_function.py` line ~603:
```python
# Current: Issues only for large deployments
show_all_details = len(report_data) <= 10

# Force full details always (no filtering)
show_all_details = True
```

**Use Case:** Compliance/audit requirements need complete documentation

---

## Benefits of Executive Summary

### Operational Benefits
- ✅ **Fast triage** - See all channel health in 30 seconds
- ✅ **Issue prioritization** - Critical channels listed first
- ✅ **Morning health check** - Quick scan workflow
- ✅ **Management visibility** - Executive-friendly summary

### Technical Benefits
- ✅ **Manageable PDF size** - 10-20 pages vs 100+ pages
- ✅ **Faster generation** - Less content to render
- ✅ **Smaller emails** - 500KB vs 5-10MB
- ✅ **Better performance** - Quicker load times

### Business Benefits
- ✅ **Actionable reports** - Focus on what matters
- ✅ **Reduced noise** - Healthy channels don't clutter
- ✅ **Better adoption** - Teams actually read the report
- ✅ **Faster response** - Issues identified immediately

---

## Related Documentation

- [SCALING_GUIDE.md](SCALING_GUIDE.md) - Complete scaling best practices
- [THRESHOLDS_GUIDE.md](THRESHOLDS_GUIDE.md) - Why these thresholds?
- [TROUBLESHOOTING_WORKFLOWS.md](TROUBLESHOOTING_WORKFLOWS.md) - Workflow-specific configurations

---

## Feedback

Have suggestions for improving the executive summary? Open an issue on GitHub!
