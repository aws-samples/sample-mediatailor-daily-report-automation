# Code Review Exclusions

Exclude the following paths from code reviews:

- `.venv/**` - Python virtual environment
- `venv/**` - Python virtual environment
- `node_modules/**` - Node.js dependencies  
- `cdk.out/**` - CDK build artifacts
- `**/__pycache__/**` - Python cache
- `**/*.pyc` - Python compiled files
- `.git/**` - Git metadata
- `.amazonq/**` - Amazon Q configuration
- `dist/**` - Distribution builds
- `build/**` - Build artifacts

Only review application source code:
- `*.py` (application code only)
- `*.sh` (deployment scripts)
- `config/*.json` (configuration files)
- `*.md` (documentation)