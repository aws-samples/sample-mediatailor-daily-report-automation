# MediaTailor Daily Report - Architecture

## Overview

The MediaTailor Daily Report is a serverless solution that automatically generates and emails daily performance reports for AWS MediaTailor configurations. The system monitors ad fill rates, duration metrics, and provides actionable insights for revenue optimization.

## Architecture Diagram

```mermaid
flowchart TD
    MT["🎬 AWS MediaTailor<br/>Configurations<br/>• Config-1<br/>• Config-2<br/>• Config-N"] 
    CW["📊 Amazon CloudWatch<br/>Metrics Storage<br/>• Fill Rates<br/>• Durations<br/>• ADS Metrics"]
    EB["⏰ Amazon EventBridge<br/>Daily Trigger<br/>Cron: 16:00 UTC<br/>(12 AM UTC+8)"]
    
    LF["⚡ AWS Lambda Function<br/>MediaTailorReportFunction<br/>• Query Metrics<br/>• Generate PDF<br/>• Send Email"]
    
    SES["📧 Amazon SES<br/>Email Service<br/>• PDF Delivery<br/>• Multi Recipients"]
    
    USERS["👥 Email Recipients<br/>• Operations Team<br/>• Management<br/>• Stakeholders"]
    
    MT -->|"Publishes Metrics"| CW
    CW -->|"Stores Data"| EB
    EB -->|"Triggers Daily"| LF
    LF -->|"Queries Metrics"| CW
    LF -->|"Sends Report"| SES
    SES -->|"Delivers Email"| USERS
    
    subgraph "Lambda Processing"
        direction TB
        Q["📈 CloudWatch Query<br/>• Get 24h Metrics<br/>• Calculate Weighted<br/>• Aggregate Data"]
        P["📄 PDF Generation<br/>• ReportLab Library<br/>• AWS Design Colors<br/>• Status Indicators"]
        E["✉️ Email Composition<br/>• MIME Multipart<br/>• PDF Attachment<br/>• HTML Body"]
        
        Q --> P --> E
    end
    
    LF -.-> Q
    
    classDef aws fill:#FF9900,stroke:#232F3E,stroke-width:2px,color:#fff
    classDef service fill:#232F3E,stroke:#FF9900,stroke-width:2px,color:#fff
    classDef process fill:#146EB4,stroke:#232F3E,stroke-width:2px,color:#fff
    classDef user fill:#037F0C,stroke:#232F3E,stroke-width:2px,color:#fff
    
    class MT,CW,EB,SES aws
    class LF service
    class Q,P,E process
    class USERS user
```

## Components

### 1. AWS MediaTailor
- **Purpose**: Source of ad serving metrics
- **Metrics Collected**:
  - `Avail.FillRate` - Average fill rate across ad avails
  - `Avail.Duration` - Total planned ad time
  - `Avail.FilledDuration` - Total filled ad time
  - `AdDecisionServer.FillRate` - ADS fill rate

### 2. Amazon CloudWatch
- **Purpose**: Metrics storage and aggregation
- **Data Points**: 24-hour aggregated metrics
- **Statistics**: Average and Sum values
- **Retention**: Standard CloudWatch retention policies

### 3. Amazon EventBridge
- **Purpose**: Scheduled trigger for daily reports
- **Schedule**: Configurable cron expression (default: 16:00 UTC)
- **Trigger**: Invokes Lambda function daily
- **Reliability**: Built-in retry and error handling

### 4. AWS Lambda Function
- **Runtime**: Python 3.9+ with Docker container
- **Memory**: 512 MB
- **Timeout**: 5 minutes
- **Trigger**: EventBridge scheduled event
- **Dependencies**: ReportLab, Boto3, email libraries

#### Lambda Function Flow:
1. **Configuration Loading**: Read config from environment variables
2. **Metrics Retrieval**: Query CloudWatch for each MediaTailor config
3. **Data Processing**: Calculate weighted fill rates and aggregations
4. **PDF Generation**: Create formatted report with AWS design system
5. **Email Composition**: Build multipart MIME message with PDF attachment
6. **Email Delivery**: Send via Amazon SES

### 5. Amazon SES (Simple Email Service)
- **Purpose**: Email delivery service
- **Features**: 
  - PDF attachment support
  - Multiple recipients
  - Delivery tracking
  - Bounce/complaint handling
- **Requirements**: Verified sender email address

## Data Flow

1. **MediaTailor** generates metrics during ad serving operations
2. **CloudWatch** collects and stores metrics with timestamps
3. **EventBridge** triggers Lambda function on schedule
4. **Lambda** queries CloudWatch for previous 24-hour metrics
5. **Lambda** processes data and generates PDF report
6. **Lambda** sends email via SES with PDF attachment
7. **Recipients** receive daily report with actionable insights

## Security

### IAM Permissions
- **CloudWatch**: `GetMetricStatistics`, `ListMetrics`
- **SES**: `SendEmail`, `SendRawEmail`
- **Logs**: CloudWatch Logs for monitoring

### Network Security
- Lambda runs in AWS managed VPC
- All communications over HTTPS/TLS
- No inbound network access required

### Data Protection
- Metrics data encrypted in transit and at rest
- Email content encrypted during transmission
- No sensitive data stored in Lambda

## Scalability

### Current Limits
- **Lambda**: 5-minute timeout, 512 MB memory
- **SES**: 200 emails/day (sandbox), higher with production access
- **CloudWatch**: Standard API rate limits

### Scaling Considerations
- Multiple MediaTailor configurations supported
- Configurable recipient lists
- Regional deployment flexibility
- Cost scales with usage (serverless)

## Monitoring & Observability

### CloudWatch Logs
- Lambda execution logs
- Error tracking and debugging
- Performance metrics

### CloudWatch Metrics
- Lambda duration and memory usage
- Error rates and success rates
- SES delivery statistics

### Alerting
- Lambda function failures
- SES delivery failures
- CloudWatch API throttling

## Cost Optimization

### Serverless Benefits
- Pay-per-execution model
- No idle resource costs
- Automatic scaling

### Cost Components
- **Lambda**: Execution time and memory
- **SES**: Email sending costs
- **CloudWatch**: Metrics storage and API calls
- **EventBridge**: Rule evaluations

## Deployment

### Infrastructure as Code
- **CDK (Cloud Development Kit)**: TypeScript/Python
- **CloudFormation**: Generated templates
- **Version Control**: Git-based deployment

### Environments
- Single-region deployment
- Configurable via `config.json`
- Environment-specific configurations

## Disaster Recovery

### Backup Strategy
- Configuration stored in version control
- Lambda code in container registry
- CloudWatch metrics retained per AWS policy

### Recovery Procedures
- Redeploy from source code
- Reconfigure SES email verification
- Restore from CloudFormation template

## Future Enhancements

### Potential Improvements
- **Dashboard Integration**: Real-time web dashboard
- **Alert Thresholds**: Configurable alerting rules
- **Historical Trends**: Multi-day trend analysis
- **Custom Metrics**: Additional calculated metrics
- **Multi-Region**: Cross-region metric aggregation