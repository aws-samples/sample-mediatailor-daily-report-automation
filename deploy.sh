#!/bin/bash

# Deploy MediaTailor Daily Report with CDK

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

# Bootstrap CDK (if first time)
echo "Bootstrapping CDK (if needed)..."
cdk bootstrap

# Deploy stack
echo "Deploying stack..."
cdk deploy --require-approval never