#!/usr/bin/env python3
import aws_cdk as cdk
from mediatailor_report.mediatailor_report_stack import MediaTailorReportStack

app = cdk.App()

MediaTailorReportStack(app, "MediaTailorReportStack",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-east-1"
    )
)

app.synth()