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
            echo "Error: Unknown argument '$1'"
            echo "Usage: $0 [up|down] [--region REGION]"
            exit 1
            ;;
    esac
done

# Validate action parameter (up=deploy, down=destroy)
# Exits with error if invalid action provided
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
    REGION=$(aws configure get region 2>/dev/null || echo "")
    if [ -z "$REGION" ]; then
        REGION="$AWS_REGION"
    fi
fi

if [ -z "$REGION" ]; then
    echo "Error: No region specified. Set AWS_REGION environment variable, configure AWS CLI, or use --region flag"
    exit 1
fi

# Validate region format (basic security check)
if [[ ! "$REGION" =~ ^[a-z0-9-]+$ ]] || [ ${#REGION} -gt 20 ]; then
    echo "Error: Invalid region format: $REGION"
    exit 1
fi

echo "Region: $REGION"

# Check if config.json exists and validate
if [ ! -f "config/config.json" ]; then
    echo "Error: config/config.json not found!"
    echo "Please copy config/config.json.example to config/config.json and update with your values."
    exit 1
fi

# Basic security check for config file
if [ ! -r "config/config.json" ]; then
    echo "Error: Cannot read config/config.json (permission denied)"
    exit 1
fi

# Check file size to prevent excessive memory usage
CONFIG_SIZE=$(stat -f%z "config/config.json" 2>/dev/null || stat -c%s "config/config.json" 2>/dev/null || echo "0")
if [ "$CONFIG_SIZE" -gt 100000 ]; then
    echo "Error: Configuration file too large (${CONFIG_SIZE} bytes, max 100KB)"
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
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
echo "Activating virtual environment..."
if [ ! -f "venv/bin/activate" ]; then
    echo "Error: Virtual environment activation script not found. Virtual environment may be corrupted."
    exit 1
fi

source venv/bin/activate
if [ $? -ne 0 ] || [ -z "$VIRTUAL_ENV" ]; then
    echo "Error: Failed to activate virtual environment. Try removing 'venv' directory and running again."
    exit 1
fi

# Verify Python is available in virtual environment
if ! command -v python &> /dev/null; then
    echo "Error: Python not available in virtual environment"
    exit 1
fi

# Install Python dependencies
echo "Installing dependencies..."
if [ ! -f "requirements.txt" ]; then
    echo "Error: requirements.txt not found!"
    exit 1
fi

pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install Python dependencies. Check requirements.txt and network connectivity."
    exit 1
fi

# Execute action
case $ACTION in
    up)
        # Bootstrap CDK (if first time)
        echo "Bootstrapping CDK (if needed)..."
        ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
        if [ $? -ne 0 ] || [ -z "$ACCOUNT_ID" ]; then
            echo "Error: Failed to get AWS account ID. Check your AWS credentials."
            exit 1
        fi
        
        # Validate account ID format
        if [[ ! "$ACCOUNT_ID" =~ ^[0-9]{12}$ ]]; then
            echo "Error: Invalid AWS account ID format"
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