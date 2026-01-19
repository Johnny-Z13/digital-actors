#!/bin/bash

# Startup script for antdemo-server
# This script loads environment variables from .env and starts the WebSocket server

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting antdemo-server...${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please create a .env file with your API keys."
    echo "You can copy .env.example to get started:"
    echo "  cp .env.example .env"
    exit 1
fi

# Load environment variables from .env
echo -e "${YELLOW}Loading environment variables from .env...${NC}"
export $(grep -v '^#' .env | grep -v '^$' | xargs)

# Check if ANTHROPIC_API_KEY is set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${RED}Error: ANTHROPIC_API_KEY not set in .env file!${NC}"
    echo "Please add your Anthropic API key to .env"
    exit 1
fi

echo -e "${GREEN}✓ Environment variables loaded${NC}"
echo -e "${GREEN}✓ ANTHROPIC_API_KEY is set${NC}"

# Start the WebSocket server
echo -e "${GREEN}Starting WebSocket server on port 8765...${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

python3 websocket.py
