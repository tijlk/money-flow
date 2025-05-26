#!/bin/bash

check_status () {
    if [[ ${1} -eq 0 ]] ; then
        echo "${2} succeeded."
        echo ""
    else
        echo "${2} failed, so quitting."
        echo "${3}"
        exit 2
    fi
}

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv not found. Installing uv..."
    brew install uv
    check_status ${?} "Installing uv"
fi

# Delete the virtual environment if it already exists
if [ -d .venv ]; then 
    rm -Rf .venv
    check_status ${?} "Removing existing virtual environment"
fi

# Create virtual environment and install the dependencies
uv sync --all-extras
check_status ${?} "Installing dependencies with uv"

# Install Money Flow package in editable mode
uv pip install -e .[dev]
check_status ${?} "Installing money-flow package in editable mode"

# Install pre-commit hooks
pre-commit install
check_status ${?} "Installing pre-commit hooks"

echo "Setup complete. You can now use the Money Flow package."

