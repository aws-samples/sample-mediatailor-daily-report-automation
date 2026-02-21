# Metrics Accuracy Test

Verifies that MediaTailor metrics are accurately retrieved and calculated.

## Prerequisites

- AWS CLI configured with appropriate credentials
- CDK stack deployed
- At least one MediaTailor configuration in `config/config.json`

## Usage

```bash
cd tests
bash test_accuracy.sh
```

## What It Tests

- CloudWatch metrics retrieval
- Weighted fill rate calculation: `(FilledDuration / Duration) × 100`
- Data integrity and precision
- Business metrics validation
- New metrics: Observed duration metrics, GetManifest.Latency, Origin.Timeouts

The test compares Lambda output against direct CloudWatch API queries to ensure accuracy.
