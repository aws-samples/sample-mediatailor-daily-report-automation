<div class="title-page">
<h1 style="text-align: center; margin-top: 200px; font-size: 32pt;">MediaTailor Daily Report</h1>
<h2 style="text-align: center; color: #FF9900; font-size: 24pt; border: none;">Installation & Operations Guide</h2>
<p style="text-align: center; margin-top: 100px; font-size: 14pt;">Automated Daily Email Reports for MediaTailor Ad-Fill Rate Metrics</p>
<p style="text-align: center; margin-top: 50px; color: #666;">Version 1.0 - Evaluation Release</p>
</div>

<div class="page-break"></div>

## Important Notice and Disclaimer

### Purpose and Scope

This software is provided as a proof-of-concept for evaluation and educational purposes only. It demonstrates automated reporting capabilities for AWS MediaTailor and serves as a reference implementation for understanding serverless architectures and metrics collection patterns.

### Intended Use

- **Evaluation and Testing**: Assess functionality in non-production environments
- **Educational Resource**: Learn AWS serverless patterns and MediaTailor metrics
- **Reference Implementation**: Starting point for custom solution development
- **Proof of Concept**: Demonstrate automated reporting capabilities

### Important Limitations

**Not Production-Ready**: This software has not undergone rigorous testing and validation required for production workloads. It is not an official AWS product or service.

**No Warranty**: Provided "as is" without warranty of any kind, either express or implied, including but not limited to warranties of merchantability, fitness for a particular purpose, or non-infringement.

**No Support**: No ongoing support, maintenance, updates, or bug fixes are provided.

**Your Responsibility**: You are solely responsible for:
- Testing and validating the software in your environment
- Ensuring compliance with your security and operational policies
- All AWS service costs incurred during deployment and operation
- Any modifications or customizations required for your use case
- Assessing production readiness if considering further development

### Recommendations

1. Deploy only in non-production AWS accounts for evaluation
2. Review all source code before deployment
3. Thoroughly test functionality in your specific environment
4. Monitor AWS service costs during evaluation period
5. Assess against your organization's security and compliance requirements

### Production Use

If you need a production-ready solution, consider engaging with AWS Professional Services or AWS Partners who can provide:
- Production-grade architecture and implementation
- Ongoing support and maintenance
- Security and compliance validation
- Custom feature development
- Service level agreements (SLAs)

### Acknowledgment

By deploying this software, you acknowledge that you have read, understood, and accept these terms and limitations.

<div class="page-break"></div>

## Table of Contents
1. [Important Notice and Disclaimer](#important-notice-and-disclaimer)
2. [Overview](#overview)
3. [Minimum Requirements](#minimum-requirements)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Deployment](#deployment)
7. [Verification](#verification)
8. [CloudWatch Metrics](#cloudwatch-metrics)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance](#maintenance)

<div class="page-break"></div>

## Overview

### What is MediaTailor Daily Report?

MediaTailor Daily Report is an automated serverless solution that generates and delivers daily performance reports for AWS MediaTailor configurations via email. The system monitors ad fill rates, duration metrics, and provides actionable insights for revenue optimization.

### Key Features

- **Automated Daily Reports**: Scheduled email delivery with PDF attachments
- **Comprehensive Metrics**: Fill rates, duration, errors, latency, and more
- **Multi-Configuration Support**: Monitor multiple MediaTailor configurations
- **Revenue-Focused Analytics**: Weighted fill rate calculations for accurate revenue tracking
- **Color-Coded Status Indicators**: Quick identification of performance issues
- **Serverless Architecture**: Cost-effective, scalable, and maintenance-free
- **Professional PDF Reports**: AWS-branded, formatted reports with tables and charts

### Architecture Components

- **AWS Lambda**: Executes report generation logic (Docker container, Python 3.9+)
- **Amazon EventBridge**: Triggers daily report generation on schedule
- **Amazon CloudWatch**: Stores and provides MediaTailor metrics
- **Amazon SES**: Delivers email reports with PDF attachments
- **AWS CDK**: Infrastructure as Code for deployment

### Use Cases

- **Evaluation**: Assess automated reporting capabilities for MediaTailor
- **Proof of Concept**: Demonstrate daily metrics collection and email delivery
- **Testing**: Validate metrics accuracy and report formatting
- **Learning**: Understand MediaTailor metrics and their business impact
- **Reference**: Use as a starting point for custom reporting solutions

**Note**: This is an evaluation tool only. It is not suitable for production use without significant additional development and testing.

---

## Minimum Requirements

### AWS Account Requirements

- **AWS Account**: Active AWS account with administrative access
- **AWS CLI**: Version 2.x or higher installed and configured
- **AWS Credentials**: Configured with appropriate permissions
- **AWS Region**: Any region supporting Lambda, SES, EventBridge, and CloudWatch

### Required AWS Permissions

Your AWS user/role must have permissions for:
- CloudFormation (stack creation/deletion)
- Lambda (function creation, Docker image deployment)
- IAM (role creation for Lambda execution)
- SES (email identity creation and verification)
- EventBridge (rule creation)
- CloudWatch (metrics access, log groups)
- ECR (Docker image repository)
- S3 (CDK bootstrap bucket)

### Local Environment

**Operating System**: macOS, Linux, or Windows (WSL recommended)

**Required Software**:
- **Node.js**: Version 14.x or higher (for AWS CDK)
- **Python**: Version 3.9 or higher
- **pip**: Python package manager
- **AWS CDK**: Version 2.100.0 or higher
- **Docker or Podman**: Container runtime for Lambda deployment

**Disk Space**: Minimum 500 MB for dependencies and Docker images

**Network**: Internet connectivity for AWS API calls and package downloads

### MediaTailor Prerequisites

- **Active MediaTailor Configurations**: At least one MediaTailor configuration publishing metrics to CloudWatch
- **CloudWatch Metrics**: MediaTailor must be actively publishing metrics (verify in CloudWatch console)
- **Configuration Names**: Know the exact names of your MediaTailor configurations

### Email Requirements

- **Sender Email**: Valid email address you control (will be used as sender)
- **Recipient Emails**: Valid email addresses for report recipients
- **SES Verification**: Ability to access sender email inbox for AWS verification link
- **SES Sandbox**: If in SES sandbox mode, recipient emails must also be verified

---

## Installation

### Step 1: Install AWS CLI

**macOS**:
```bash
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
```

**Linux**:
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

**Windows** (PowerShell):
```powershell
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi
```

**Verify Installation**:
```bash
aws --version
# Expected output: aws-cli/2.x.x ...
```

### Step 2: Configure AWS Credentials

```bash
aws configure
```

Provide:
- **AWS Access Key ID**: Your access key
- **AWS Secret Access Key**: Your secret key
- **Default region**: e.g., `us-east-1`
- **Default output format**: `json`

**Verify Configuration**:
```bash
aws sts get-caller-identity
```

### Step 3: Install Node.js and AWS CDK

**Install Node.js** (if not already installed):
- Download from: https://nodejs.org/
- Verify: `node --version` (should be 14.x or higher)

**Install AWS CDK**:
```bash
npm install -g aws-cdk
```

**Verify CDK Installation**:
```bash
cdk --version
# Expected output: 2.x.x or higher
```

### Step 4: Download Application Code

**Option A: Clone from Git Repository** (if available):
```bash
git clone <repository-url>
cd emt-daily-report
```

**Option B: Extract from Archive**:
```bash
unzip emt-daily-report.zip
cd emt-daily-report
```

### Step 5: Verify Directory Structure

```bash
ls -la
```

Expected files:
- `deploy.sh` - Deployment script
- `app.py` - CDK application entry point
- `requirements.txt` - Python dependencies
- `config/` - Configuration directory
- `lambda/` - Lambda function code
- `docs/` - Documentation

---

## Configuration

### Step 1: Create Configuration File

```bash
cd config
cp config.json.example config.json
```

### Step 2: Edit Configuration

Open `config/config.json` in your text editor:

```json
{
  "mediatailor_configs": ["your-config-1", "your-config-2"],
  "metrics": [
    "Avail.FillRate",
    "Avail.Duration",
    "Avail.FilledDuration",
    "AdDecisionServer.FillRate",
    "AdDecisionServer.Ads",
    "AdDecisionServer.Duration",
    "AdDecisionServer.Errors",
    "AdDecisionServer.Timeouts",
    "AdDecisionServer.Latency",
    "Session.Duration",
    "Avail.Impression",
    "Avail.ObservedDuration",
    "Avail.ExpectedDuration",
    "GetManifest.Errors",
    "Origin.Errors"
  ],
  "recipients": ["recipient@yourdomain.com"],
  "sender_email": "mediatailor-reports@yourdomain.com",
  "schedule": {
    "hour": "16",
    "minute": "0"
  }
}
```

### Configuration Parameters

#### mediatailor_configs (Required)
- **Type**: Array of strings
- **Description**: List of MediaTailor configuration names to monitor
- **Example**: `["live-config-1", "vod-config-2"]`
- **How to Find**: AWS Console → MediaTailor → Configurations

#### metrics (Required)
- **Type**: Array of strings
- **Description**: CloudWatch metrics to include in reports
- **Default**: Use the full list provided above
- **Customization**: Remove metrics you don't need

#### recipients (Required)
- **Type**: Array of email addresses
- **Description**: Email addresses that will receive daily reports
- **Example**: `["team@company.com", "manager@company.com"]`
- **Note**: In SES sandbox, these must be verified

#### sender_email (Required)
- **Type**: Email address
- **Description**: Email address reports will be sent from
- **Example**: `"mediatailor-reports@yourdomain.com"`
- **Important**: You must have access to this inbox for verification
- **Note**: Do not use "noreply" addresses as you need to verify the email

#### schedule (Required)
- **Type**: Object with hour and minute
- **Description**: Daily report schedule in UTC time
- **Format**: 24-hour format
- **Examples**:
  - `{"hour": "16", "minute": "0"}` = 4:00 PM UTC
  - `{"hour": "8", "minute": "30"}` = 8:30 AM UTC
  - `{"hour": "0", "minute": "0"}` = Midnight UTC

### Configuration Best Practices

1. **Start Small**: Begin with 1-2 MediaTailor configurations for testing
2. **Time Zone Consideration**: Schedule is in UTC, convert from your local time
3. **Email Domains**: Use corporate email domains you control
4. **Metrics Selection**: Include all metrics initially, remove unused ones later
5. **Multiple Recipients**: Add all stakeholders who need daily reports

---

## Deployment

### Important: Evaluation Deployment

**Recommendation**: Deploy only to non-production AWS accounts for evaluation.

### Step 1: Run Deployment Script

**Default Region** (uses AWS CLI configured region):
```bash
./deploy.sh up
```

**Specific Region**:
```bash
./deploy.sh up --region us-east-1
```

### Step 2: Monitor Deployment

The script will:
1. Create Python virtual environment
2. Install dependencies
3. Bootstrap CDK (first time only)
4. Deploy CloudFormation stack
5. Create Lambda function with Docker container
6. Configure EventBridge schedule
7. Create SES email identity

**Expected Output**:
```
Action: up
Region: us-east-1
Configuration file found: config/config.json
Creating virtual environment...
Installing dependencies...
Bootstrapping CDK (if needed)...
Deploying stack...
✅ MediaTailorReportStack

Deployment completed successfully!
```

**Deployment Time**: 5-10 minutes (first deployment may take longer)

### Step 3: Note Stack Outputs

After deployment, note the CloudFormation outputs:
- Lambda Function Name
- SES Email Identity ARN
- EventBridge Rule Name

---

## Verification

### Step 1: Verify SES Email Identity

**Critical**: You must verify the sender email before reports can be sent.

1. Check the sender email inbox
2. Look for email from AWS SES with subject: "Amazon SES Email Address Verification Request"
3. Click the verification link in the email
4. Confirm you see "Congratulations!" message

**Verification Status Check**:
```bash
aws ses get-identity-verification-attributes \
  --identities mediatailor-reports@yourdomain.com
```

### Step 2: Test Lambda Function

**Manual Invocation**:
```bash
aws lambda invoke \
  --function-name MediaTailorReportStack-MediaTailorReportFunction \
  --cli-binary-format raw-in-base64-out \
  output.json
```

**Check Output**:
```bash
cat output.json
```

Expected: `{"statusCode": 200, "body": "Report sent successfully"}`

### Step 3: Verify Email Delivery

1. Check recipient email inboxes
2. Look for email with subject: "MediaTailor Daily Report - [DATE]"
3. Verify PDF attachment is present
4. Open PDF and verify metrics are displayed

### Step 4: Check CloudWatch Logs

```bash
aws logs tail /aws/lambda/MediaTailorReportStack-MediaTailorReportFunction --follow
```

Look for:
- "Report generation started"
- "Retrieved metrics for configuration: [name]"
- "PDF report generated successfully"
- "Email sent successfully"

---

## CloudWatch Metrics

### MediaTailor Metrics Collected

The application queries the following CloudWatch metrics from the `AWS/MediaTailor` namespace:

#### Fill Rate Metrics

**Avail.FillRate**
- **Description**: Average fill rate percentage across ad breaks
- **Unit**: Percent
- **Interpretation**: Higher is better (target: >85%)
- **Business Impact**: Direct correlation to revenue

**AdDecisionServer.FillRate**
- **Description**: Fill rate from Ad Decision Server perspective
- **Unit**: Percent
- **Use**: Identify if issues are with ADS or MediaTailor

#### Duration Metrics

**Avail.Duration**
- **Description**: Total planned ad break duration
- **Unit**: Milliseconds
- **Use**: Understand total ad inventory available

**Avail.FilledDuration**
- **Description**: Actual duration filled with ads
- **Unit**: Milliseconds
- **Use**: Calculate weighted fill rate and revenue

**Avail.ObservedDuration**
- **Description**: Actual ad break duration that occurred
- **Unit**: Milliseconds
- **Use**: Compare with planned duration for SCTE-35 timing analysis

**Session.Duration**
- **Description**: Total viewer session time
- **Unit**: Milliseconds
- **Use**: Understand viewer engagement

#### Ad Decision Server Metrics

**AdDecisionServer.Ads**
- **Description**: Number of ads returned by ADS
- **Unit**: Count
- **Use**: Verify ADS is responding with ads

**AdDecisionServer.Duration**
- **Description**: Total duration of ads from ADS
- **Unit**: Milliseconds
- **Use**: Compare with filled duration

**AdDecisionServer.Latency**
- **Description**: ADS response time
- **Unit**: Milliseconds
- **Thresholds**: Good (<300ms), Slow (300-500ms), High (>500ms)
- **Use**: Identify performance bottlenecks

**AdDecisionServer.Errors**
- **Description**: Failed ADS requests
- **Unit**: Count
- **Threshold**: Critical if >100 errors
- **Use**: Monitor ADS health

**AdDecisionServer.Timeouts**
- **Description**: Timed out ADS requests
- **Unit**: Count
- **Threshold**: Warning if >50 timeouts
- **Use**: Identify network or ADS performance issues

#### Impression Metrics

**Avail.Impression**
- **Description**: Number of ad impressions served
- **Unit**: Count
- **Use**: Track ad delivery volume

#### Error Metrics

**GetManifest.Errors**
- **Description**: Errors during manifest generation
- **Unit**: Count
- **Use**: Monitor MediaTailor health

**Origin.Errors**
- **Description**: Origin server connectivity issues
- **Unit**: Count
- **Use**: Identify content delivery problems

### Report Status Indicators

The PDF report includes color-coded status indicators:

- **✓ Good (Green)**: Metrics within optimal range
- **🟡 Warning (Yellow)**: Metrics need attention
- **🔴 Critical (Red)**: Immediate action required
- **⚪ No Data (Gray)**: No metrics available
- **⚠️ Check Data**: Data inconsistency detected

### Metric Aggregation

- **Time Window**: 24 hours (previous day)
- **Statistics**: Average (Avg) and Sum
- **Period**: 86400 seconds (1 day)
- **Timezone**: UTC

---

## Troubleshooting

### Common Issues and Solutions

#### Issue: Email Not Received

**Symptoms**: Lambda executes successfully but no email arrives

**Possible Causes**:
1. Sender email not verified in SES
2. Recipient email not verified (if in SES sandbox)
3. Email in spam folder
4. SES sending limits exceeded

**Solutions**:
```bash
# Check SES verification status
aws ses get-identity-verification-attributes \
  --identities your-sender@domain.com

# Check SES sending statistics
aws ses get-send-statistics

# Check Lambda logs for SES errors
aws logs tail \
  /aws/lambda/MediaTailorReportStack-MediaTailorReportFunction \
  --follow
```

**Resolution**:
- Verify sender email by clicking AWS verification link
- If in sandbox, verify recipient emails or request production access
- Check spam/junk folders
- Request SES sending limit increase if needed

#### Issue: No Metrics in Report

**Symptoms**: PDF report shows "No Data" for all metrics

**Possible Causes**:
1. MediaTailor configuration names incorrect
2. No metrics published in last 24 hours
3. Wrong AWS region
4. IAM permissions missing

**Solutions**:
```bash
# Verify MediaTailor configurations exist
aws mediatailor list-playback-configurations

# Check CloudWatch metrics manually
aws cloudwatch get-metric-statistics \
  --namespace AWS/MediaTailor \
  --metric-name Avail.FillRate \
  --dimensions Name=Configuration,Value=your-config-name \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 --statistics Average

# Check Lambda IAM role permissions
aws lambda get-function \
  --function-name MediaTailorReportStack-MediaTailorReportFunction
```

**Resolution**:
- Verify configuration names match exactly (case-sensitive)
- Ensure MediaTailor is actively serving content
- Deploy to correct region where MediaTailor is running
- Verify Lambda has CloudWatch read permissions

#### Issue: Lambda Timeout

**Symptoms**: Lambda execution times out after 5 minutes

**Possible Causes**:
1. Too many MediaTailor configurations
2. CloudWatch API throttling
3. Large number of metrics

**Solutions**:
```bash
# Check Lambda duration in CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda --metric-name Duration \
  --dimensions Name=FunctionName,Value=MediaTailorReportStack-MediaTailorReportFunction \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Maximum
```

**Resolution**:
- Reduce number of configurations in config.json
- Remove unnecessary metrics from configuration
- Contact AWS support to increase CloudWatch API limits

#### Issue: Deployment Fails

**Symptoms**: `./deploy.sh up` fails with errors

**Common Errors**:

**"CDK CLI not found"**:
```bash
npm install -g aws-cdk
```

**"config.json not found"**:
```bash
cp config/config.json.example config/config.json
# Edit config.json with your settings
```

**"Failed to get AWS account ID"**:
```bash
aws configure
# Verify credentials are correct
aws sts get-caller-identity
```

**"Bootstrap failed"**:
```bash
# Manually bootstrap CDK
cdk bootstrap aws://ACCOUNT-ID/REGION
```

#### Issue: Wrong Schedule Time

**Symptoms**: Reports arrive at unexpected time

**Cause**: Schedule is in UTC, not local time

**Solution**:
1. Convert your desired local time to UTC
2. Update config.json schedule
3. Redeploy: `./deploy.sh up`

**Example**: Want reports at 9 AM EST (UTC-5):
```json
{
  "schedule": {
    "hour": "14",
    "minute": "0"
  }
}
```

#### Issue: PDF Formatting Issues

**Symptoms**: PDF report looks incorrect or incomplete

**Solutions**:
```bash
# Check Lambda logs for PDF generation errors
aws logs tail \
  /aws/lambda/MediaTailorReportStack-MediaTailorReportFunction \
  --follow | grep -i pdf

# Verify ReportLab library is installed
aws lambda invoke \
  --function-name MediaTailorReportStack-MediaTailorReportFunction \
  output.json
cat output.json
```

**Resolution**:
- Redeploy to ensure latest code: `./deploy.sh up`
- Check Lambda logs for specific errors
- Verify Docker image built correctly

### Debug Mode

Enable detailed logging:

1. Update Lambda environment variable `LOG_LEVEL` to `DEBUG`
2. Invoke function manually
3. Check CloudWatch logs for detailed execution trace

```bash
# Update log level (via CDK or AWS Console)
# Then invoke
aws lambda invoke \
  --function-name MediaTailorReportStack-MediaTailorReportFunction \
  output.json

# View detailed logs
aws logs tail \
  /aws/lambda/MediaTailorReportStack-MediaTailorReportFunction \
  --follow
```

### Getting Help

**CloudWatch Logs**: Primary source for debugging
```bash
aws logs tail \
  /aws/lambda/MediaTailorReportStack-MediaTailorReportFunction \
  --follow
```

**AWS Support**: For AWS service-specific issues
- SES sending limits
- CloudWatch API throttling
- Lambda execution issues

**Application Issues**: Check logs for error messages and stack traces

---

## Maintenance

### Regular Maintenance Tasks

#### Weekly
- Review CloudWatch logs for errors
- Verify email delivery success rate
- Check SES bounce/complaint rates

#### Monthly
- Review and optimize metrics list
- Update MediaTailor configuration list
- Review Lambda execution costs
- Check CloudWatch log retention

#### Quarterly
- Update dependencies (requirements.txt)
- Review and update AWS CDK version
- Audit IAM permissions
- Review SES sending statistics

### Updating Configuration

**To update MediaTailor configurations or recipients**:

1. Edit `config/config.json`
2. Redeploy: `./deploy.sh up`
3. Verify changes: Test Lambda function

**To change schedule**:

1. Edit `config/config.json` schedule section
2. Redeploy: `./deploy.sh up`
3. Verify EventBridge rule updated

### Updating Application Code

```bash
# Pull latest code
git pull origin main

# Redeploy
./deploy.sh up
```

### Monitoring Costs

**Cost Components**:
- Lambda executions (typically <$1/month)
- SES email sending ($0.10 per 1,000 emails)
- CloudWatch Logs storage (minimal)
- CloudWatch API calls (minimal)

**Monitor Costs**:
```bash
# View Lambda costs in AWS Cost Explorer
# Filter by service: Lambda
# Filter by resource: MediaTailorReportStack-MediaTailorReportFunction
```

### Backup and Disaster Recovery

**What to Backup**:
- `config/config.json` - Configuration file
- Application source code (if modified)

**Recovery Procedure**:
1. Restore configuration file
2. Redeploy: `./deploy.sh up`
3. Verify SES email identity (may need re-verification)
4. Test Lambda function

### Uninstalling

**To remove the application**:

```bash
./deploy.sh down
```

**To remove from specific region**:
```bash
./deploy.sh down --region us-east-1
```

**Manual Cleanup** (if needed):
```bash
# Delete CloudFormation stack
aws cloudformation delete-stack \
  --stack-name MediaTailorReportStack

# Remove SES email identity
aws ses delete-identity \
  --identity mediatailor-reports@yourdomain.com

# Delete CloudWatch log groups
aws logs delete-log-group \
  --log-group-name /aws/lambda/MediaTailorReportStack-MediaTailorReportFunction
```

### Upgrading

**To upgrade to new version**:

1. Backup current configuration
2. Download new version
3. Restore configuration file
4. Run deployment: `./deploy.sh up`
5. Test functionality

---

## Support and Resources

### Documentation
- AWS MediaTailor: https://docs.aws.amazon.com/mediatailor/
- AWS Lambda: https://docs.aws.amazon.com/lambda/
- Amazon SES: https://docs.aws.amazon.com/ses/
- AWS CDK: https://docs.aws.amazon.com/cdk/

### Useful Commands

```bash
# View Lambda function details
aws lambda get-function \
  --function-name MediaTailorReportStack-MediaTailorReportFunction

# List CloudWatch log streams
aws logs describe-log-streams \
  --log-group-name /aws/lambda/MediaTailorReportStack-MediaTailorReportFunction

# Check EventBridge rule
aws events describe-rule \
  --name MediaTailorReportStack-DailyReportRule

# View SES sending statistics
aws ses get-send-statistics

# List MediaTailor configurations
aws mediatailor list-playback-configurations
```

### Best Practices for Evaluation

1. **Non-Production Account**: Always deploy to a test/evaluation AWS account
2. **Review Code**: Examine the source code before deployment
3. **Test Thoroughly**: Validate all functionality in your environment
4. **Monitor Costs**: Track AWS service charges during evaluation
5. **Document Findings**: Note any issues or required modifications
6. **Security Review**: Assess against your security policies
7. **Backup Configuration**: Store config.json securely
8. **Evaluate Fit**: Determine if this meets your requirements before further investment

---

## Appendix

### Sample Report Output

The daily report includes:
- Report date and generation time
- Configuration-specific metrics tables
- Fill rate percentages with status indicators
- Duration metrics (hours/minutes/seconds)
- Error counts and latency measurements
- Color-coded status for quick assessment
- Professional AWS branding

### Metric Calculation Examples

**Weighted Fill Rate**:
```
Weighted Fill Rate = (Avail.FilledDuration / Avail.Duration) × 100
Example: (2000 seconds / 3800 seconds) × 100 = 52.6%
```

**Revenue Efficiency**:
```
Revenue Efficiency = (Avail.FilledDuration / Avail.ObservedDuration) × 100
Example: (2000 seconds / 2500 seconds) × 100 = 80%
```

### Time Zone Conversion Table

| Local Time | UTC Time | Schedule Config |
|------------|----------|-----------------|
| 9 AM EST   | 2 PM     | "hour": "14"    |
| 9 AM PST   | 5 PM     | "hour": "17"    |
| 9 AM GMT   | 9 AM     | "hour": "9"     |
| 5 PM JST   | 8 AM     | "hour": "8"     |

### AWS Service Limits

- **Lambda**: 1000 concurrent executions (default)
- **SES Sandbox**: 200 emails/day, verified recipients only
- **SES Production**: 50,000+ emails/day (request increase)
- **CloudWatch API**: 400 requests/second (GetMetricStatistics)

### Security Considerations

- Lambda execution role follows least privilege principle
- All communications encrypted in transit (TLS)
- No sensitive data stored in Lambda environment
- SES email identity scoped to specific sender
- CloudWatch logs retained for 30 days only
- IAM permissions scoped to specific resources

---

**Document Version**: 1.0 (Evaluation Release)  
**Last Updated**: January 2025  
**Application Version**: Compatible with CDK 2.100.0+  
**AWS Services**: Lambda, SES, EventBridge, CloudWatch, MediaTailor  

**Note**: This solution is for evaluation purposes only. For production deployments, engage with AWS Professional Services or AWS Partners.

