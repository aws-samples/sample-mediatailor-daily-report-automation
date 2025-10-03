#!/bin/bash

# Deploy MediaTailor Daily Report with CDK
# Usage: ./deploy.sh [action] [--region REGION]
# Actions: up (default), down
# Examples: 
#   ./deploy.sh up
#   ./deploy.sh down --region us-west-2

# Parse arguments
ACTION=${1:-up}
REGION=""

# Parse flags
while [[ $# -gt 0 ]]; do
    case $1 in
        --region)
            REGION="$2"
            shift 2
            ;;
        up|down)
            ACTION="$1"
            shift
            ;;
        *)
            shift
            ;;
    esac
done

case $ACTION in
    up|down)
        echo "Action: $ACTION"
        ;;
    *)
        echo "Error: Invalid action '$ACTION'. Use: up or down"
        exit 1
        ;;
esac

# Get region from AWS configuration if not specified
if [ -z "$REGION" ]; then
    REGION=$(aws configure get region 2>/dev/null || echo "$AWS_REGION")
fi

if [ -z "$REGION" ]; then
    echo "Error: No region specified. Set AWS_REGION environment variable, configure AWS CLI, or use --region flag"
    exit 1
fi

echo "Region: $REGION"

# Check if config.json exists
if [ ! -f "config/config.json" ]; then
    echo "Error: config/config.json not found!"
    echo "Please copy config/config.json.example to config/config.json and update with your values."
    exit 1
fi

echo "Configuration file found: config/config.json"

# Check if CDK CLI is installed
if ! command -v cdk &> /dev/null; then
    echo "CDK CLI not found. Install it first: npm install -g aws-cdk"
    exit 1
fi

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install Python dependencies"
    exit 1
fi

# Execute action
case $ACTION in
    up)
        # Bootstrap CDK (if first time)
        echo "Bootstrapping CDK (if needed)..."
        ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        if [ $? -ne 0 ]; then
            echo "Error: Failed to get AWS account ID. Check your AWS credentials."
            exit 1
        fi

        cdk bootstrap "aws://${ACCOUNT_ID}/${REGION}"
        if [ $? -ne 0 ]; then
            echo "Error: CDK bootstrap failed"
            exit 1
        fi

        # Deploy stack
        echo "Deploying stack..."
        cdk deploy --context region="$REGION" --require-approval never
        if [ $? -ne 0 ]; then
            echo "Error: CDK deployment failed"
            exit 1
        fi
        echo "Deployment completed successfully!"
        ;;
    down)
        echo "Destroying stack..."
        cdk destroy --context region="$REGION" --force
        if [ $? -ne 0 ]; then
            echo "Error: CDK destroy failed"
            exit 1
        fi
        echo "Stack destroyed successfully!"
        ;;
esac