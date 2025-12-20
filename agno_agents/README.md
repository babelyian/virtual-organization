# Agno Agents Odoo Module

This Odoo module provides integration with Agno AI agents, allowing users to define, configure, and manage AI agents directly from the Odoo interface.

## Features

- ✅ Create and configure Agno agents with custom properties
- ✅ Start and stop agents from Odoo interface
- ✅ Agent status monitoring and management
- ✅ Simple configuration for AI model settings
- ✅ Agents accessible on configurable ports (default: 7777)
- ✅ Support for OpenAI-like model APIs
- ✅ JSON API endpoints for external integration

## Installation Requirements

### 1. Install Agno Library

The module requires the Agno Python library. Install it in your Odoo environment:

```bash
pip install agno
```

### 2. Environment Variables

Set up the required environment variable for API access:

```bash
export API_KEY="your-api-key-here"
```

You can also use different environment variable names by configuring them in the agent settings.

### 3. System Requirements

- Python 3.8 or higher
- Odoo 17.0 or higher
- Internet connection for AI model API access
- Sufficient system resources for running multiple agents

## Installation

1. Copy this module to your Odoo addons directory
2. Update the addons list: `odoo-bin -u all -d your_database --db-filter=your_database`
3. Install the module from Odoo Apps menu

## Usage

### Creating an Agent

1. Navigate to **Agno Agents** menu in Odoo
2. Click **Create** to create a new agent
3. Configure the agent properties:
   - **Agent Name**: Unique identifier
   - **Role**: Description of agent's purpose
   - **Model Settings**: AI model configuration
   - **Advanced Options**: Additional settings

### Starting/Stopping Agents

- Use the **Start Agent** button to activate an agent
- Use the **Stop Agent** button to deactivate an agent
- Monitor agent status in the list view

### Agent Configuration

Each agent can be configured with:

- **Basic Properties**:
  - Agent Name
  - Role description
  - Instructions

- **Model Settings**:
  - Model ID (e.g., "qwen3:latest")
  - Base URL for API
  - API key environment variable name

- **Advanced Settings**:
  - History context settings
  - Debug mode
  - Markdown support
  - Database file configuration

## API Endpoints

The module provides JSON API endpoints for external integration:

- `GET /agno_agents/status` - Get all agents status
- `POST /agno_agents/start/<agent_id>` - Start specific agent
- `POST /agno_agents/stop/<agent_id>` - Stop specific agent
- `GET /agno_agents/agent/<agent_id>/info` - Get agent details

## Example Agent Script

When an agent is started, the module generates and executes a Python script similar to:

```python
import os
from agno.agent import Agent
from agno.models.openai.like import OpenAILike
from agno.os import AgentOS
from agno.db.sqlite import SqliteDb

# Configuration
API_KEY = os.environ.get("API_KEY")
model = OpenAILike(
    id="qwen3:latest",
    base_url="https://chat.aiahura.com/api/v1",
    api_key=API_KEY,
)

# Create agent
agent = Agent(
    name="My Agent",
    role="AI Assistant",
    model=model,
    # ... other configuration
)

# Start AgentOS
agent_os = AgentOS(agents=[agent])
agent_os.serve(host="0.0.0.0", port=7777, reload=False)
```

## Troubleshooting

### Common Issues

1. **Agent fails to start**
   - Check that API_KEY environment variable is set
   - Verify Agno library is installed
   - Check agent configuration

2. **Port already in use**
   - Change the port number in agent configuration
   - Stop conflicting services

3. **Model API errors**
   - Verify API key is correct
   - Check base URL configuration
   - Ensure internet connectivity

### Logs and Debugging

- Enable debug mode in agent configuration
- Check Odoo logs for error messages
- Review agent error messages in the Status & Logs tab

## Support

For issues related to:
- **Agno library**: Check Agno documentation
- **Odoo integration**: Review this module's code and logs
- **AI model APIs**: Consult your AI service provider

## License

This module is licensed under LGPL-3.