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
import json
import os

class MediaTailorReportStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Load configuration from file
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Use sender email from config
        sender_email = config.get('sender_email', config['recipients'][0])
        
        # SES Email Identity
        email_identity = ses.EmailIdentity(self, "SenderEmailIdentity",
            identity=ses.Identity.email(sender_email)
        )

        # Lambda function using Docker image
        lambda_function = _lambda.DockerImageFunction(self, "MediaTailorReportFunction",
            code=_lambda.DockerImageCode.from_image_asset("lambda"),
            timeout=Duration.minutes(5),
            memory_size=512,
            architecture=_lambda.Architecture.ARM_64,
            environment={
                "REPORT_CONFIG": json.dumps(config),
                "LOG_LEVEL": "INFO"  # Change to DEBUG for development
            },
            log_retention=logs.RetentionDays.ONE_MONTH
        )

        # IAM permissions
        lambda_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "cloudwatch:GetMetricStatistics",
                "cloudwatch:ListMetrics"
            ],
            resources=["*"]
        ))

        lambda_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "ses:SendEmail",
                "ses:SendRawEmail"
            ],
            resources=[email_identity.email_identity_arn]
        ))

        # EventBridge rule for daily trigger
        schedule_config = config.get('schedule', {'hour': '16', 'minute': '0'})
        rule = events.Rule(self, "DailyTrigger",
            schedule=events.Schedule.cron(
                minute=schedule_config['minute'], 
                hour=schedule_config['hour']
            )
        )

        rule.add_target(targets.LambdaFunction(lambda_function))

        # Outputs
        CfnOutput(self, "FunctionName",
            description="Lambda function name",
            value=lambda_function.function_name
        )