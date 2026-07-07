# VendorGuard AI

`VendorGuard AI` is a Python ADK multi-agent system designed for automated, intelligent vendor risk assessment and security posture analysis.

## Project Structure

```text
vendorguard-ai/
├── app/                  # Main application package
│   ├── __init__.py
│   └── tools/            # Custom agent tools
│       └── __init__.py
├── ui/                   # Streamlit user interface
├── data/                 # Local data storage, vendor profiles, reports
├── knowledge/            # Retrieval-Augmented Generation (RAG) knowledge bases
├── tests/                # Automated test suites
├── docs/                 # Documentation and architecture diagrams
├── pyproject.toml        # PEP 621 project configuration and dependencies
├── requirements.txt      # Dependency list
├── .env.example          # Template environment variable configuration
├── .pre-commit-config.yaml # Pre-commit hook configuration for security checks
└── semgrep_rules.yml     # Custom Semgrep security rules
```

## Getting Started

### Prerequisites
- Python >= 3.10
- Git

### Installation
1. Clone the repository and navigate to the project directory:
   ```bash
   cd Vendorsguard.ai
   ```
2. Create and activate a virtual environment (if not already done):
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies in editable mode:
   ```bash
   pip install -e .[dev]
   ```

### Environment Configuration
Copy the template configuration file to `.env` and fill in your keys:
```bash
cp .env.example .env
```

## Shift-Left Security

This project enforces security best practices locally before changes are committed.

### Pre-commit Hooks
The pre-commit hooks check for:
- Exposed private keys (`detect-private-key`)
- Hardcoded secrets and credentials (`detect-secrets`)
- Custom security vulnerabilities using Semgrep:
  - Hardcoded Google API keys (`AIza...`)
  - Secret-looking variable assignments (e.g., assigning a string to a variable named 'password' or 'token')
  - Disabling SSL certificate verification (`verify=False`)

To install the git hook scripts:
```bash
pre-commit install
```

To run the checks manually against all files:
```bash
pre-commit run --all-files
```
