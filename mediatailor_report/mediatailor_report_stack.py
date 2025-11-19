from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_ses as ses,
    aws_logs as logs,
    CfnOutput
)
from constructs import Construct
from cdk_nag import NagSuppressions
import json
import os

class MediaTailorReportStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Load configuration from file
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.json')
        
        try:
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Configuration file not found: {config_path}. Please copy config.json.example to config.json and update with your settings.")
            
            # Validate file size to prevent excessive memory usage
            file_size = os.path.getsize(config_path)
            if file_size > 100000:  # 100KB limit
                raise ValueError(f"Configuration file too large: {file_size} bytes")
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if not isinstance(config, dict):
                    raise ValueError("Configuration must be a JSON object")
                
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in configuration file {config_path}")
        except PermissionError:
            raise PermissionError(f"Permission denied reading configuration file: {config_path}")
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        except Exception:
            raise RuntimeError(f"Failed to load configuration from {config_path}")
        
        # Validate required configuration
        required_fields = ['recipients']
        for field in required_fields:
            if field not in config or not config[field]:
                raise ValueError(f"Missing required configuration field: {field}")
        
        # Validate recipients list
        if not isinstance(config['recipients'], list) or not config['recipients']:
            raise ValueError("Recipients must be a non-empty list of email addresses")
        if len(config['recipients']) > 50:
            raise ValueError("Too many recipients (maximum 50 allowed)")
        
        # Use sender email from config with proper validation
        sender_email = config.get('sender_email')
        if not sender_email:
            sender_email = config['recipients'][0]
        
        # Basic email validation with security checks
        def validate_email(email):
            if not isinstance(email, str) or len(email) > 254:
                return False
            if email.count('@') != 1:
                return False
            local, domain = email.split('@')
            if not local or not domain or len(local) > 64:
                return False
            return '.' in domain and len(domain) <= 253
        
        if not validate_email(sender_email):
            raise ValueError("Invalid sender email format")
        
        for i, recipient in enumerate(config['recipients']):
            if not validate_email(recipient):
                raise ValueError(f"Invalid recipient email format at index {i}")
            if len(config['recipients']) > 50:  # Limit recipient count
                raise ValueError("Too many recipients (max 50)")
        
        # SES Email Identity
        email_identity = ses.EmailIdentity(self, "SenderEmailIdentity",
            identity=ses.Identity.email(sender_email)
        )

        # Lambda function using Docker image
        try:
            lambda_function = _lambda.DockerImageFunction(self, "MediaTailorReportFunction",
                code=_lambda.DockerImageCode.from_image_asset("lambda"),
                timeout=Duration.minutes(5),
                memory_size=512,
                architecture=_lambda.Architecture.ARM_64,
                environment={
                    "REPORT_CONFIG": json.dumps(config),
                    "LOG_LEVEL": "INFO"  # Change to DEBUG for development
                },
                log_group=logs.LogGroup(self, "MediaTailorReportFunctionLogGroup",
                    retention=logs.RetentionDays.ONE_MONTH
                )
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create Lambda function: {str(e)}") from e

        # IAM permissions - CloudWatch GetMetricStatistics doesn't support resource-level permissions
        lambda_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "cloudwatch:GetMetricStatistics",
                "cloudwatch:ListMetrics"
            ],
            resources=["*"]
        ))
        
        # cdk-nag suppressions
        NagSuppressions.add_resource_suppressions(
            lambda_function,
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "AWSLambdaBasicExecutionRole is AWS managed policy for Lambda CloudWatch Logs access - standard practice for Lambda functions",
                    "appliesTo": ["Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "CloudWatch GetMetricStatistics/ListMetrics APIs require Resource:* per AWS API design. CloudWatch does not support resource-level or namespace-based IAM conditions for these actions.",
                    "appliesTo": ["Resource::*"]
                }
            ],
            apply_to_children=True
        )

        lambda_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "ses:SendEmail",
                "ses:SendRawEmail"
            ],
            resources=[email_identity.email_identity_arn]
        ))

        # EventBridge rule for daily trigger
        try:
            schedule_config = config.get('schedule', {'hour': '16', 'minute': '0'})
            
            # Validate schedule configuration
            if not isinstance(schedule_config, dict):
                raise ValueError("Schedule configuration must be a dictionary")
            if 'hour' not in schedule_config or 'minute' not in schedule_config:
                raise ValueError("Schedule must contain 'hour' and 'minute' keys")
            
            hour = str(schedule_config['hour'])
            minute = str(schedule_config['minute'])
            
            # Validate cron values
            if not hour.isdigit() or not (0 <= int(hour) <= 23):
                raise ValueError(f"Invalid hour value: {hour} (must be 0-23)")
            if not minute.isdigit() or not (0 <= int(minute) <= 59):
                raise ValueError(f"Invalid minute value: {minute} (must be 0-59)")
            
            rule = events.Rule(self, "DailyTrigger",
                schedule=events.Schedule.cron(minute=minute, hour=hour)
            )
            rule.add_target(targets.LambdaFunction(lambda_function))
        except Exception as e:
            raise RuntimeError(f"Failed to create EventBridge rule: {str(e)}") from e

        # Outputs
        CfnOutput(self, "FunctionName",
            description="Lambda function name",
            value=lambda_function.function_name
        )