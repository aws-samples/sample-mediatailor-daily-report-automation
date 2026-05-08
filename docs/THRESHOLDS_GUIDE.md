# MediaTailor Metrics Thresholds Guide

## Overview

This guide explains the alert thresholds used in the MediaTailor Daily Report, including their rationale, AWS documentation sources, and when to adjust them.

---

## Threshold Philosophy

**Default thresholds are designed for:**
- ✅ Production streaming workflows
- ✅ Ad monetization focus (revenue impact)
- ✅ Standard AWS MediaTailor configurations
- ✅ Early warning before user-visible issues

**These thresholds reflect:**
- AWS service quotas and recommendations
- Industry best practices for streaming
- Revenue-impacting performance degradation
- Predictive alerting (catch issues before outages)

---

## Fill Rate Metrics

### Avail.FillRate & AdDecisionServer.FillRate

| Status | Threshold | Rationale |
|--------|-----------|-----------|
| 🔴 Critical | <70% | Significant revenue loss (>30% unfilled inventory) |
| 🟡 Warning | 70-79% | Below industry standard, investigate ADS/inventory |
| ✓ Healthy | ≥80% | Good monetization performance |

**Source:** Industry standard for programmatic advertising

**Why These Numbers?**

**70% Critical Threshold:**
- Losing >30% of potential revenue
- Typically indicates systemic issues:
  - ADS campaign targeting problems
  - Insufficient demand/inventory
  - Technical insertion failures
- In programmatic workflows, should trigger immediate investigation

**80% Healthy Threshold:**
- Industry benchmark for good fill rates
- Programmatic + direct campaigns typically achieve 80-95%
- Balances monetization with user experience

**Important Exceptions:**

⚠️ **Direct Campaigns Without Backfill:**
- Low fill rates (14-50%) are **NORMAL**
- Only targeted breaks get filled
- **Solution:** Remove fill rate metrics from config (see docs/TROUBLESHOOTING_WORKFLOWS.md)

⚠️ **Off-Peak Hours:**
- Lower advertiser demand overnight/weekends
- 60-70% may be acceptable
- Consider time-of-day context

⚠️ **New Campaigns:**
- Initial learning period for programmatic
- May take 24-48h to ramp up
- Don't panic on first day

**When to Adjust:**
- **Higher thresholds (85%/90%):** Premium content with guaranteed backfill
- **Lower thresholds (60%/70%):** Niche content, limited advertiser demand
- **Remove entirely:** Direct campaigns only (no programmatic)

---

## Latency Metrics

### AdDecisionServer.Latency

| Status | Threshold | Rationale |
|--------|-----------|-----------|
| 🔴 Critical | >2000ms | Approaching AWS 3s timeout, high timeout risk |
| 🟡 Warning | 1000-2000ms | Above AWS recommendation, may impact UX |
| ✓ Healthy | ≤1000ms | Within AWS best practice |

**Sources:**
- [AWS MediaTailor Quotas](https://docs.aws.amazon.com/mediatailor/latest/ug/quotas.html) - 3s timeout
- [AWS CDN Monitoring Guide](https://docs.aws.amazon.com/mediatailor/latest/ug/cdn-monitoring.html) - <1000ms recommendation

**Why These Numbers?**

**2000ms Critical:**
- AWS MediaTailor has a **hard 3-second timeout** for ADS requests
- At 2000ms, you're at 67% of timeout (danger zone)
- High likelihood of timeout errors, failed ad insertion
- User-visible impact: slate/blank instead of ads

**1000ms Warning:**
- AWS explicitly recommends ADS response time <1000ms
- Above this: playback startup delays
- Manifest generation slower
- Player buffering more likely

**Healthy ≤1000ms:**
- Fast enough for smooth ad insertion
- No user-visible delays
- Good margin before timeout

**Common Causes of High Latency:**
- ADS server under load
- Network congestion
- Complex targeting/decisioning logic
- Database query slowness in ADS
- Geographic distance (ADS in wrong region)

**Actionable Response:**
```
>2000ms → Immediate action
- Check ADS server load/health
- Review recent ADS config changes
- Consider ADS failover/backup

1000-2000ms → Investigate within 24h
- Analyze ADS query patterns
- Optimize targeting rules
- Consider caching strategies

<1000ms → Healthy, monitor trends
```

---

### GetManifest.Latency

| Status | Threshold | Rationale |
|--------|-----------|-----------|
| 🔴 Critical | >500ms | Severe playback startup delay, buffering likely |
| 🟡 Warning | 200-500ms | Above AWS recommendation, noticeable delay |
| ✓ Healthy | ≤200ms | Fast playback startup |

**Source:** [AWS CDN Monitoring Guide](https://docs.aws.amazon.com/mediatailor/latest/ug/cdn-monitoring.html) - <200ms recommendation

**Why These Numbers?**

**500ms Critical:**
- User-visible startup delay
- Players typically timeout after 1-2s
- Causes buffering, playback failures
- Poor QoE (Quality of Experience)

**200ms Warning:**
- AWS recommends <200ms for good UX
- Above this: startup feels "sluggish"
- Accumulates with player/CDN latency
- May cause mobile playback issues

**Healthy ≤200ms:**
- Instant playback feel
- No user-perceived delay
- Good mobile performance

**Typical Values:**
- Well-optimized: 50-100ms
- Good: 100-200ms
- Acceptable: 200-300ms
- Problem: >300ms

**Common Causes:**
- Origin server slow
- Complex manifest personalization
- MediaTailor processing delay
- CDN cache miss
- Large manifest files

**Optimization Tips:**
- Enable CDN caching for origin manifests
- Simplify ad personalization rules
- Reduce manifest size
- Use regional MediaTailor endpoints

---

## Error Count Metrics

### AdDecisionServer.Errors, AdDecisionServer.Timeouts, GetManifest.Errors, Origin.Errors, Origin.Timeouts

| Status | Threshold | Rationale |
|--------|-----------|-----------|
| 🔴 Critical | ≥1000 errors/day | Systemic failure, significant ad revenue loss |
| 🟡 Warning | 100-999 errors/day | Elevated error rate, investigate cause |
| ✓ Healthy | <100 errors/day | Acceptable baseline (transient issues) |

**Why These Numbers?**

**1000 Errors Critical:**
- At 1000 errors/day = **41 errors/hour** = 1 error every 1.5 minutes
- For high-traffic channels: clear systemic problem
- Significant revenue impact (ads not inserted)
- User experience degradation

**100 Errors Warning:**
- 100 errors/day = **4 errors/hour** = 1 error every 15 minutes
- Above normal baseline
- May indicate intermittent issues
- Worth investigating but not urgent

**<100 Healthy:**
- Normal "noise" level
- Transient network blips
- Occasional ADS hiccups
- Player retries usually handle

**Why Absolute (Not Percentage) Thresholds?**

We use absolute counts because:
- ❌ No denominator available (AdDecisionServer.Ads = ads returned, not requests made)
- ❌ Can't calculate error rate % accurately
- ✅ Absolute thresholds work across traffic levels

**Context Matters:**

For **low-traffic channels** (1000 requests/day):
- 100 errors = 10% error rate → serious problem
- Consider lower thresholds (25/250 instead of 100/1000)

For **high-traffic channels** (1M requests/day):
- 1000 errors = 0.1% error rate → acceptable
- Consider higher thresholds (5000/10000)

**Future Enhancement:**
If AWS exposes request count metrics, we could switch to percentage-based thresholds.

**Common Error Patterns:**

| Error Count | Likely Cause | Action |
|-------------|--------------|--------|
| Sudden spike | ADS outage, config change | Immediate investigation |
| Gradual increase | Growing traffic, degrading ADS performance | Scale ADS resources |
| Consistent daily | Systematic issue (bad config, broken ads) | Root cause analysis |
| Random spikes | Network transient, CDN issues | Monitor, may self-resolve |

---

## Duration Metrics (No Thresholds)

### Avail.Duration, Avail.FilledDuration, AdDecisionServer.Duration, Avail.ObservedDuration, Avail.ObservedFilledDuration

**Status:** Always **ℹ️ Info** (informational only)

**Why No Thresholds?**

These metrics are **context-dependent**:
- High duration = more ad inventory (could be good or bad)
- Low duration = less inventory (could be intentional)
- No universal "healthy" range

**Use Case:**
- Calculate fill rates (numerator/denominator)
- Understand inventory volume
- Compare planned vs observed
- Revenue calculations

**Not Indicators of Health By Themselves**

---

## Volume Metrics (No Thresholds)

### Avail.Impression, AdDecisionServer.Ads

**Status:** Always **ℹ️ Info** (informational only)

**Why No Thresholds?**

Volume is relative to:
- Traffic levels (high traffic = high volume)
- Content type (sports = more breaks)
- Campaign targeting (direct = lower volume)

**Use Case:**
- Sanity check (sudden drop = problem)
- Capacity planning
- Revenue estimation
- Trend analysis

**When Volume = 0:**
- ⚠️ May indicate no traffic
- ⚠️ May indicate no campaigns active
- ⚠️ May indicate insertion failure
- Context required (check other metrics)

---

## Threshold Customization (Future)

Currently, thresholds are **hardcoded** in the Lambda function for simplicity and consistency.

### When Might You Need Custom Thresholds?

**Scenario 1: Premium Content**
- Guaranteed 95%+ fill rates (SLA)
- Tighten: Critical at <90%, Warning at <95%

**Scenario 2: Niche Content**
- Limited advertiser demand
- Relax: Critical at <50%, Warning at <60%

**Scenario 3: Low-Traffic Channels**
- 100 errors = high error rate
- Tighten: Critical at 250, Warning at 50

**Scenario 4: Different ADS Performance**
- Slower ADS infrastructure
- Relax: Critical at 3000ms, Warning at 2000ms

### How to Implement (Manual for Now)

**Edit:** `lambda/lambda_function.py` lines ~640-690

**Example:**
```python
# Current (hardcoded)
if metric == 'Avail.FillRate':
    if rate_percent < 70:
        status_text = "🔴 Critical"

# Custom for premium content
if metric == 'Avail.FillRate':
    if rate_percent < 90:  # Changed from 70
        status_text = "🔴 Critical"
```

**Future Enhancement:**
Add `thresholds` section to `config.json` for customer-specific overrides.

---

## Quick Reference Table

| Metric | Critical | Warning | Healthy | Source |
|--------|----------|---------|---------|--------|
| **Fill Rates** | <70% | 70-79% | ≥80% | Industry standard |
| **ADS Latency** | >2000ms | 1000-2000ms | ≤1000ms | [AWS Quotas](https://docs.aws.amazon.com/mediatailor/latest/ug/quotas.html), [CDN Guide](https://docs.aws.amazon.com/mediatailor/latest/ug/cdn-monitoring.html) |
| **Manifest Latency** | >500ms | 200-500ms | ≤200ms | [CDN Guide](https://docs.aws.amazon.com/mediatailor/latest/ug/cdn-monitoring.html) |
| **Error Counts** | ≥1000/day | 100-999/day | <100/day | Experience-based |
| **Durations** | N/A | N/A | Info only | Context-dependent |
| **Volumes** | N/A | N/A | Info only | Traffic-dependent |

---

## When to Override Defaults

### ✅ Good Reasons to Customize:
- SLA requirements differ from defaults
- Content/traffic characteristics justify different levels
- ADS infrastructure has known performance baseline
- Regulatory/compliance reporting needs

### ❌ Bad Reasons to Customize:
- "Reduce false alarms" by hiding real problems
- Avoiding fixing underlying issues
- Making metrics "always green"
- No understanding of threshold rationale

**Golden Rule:** Thresholds should reflect **business requirements** and **technical reality**, not just make dashboards look good.

---

## Feedback and Evolution

These thresholds are based on:
- AWS official documentation
- Industry best practices
- Customer feedback from deployments

**Have different requirements?**
- Document your use case in GitHub issues
- Share your traffic patterns and SLAs
- Help us understand when defaults don't fit
- Contribute to threshold customization feature

**Future Roadmap:**
1. Document defaults (✅ this guide)
2. Gather customer feedback on threshold needs
3. Implement configurable thresholds in config.json
4. Add preset threshold profiles (premium/standard/niche)
5. Support per-config overrides for mixed workloads
