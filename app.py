#!/usr/bin/env python3
import aws_cdk as cdk
from aws_cdk import Aspects
from cdk_nag import AwsSolutionsChecks
from mediatailor_report.mediatailor_report_stack import MediaTailorReportStack
import sys

try:
    app = cdk.App()
    
    # Validate context values
    account = app.node.try_get_context("account")
    region = app.node.try_get_context("region")
    
    if account and not account.isdigit():
        raise ValueError(f"Invalid account format: {account}")
    if region and (len(region) > 20 or not region.replace('-', '').isalnum()):
        raise ValueError(f"Invalid region format: {region}")
    
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
    print(f"Error: CDK application failed - {str(e)[:100]}", file=sys.stderr)
    sys.exit(1)