#!/usr/bin/env python3
import aws_cdk as cdk
from aws_cdk import Aspects
from cdk_nag import AwsSolutionsChecks
from mediatailor_report.mediatailor_report_stack import MediaTailorReportStack
import sys
import os

try:
    app = cdk.App()
    
    # Get account and region from context or environment variables
    account = app.node.try_get_context("account") or os.environ.get('CDK_DEFAULT_ACCOUNT')
    region = app.node.try_get_context("region") or os.environ.get('CDK_DEFAULT_REGION') or os.environ.get('AWS_REGION')
    
    if not account:
        raise ValueError("Missing required context: 'account' must be provided via context or CDK_DEFAULT_ACCOUNT environment variable")
    if not region:
        raise ValueError("Missing required context: 'region' must be provided via context, CDK_DEFAULT_REGION, or AWS_REGION environment variable")
    
    if not isinstance(account, str) or not account.isdigit():
        raise ValueError("Invalid account format: must be numeric")
    if not isinstance(region, str) or len(region) > 20 or not region.replace('-', '').isalnum():
        raise ValueError("Invalid region format: must be alphanumeric with hyphens")
    
    MediaTailorReportStack(app, "MediaTailorReportStack",
        env=cdk.Environment(
            account=account,
            region=region
        )
    )
    
    # Add AWS Solutions security checks
    Aspects.of(app).add(AwsSolutionsChecks(verbose=True))
    
    app.synth()
    
except Exception as e:
    import traceback
    print(f"Error: CDK application failed - {str(e)}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)