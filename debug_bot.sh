#!/bin/bash
# Debug script for the JAPA bot

# Check if token is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <telegram_token>"
  echo "Example: $0 12345678:ABCDEfghIJKLmnopQRSTuvwxYZ"
  exit 1
fi

TOKEN=$1

echo "Starting JAPA bot in debug mode..."
echo "Log file: japa.log"
echo ""
echo "Token: ${TOKEN:0:5}...${TOKEN: -5}"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run the bot with debug flag
python src/main.py --config config.json --token "$TOKEN" --debug

# Exit with the same status as the Python script
exit $? 