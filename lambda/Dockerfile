FROM public.ecr.aws/lambda/python:3.13-arm64@sha256:40f8c6fafce540a133779e249d6206820c1d62e0442d0bdd9c8e1eb84c3b4eff

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