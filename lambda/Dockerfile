FROM public.ecr.aws/lambda/python:3.9-arm64@sha256:22f6cc58f9c71236077768774af97aa2e1661fe530720350cbeecac4ba71dbe5

# Copy requirements and install dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements.txt

# Copy function code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# Explicitly set non-root user (Lambda base image default)
USER 1000

# Health check for container
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import lambda_function"]

# Set the CMD to your handler
CMD ["lambda_function.lambda_handler"]