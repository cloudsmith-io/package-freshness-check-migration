#!/bin/bash
# Run the example code to demonstrate the package freshness checker

# Ensure we're in the correct directory
cd "$(dirname "$0")"

# Create a Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
  echo "Creating Python virtual environment..."
  python -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
else
  source venv/bin/activate
fi

# Run the example
echo "Running the package freshness example..."
python examples/usage_example.py

# Run the main script with some options
echo ""
echo "Running the full package freshness checker..."
python freshness_checker.py

# Deactivate the virtual environment
deactivate
