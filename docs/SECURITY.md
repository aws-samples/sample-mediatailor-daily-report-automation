# Security

## Overview
This document outlines the security measures and best practices implemented in the MediaTailor Daily Report system.

---

## Security Features

### AWS Solutions Security Validation
- Automated security checks using AWS CDK best practices
- IAM permissions follow least privilege principle
- All findings validated and documented

### Container Security
- Base image pinned to specific SHA256 hash for reproducible builds
- Runs as non-root user (UID 1000)
- Health checks implemented for container monitoring
- Optimized image size with `--no-cache-dir` flag

### Application Security
- Comprehensive input validation and sanitization
- Configuration file size limits (100KB max)
- Email validation with format and length checks
- Resource limits (50 recipients max)
- Sanitized error messages prevent information disclosure
- Log injection prevention

---

## IAM Permissions

### Lambda Execution Role

**CloudWatch Metrics Access**:
- Actions: `cloudwatch:GetMetricStatistics`, `cloudwatch:ListMetrics`
- Resource: `*` (required by CloudWatch API)
- Justification: CloudWatch APIs require wildcard resource and do not support resource-level or namespace-based IAM conditions

**SES Email Sending**:
- Actions: `ses:SendEmail`, `ses:SendRawEmail`
- Resource: Scoped to specific email identity ARN
- Justification: Least privilege - only sender email identity

**CloudWatch Logs**:
- Managed Policy: `AWSLambdaBasicExecutionRole`
- Actions: Log creation and writing
- Justification: AWS managed policy, standard for Lambda functions

---

## Data Protection

### In Transit
- All AWS API communications use TLS encryption
- SES email delivery encrypted in transit

### At Rest
- No sensitive data stored in Lambda environment
- Configuration passed as environment variables
- CloudWatch logs retained for 30 days only

### Logging
- Structured logging with correlation IDs
- Sanitized error messages (no stack traces in production)
- User input sanitized before logging
- Log level configurable (INFO, DEBUG, WARNING, ERROR)

---

## Container Security Details

### Base Image
```dockerfile
FROM public.ecr.aws/lambda/python:3.13-arm64@sha256:40f8c6fafce540a133779e249d6206820c1d62e0442d0bdd9c8e1eb84c3b4eff
```

**Benefits**:
- Reproducible builds
- Protection against upstream changes
- Known security baseline

**Maintenance**: Update hash periodically for security patches

### Health Check
```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import lambda_function"]
```

**Purpose**: Validates Lambda function code integrity

### Non-Root User
- Explicitly set to UID 1000 (non-root user)
- Follows container security best practices
- Prevents privilege escalation attacks

---

## Input Validation

### Configuration File
- JSON format validation
- File size limit: 100KB
- Type checking for all fields
- Required field validation

### Email Addresses
- Format validation (RFC 5322 compliant)
- Length limits (local: 64 chars, domain: 253 chars, total: 254 chars)
- Single @ symbol validation
- Domain validation (must contain dot)

### MediaTailor Configuration Names
- Alphanumeric and limited special characters only
- Length limit: 100 characters
- Sanitization before CloudWatch API calls

### Recipient Count
- Maximum: 50 recipients
- Prevents resource exhaustion

---

## Deployment Security

### CDK Security
- Error handling in CDK application
- Input validation for AWS regions and account IDs
- Build artifacts excluded from version control (`.gitignore`)

### Deployment Script
- Validation for AWS regions
- Account ID format checking
- File size validation
- Error handling with rollback capability

---

## Monitoring and Logging

### CloudWatch Logs
- Retention: 30 days (automatic cleanup)
- Structured logging format
- Correlation IDs for request tracing
- Configurable log levels

### Recommended Monitoring
- Set up CloudWatch alarms for Lambda errors
- Monitor SES bounce and complaint rates
- Track Lambda execution duration
- Review logs regularly for anomalies

---

## Best Practices for Deployment

### Pre-Deployment
1. Review all configuration files for sensitive data
2. Validate email addresses are correct
3. Test in non-production environment first
4. Review IAM permissions

### Post-Deployment
1. Verify SES email identity immediately
2. Test Lambda function manually
3. Monitor CloudWatch logs for errors
4. Check email delivery success

### Ongoing Maintenance
1. Update base image hash quarterly for security patches
2. Review CloudWatch logs weekly
3. Monitor AWS service costs
4. Keep dependencies updated
5. Review IAM permissions periodically

---

## Updating Base Image

When AWS releases security updates:

1. Pull latest image:
   ```bash
   docker pull public.ecr.aws/lambda/python:3.13-arm64
   ```

2. Get new SHA256:
   ```bash
   docker inspect public.ecr.aws/lambda/python:3.13-arm64 --format='{{index .RepoDigests 0}}'
   ```

3. Update `lambda/Dockerfile` with new hash

4. Test and deploy:
   ```bash
   cdk synth
   cdk deploy
   ```

---

## Security Considerations

### AWS Account
- Deploy to non-production accounts for evaluation
- Use separate AWS accounts for dev/test/prod
- Enable AWS CloudTrail for audit logging
- Enable AWS Config for compliance monitoring

### SES Configuration
- Verify sender email immediately after deployment
- Move out of SES sandbox for production use
- Monitor bounce and complaint rates
- Configure SNS notifications for bounces

### Access Control
- Limit AWS console access to authorized users
- Use IAM roles instead of access keys where possible
- Enable MFA for AWS console access
- Review IAM policies regularly

### Network Security
- Lambda runs in AWS-managed VPC (no customer VPC required)
- All communications over HTTPS/TLS
- No inbound network access to Lambda

---

## Incident Response

### If Unauthorized Access Suspected
1. Rotate AWS credentials immediately
2. Review CloudTrail logs for suspicious activity
3. Check Lambda function code for modifications
4. Review SES sending statistics for anomalies
5. Contact AWS Support if needed

### If Email Compromise Suspected
1. Delete SES email identity
2. Review SES sending statistics
3. Check for bounce/complaint spikes
4. Verify configuration file integrity
5. Redeploy with new sender email

---

## Compliance

### Data Residency
- All data processed in AWS region of deployment
- No data transferred outside selected region
- CloudWatch metrics stored in same region

### Data Retention
- CloudWatch logs: 30 days
- No persistent data storage
- Email reports delivered and not stored

### Audit Trail
- All AWS API calls logged via CloudTrail (if enabled)
- Lambda execution logs in CloudWatch
- Structured logging with correlation IDs

---

## Security Checklist

Before deploying to production:

- [ ] Review and understand all IAM permissions
- [ ] Validate configuration file has no sensitive data
- [ ] Test in non-production environment
- [ ] Enable AWS CloudTrail
- [ ] Set up CloudWatch alarms
- [ ] Move SES out of sandbox mode
- [ ] Document incident response procedures
- [ ] Review security best practices
- [ ] Validate email addresses are correct
- [ ] Test email delivery
- [ ] Monitor costs and usage
- [ ] Schedule regular security reviews

---

## Additional Resources

- [AWS Lambda Security Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/lambda-security.html)
- [Amazon SES Security](https://docs.aws.amazon.com/ses/latest/dg/security.html)
- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [Container Security Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/security.html)

---

**Last Updated**: January 2025  
**Review Frequency**: Quarterly or after significant changes
