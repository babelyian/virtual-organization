#!/bin/bash

# Installation script for Agno Agents Odoo Module
echo "Installing requirements for Agno Agents module..."

# Install Agno library
echo "Installing Agno library..."
pip install agno

if [ $? -eq 0 ]; then
    echo "✅ Agno library installed successfully"
else
    echo "❌ Failed to install Agno library"
    exit 1
fi

# Check if API_KEY is set
if [ -z "$API_KEY" ]; then
    echo "⚠️  WARNING: API_KEY environment variable is not set."
    echo "   Please set it using: export API_KEY='your-api-key-here'"
    echo "   You can add this to your ~/.bashrc or ~/.profile for persistence"
else
    echo "✅ API_KEY environment variable is set"
fi

echo ""
echo "Installation completed!"
echo ""
echo "Next steps:"
echo "1. Install the module in Odoo through Apps menu"
echo "2. Configure your agents in 'Agno Agents' menu"
echo "3. Set API_KEY environment variable if not already done"
echo "4. Start your agents to make them accessible on port 7777"