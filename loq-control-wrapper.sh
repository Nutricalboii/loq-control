#!/bin/bash
# LOQ Control Center Shortcut
# This script allows running loq-control from anywhere.

PROJECT_DIR="/home/vaibhavpandit/loq-control"
PYTHON_EXEC="/usr/bin/python3"

# Ensure we are using the correct python environment and paths
export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"

# Run the script with all passed arguments
"$PYTHON_EXEC" "$PROJECT_DIR/loq-control.py" "$@"
