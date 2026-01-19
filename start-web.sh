#!/bin/bash

# Startup script for web-based character chat interface
# This script loads environment variables from .env and starts the web server

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          Digital Actors - AI Characters            ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
echo ""

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
echo ""

# Check if aiohttp is installed
if ! python3 -c "import aiohttp" 2>/dev/null; then
    echo -e "${YELLOW}Installing required dependencies...${NC}"
    pip3 install aiohttp --quiet
    echo -e "${GREEN}✓ Dependencies installed${NC}"
fi

# Start the web server
echo -e "${GREEN}Starting web server...${NC}"
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Server running at: ${CYAN}http://localhost:8080${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}  Open your browser and navigate to:${NC}"
echo -e "${CYAN}  → http://localhost:8080${NC}"
echo ""
echo -e "${YELLOW}  Press Ctrl+C to stop${NC}"
echo ""

python3 web_server.py
