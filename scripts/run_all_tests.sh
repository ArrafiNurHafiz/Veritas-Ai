#!/usr/bin/env bash
# Run every check the way its file expects to be run.
# The legacy tests are standalone scripts with top-level assertions, so they
# must not be collected by pytest as a single suite.
set -e
cd "$(dirname "$0")/.."

export VERITAS_DB="" VERITAS_AGENT_URL="" VERITAS_AGENT_TOKEN=""

for test in test_demo test_e2e test_agent_service test_seed test_openapi test_demo_runtime test_enterprise_llm; do
  echo "=== $test ==="
  .venv/bin/python "tests/$test.py"
done

echo "=== enterprise pytest ==="
.venv/bin/python -m pytest tests/test_enterprise_data.py tests/test_enterprise_app.py -q
