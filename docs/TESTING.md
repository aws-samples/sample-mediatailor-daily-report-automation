# Testing Guide

## Manual Testing

### Basic Test
```bash
# Get function name from CDK output
aws lambda invoke --function-name MediaTailorReportStack-MediaTailorReportFunction output.json
```

### Test with Debug Info
```bash
# Test with additional logging
aws lambda invoke --function-name MediaTailorReportStack-MediaTailorReportFunction \
  --payload '{"test": true}' \
  output.json
```

### View Results
```bash
# Check the output
cat output.json

# Check CloudWatch logs
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/MediaTailorReportStack"
```

## Testing Methods

### 1. End-to-End Testing
- **Purpose**: Validate complete report generation and delivery
- **Method**: Manual Lambda invoke
- **Expected**: PDF report sent to configured recipients
- **Validation**: Check email inbox and CloudWatch logs

### 2. Debug Mode Testing
- **Purpose**: Detailed logging and response data
- **Method**: Invoke with `{"test": true}` payload
- **Expected**: Additional logging and metric data in response
- **Use Case**: Troubleshooting and development

### 3. Configuration Testing
- **Purpose**: Validate different MediaTailor configurations
- **Method**: Update `config.json` with test configurations
- **Expected**: Reports for each configured MediaTailor setup
- **Validation**: Verify metrics for each configuration

### 4. Schedule Testing
- **Purpose**: Verify EventBridge trigger functionality
- **Method**: Wait for scheduled execution or modify cron
- **Expected**: Automatic report generation at scheduled time
- **Monitoring**: CloudWatch Events and Lambda logs

## Test Scenarios

### Single Configuration
```json
{
  "mediatailor_configs": ["test-config-1"],
  "recipients": ["test@example.com"]
}
```

### Multiple Configurations
```json
{
  "mediatailor_configs": ["config-1", "config-2", "config-3"],
  "recipients": ["team@example.com"]
}
```

### Different Time Zones
```json
{
  "schedule": {
    "hour": "8",
    "minute": "30"
  }
}
```

## Validation Checklist

- [ ] Lambda function executes without errors
- [ ] CloudWatch metrics are retrieved successfully
- [ ] PDF report is generated with correct data
- [ ] Email is sent to all configured recipients
- [ ] Report contains expected metrics and formatting
- [ ] Status indicators show correct thresholds
- [ ] Weighted fill rate calculations are accurate
- [ ] Schedule triggers function at correct time

## Troubleshooting Tests

### Missing Metrics Test
- **Setup**: Configure non-existent MediaTailor config
- **Expected**: Graceful error handling, partial report generation
- **Validation**: Check error logs, ensure other configs still process

### SES Delivery Test
- **Setup**: Use unverified email address
- **Expected**: SES error in logs, function continues
- **Validation**: Check SES bounce/complaint notifications

### Memory/Timeout Test
- **Setup**: Configure many MediaTailor configs
- **Expected**: Function completes within timeout limits
- **Validation**: Monitor Lambda duration and memory usage

## Best Practices

1. **Start Small**: Test with single configuration first
2. **Verify SES**: Ensure sender email is verified in SES
3. **Check Permissions**: Validate IAM roles have required permissions
4. **Monitor Logs**: Always check CloudWatch logs for detailed execution info
5. **Test Schedule**: Verify EventBridge rule triggers at expected time
6. **Validate Data**: Compare report metrics with CloudWatch console