import boto3
import base64
from datetime import datetime, timedelta
from typing import Optional

def generate_dashboard_url(config_name: str, region: str = 'us-east-1') -> str:
    """Generate CloudWatch dashboard URL for MediaTailor metrics"""
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=1)
    
    # CloudWatch dashboard widget configuration
    widget_config = {
        "metrics": [
            ["AWS/MediaTailor", "AdAvailFillRate", "ConfigurationName", config_name],
            [".", "AdAvailUtilization", ".", "."],
            [".", "AdAvailRequests", ".", "."],
            [".", "AdAvailImpressions", ".", "."]
        ],
        "period": 300,
        "stat": "Average",
        "region": region,
        "title": f"MediaTailor Metrics - {config_name}",
        "start": start_time.isoformat(),
        "end": end_time.isoformat()
    }
    
    # Encode widget for URL
    import json
    import urllib.parse
    
    widget_json = json.dumps(widget_config)
    encoded_widget = urllib.parse.quote(widget_json)
    
    dashboard_url = f"https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#metricsV2:graph={encoded_widget}"
    
    return dashboard_url

def create_dashboard_link_html(config_name: str) -> str:
    """Create HTML link to CloudWatch dashboard"""
    
    dashboard_url = generate_dashboard_url(config_name)
    
    return f"""
    <div style="margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px;">
        <a href="{dashboard_url}" target="_blank" style="color: #0073bb; text-decoration: none;">
            📊 View {config_name} Dashboard in CloudWatch →
        </a>
    </div>
    """