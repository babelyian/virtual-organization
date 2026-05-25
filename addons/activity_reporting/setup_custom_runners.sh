#!/bin/bash
# Setup script for Activity Reporting with custom runners

echo "======================================"
echo "Activity Reporting Setup"
echo "======================================"
echo

# Find paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACTIVITY_REPORTING_DIR="$SCRIPT_DIR"

echo "Activity Reporting directory: $ACTIVITY_REPORTING_DIR"
echo

# Check if agno_agents exists
AGNO_AGENTS_DIR="$(dirname "$ACTIVITY_REPORTING_DIR")/agno_agents"

if [ ! -d "$AGNO_AGENTS_DIR" ]; then
    echo "ERROR: agno_agents module not found at $AGNO_AGENTS_DIR"
    echo "Please install agno_agents module first"
    exit 1
fi

echo "Found agno_agents at: $AGNO_AGENTS_DIR"
echo

# Backup original runner
ORIGINAL_RUNNER="$AGNO_AGENTS_DIR/services/agno_runner.py"
BACKUP_RUNNER="$AGNO_AGENTS_DIR/services/agno_runner.py.backup"

if [ -f "$ORIGINAL_RUNNER" ] && [ ! -f "$BACKUP_RUNNER" ]; then
    echo "Backing up original runner..."
    cp "$ORIGINAL_RUNNER" "$BACKUP_RUNNER"
    echo "✓ Backup created at $BACKUP_RUNNER"
else
    echo "✓ Backup already exists or original not found"
fi

echo

# Ask user which setup method to use
echo "Choose setup method:"
echo "1) Replace agno_runner.py with custom runner (RECOMMENDED)"
echo "2) Create symlink to custom runner"
echo "3) Show manual instructions only"
echo

read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        echo
        echo "Replacing agno_runner.py..."
        cp "$ACTIVITY_REPORTING_DIR/services/agent_runners.py" "$ORIGINAL_RUNNER"
        echo "✓ Runner replaced successfully"
        echo
        echo "NOTE: Set AGENT_TYPE environment variable to use different runners:"
        echo "  export AGENT_TYPE=orchestrator  # For orchestrator"
        echo "  export AGENT_TYPE=employee      # For employee agent"
        echo "  export AGENT_TYPE=base          # For default agent"
        ;;
    2)
        echo
        echo "Creating symlink..."
        rm -f "$ORIGINAL_RUNNER"
        ln -s "$ACTIVITY_REPORTING_DIR/services/agent_runners.py" "$ORIGINAL_RUNNER"
        echo "✓ Symlink created successfully"
        ;;
    3)
        echo
        echo "Manual Setup Instructions:"
        echo "=========================="
        echo
        echo "1. Backup original runner:"
        echo "   cp $ORIGINAL_RUNNER $BACKUP_RUNNER"
        echo
        echo "2. Replace with custom runner:"
        echo "   cp $ACTIVITY_REPORTING_DIR/services/agent_runners.py $ORIGINAL_RUNNER"
        echo
        echo "3. Set environment variable before starting agents:"
        echo "   export AGENT_TYPE=orchestrator  # or employee, or base"
        echo
        exit 0
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

echo
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo
echo "Next Steps:"
echo "1. Configure Odoo connection in your agents:"
echo "   - Edit agent configuration in Odoo"
echo "   - Set: odoo_url, odoo_database, odoo_username, odoo_password"
echo
echo "2. Stop all existing agents:"
echo "   python3 $ACTIVITY_REPORTING_DIR/manage_agents.py --stop-all"
echo
echo "3. Start employee agent first (with AGENT_TYPE):"
echo "   AGENT_TYPE=employee python3 -m agno_agents..."
echo
echo "4. Start orchestrator agent:"
echo "   AGENT_TYPE=orchestrator python3 -m agno_agents..."
echo
echo "5. Test by asking the bot: 'Who are the employees?'"
echo
echo "For detailed instructions, see:"
echo "  - CUSTOM_RUNNER_SETUP.md"
echo "  - README.md"
echo

