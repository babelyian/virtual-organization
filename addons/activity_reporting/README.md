# Activity Reporting Module

## Overview

The Activity Reporting module provides an intelligent multi-agent system for querying and reporting on current activities across your Odoo organization. It uses the Agno framework to orchestrate specialized agents that can answer questions about employees, projects, tasks, timesheets, and calendar events.

## Architecture

### Multi-Agent System

The module implements a hierarchical multi-agent architecture:

```
User (via Odoo Discussions)
    ↓
Bot User (linked to Orchestrator Agent)
    ↓
Orchestrator Agent
    ├── Employee Agent    (queries hr.employee)
    ├── Todo Agent        (queries todo tasks)
    ├── Project Agent     (queries project.project, project.task)
    ├── Timesheet Agent   (queries account.analytic.line)
    └── Calendar Agent    (queries calendar.event)
```

### Agent Roles

#### Orchestrator Agent
- **Port**: Base port (default: 8000)
- **Role**: Coordinates user queries and delegates to specialized agents
- **Responsibilities**:
  - Parse user questions
  - Determine which subagents to consult
  - Aggregate responses from multiple agents
  - Format final response to user

#### Employee Agent
- **Port**: Base port + 1 (default: 8001)
- **Role**: Employee information specialist
- **Queries**: `hr.employee`, `hr.department`
- **Capabilities**:
  - Employee search and details
  - Department listings
  - Work schedule information

#### Todo Agent
- **Port**: Base port + 2 (default: 8002)
- **Role**: Task management specialist
- **Queries**: Todo task models
- **Capabilities**:
  - Task status tracking
  - Overdue task identification
  - Task assignment reporting

#### Project Agent
- **Port**: Base port + 3 (default: 8003)
- **Role**: Project management specialist
- **Queries**: `project.project`, `project.task`
- **Capabilities**:
  - Project status and progress
  - Task breakdowns
  - Timeline analysis
  - Resource allocation

#### Timesheet Agent
- **Port**: Base port + 4 (default: 8004)
- **Role**: Time tracking specialist
- **Queries**: `account.analytic.line`
- **Capabilities**:
  - Hours tracking and analysis
  - Time allocation by project/employee
  - Utilization reporting

#### Calendar Agent
- **Port**: Base port + 5 (default: 8005)
- **Role**: Calendar and scheduling specialist
- **Queries**: `calendar.event`
- **Capabilities**:
  - Meeting schedules
  - Upcoming events
  - Conflict detection

## Installation

### Prerequisites

1. **Odoo Modules**: Ensure the following modules are installed:
   - `hr` (Employees)
   - `project` (Projects)
   - `hr_timesheet` (Timesheets)
   - `calendar` (Calendar)
   - `agno_agents` (Agno Agent Framework)
   - `agno_user` (Agno Bot Users)

2. **Python Dependencies**:
   ```bash
   pip install agno --break-system-packages
   ```

3. **API Access**: Obtain an API key for the LLM provider (default: aiahura.com)

### Installation Steps

1. Copy the `activity_reporting` directory to your Odoo `addons` folder

2. Update the Odoo addons list:
   ```bash
   odoo-bin -c odoo.conf -u all
   ```

3. Install the module from Odoo:
   - Go to Apps
   - Search for "Current Activity Reporting"
   - Click Install

## Configuration

### Step 1: Create Activity Reporter

1. Navigate to: **Activity Reporting > Reporters**
2. Click **Create**
3. Fill in the configuration:
   - **Name**: e.g., "Main Activity Reporter"
   - **LLM Model**: Select your preferred model (e.g., "Gemma-3 27B")
   - **API Base URL**: `https://chat.aiahura.com/api/v1` (or your provider)
   - **API Key**: Your LLM provider API key
   - **Base Port**: Starting port (default: 8000, must be available)

### Step 2: Create Agents

1. Click the **Create Agents** button
   - This creates the orchestrator and all 5 specialized agents
   - Each agent gets its own configuration and port
   - Status changes to "Configured"

### Step 3: Start Agents

1. Click the **Start Agents** button
   - All agents start in sequence (subagents first, then orchestrator)
   - Each agent runs as a separate process
   - Status changes to "Running"

### Step 4: Create Bot User

1. Click the **Create Bot User** button
   - Creates an Odoo user linked to the orchestrator
   - This user can be added to Discussions channels

### Step 5: Use in Discussions

1. Go to **Discuss** app
2. Create or open a channel
3. Add the bot user to the channel
4. Tag the bot and ask questions!

## Usage Examples

### Example Conversations

**User**: @activity_bot What projects are currently active?

**Bot**: Currently, we have 3 active projects:

1. **Website Redesign** (50% complete)
   - 12 tasks, 8 completed
   - Assigned to: Design Team
   - Deadline: Next month

2. **Mobile App Development** (30% complete)
   - 20 tasks, 6 completed
   - Assigned to: Dev Team
   - Deadline: Q2

3. **Marketing Campaign** (75% complete)
   - 8 tasks, 6 completed
   - Assigned to: Marketing
   - Deadline: This week

---

**User**: @activity_bot How many hours did John work last week?

**Bot**: John's timesheet for last week (Feb 5-11):

- **Total Hours**: 42.5 hours
- **Projects**:
  - Website Redesign: 25 hours
  - Mobile App: 15 hours
  - Admin tasks: 2.5 hours
- **Daily Average**: 8.5 hours

---

**User**: @activity_bot What meetings do I have tomorrow?

**Bot**: Your schedule for tomorrow (Feb 14):

1. **9:00 AM - 10:00 AM**: Team Standup
   - Location: Conference Room A
   - Attendees: Dev Team (8 people)

2. **2:00 PM - 3:30 PM**: Client Presentation
   - Location: Main Office
   - Attendees: Client team + Sales

3. **4:00 PM - 5:00 PM**: 1-on-1 with Manager
   - Location: Manager's Office

---

**User**: @activity_bot Are there any overdue tasks?

**Bot**: Yes, there are 5 overdue tasks:

**High Priority**:
- Fix critical bug (3 days overdue) - Assigned to: Alice
- Review security audit (2 days overdue) - Assigned to: Bob

**Medium Priority**:
- Update documentation (5 days overdue) - Assigned to: Charlie
- Design mockups (1 day overdue) - Assigned to: Diana

**Low Priority**:
- Clean up old files (7 days overdue) - Assigned to: Eve

Would you like me to notify the assignees?

## Advanced Configuration

### Custom Agent Instructions

You can customize agent behavior by editing the agents after creation:

1. Go to **Agno Agents > Agents**
2. Find your agent (e.g., "employee_agent_1")
3. Edit the **Instructions** field to add custom behavior
4. Restart the agent for changes to take effect

### Port Configuration

If you need to change ports (e.g., due to conflicts):

1. Stop all agents
2. Edit the **Base Port** in the Activity Reporter
3. Save the record
4. The system will warn you if ports are already in use
5. Start agents again

### Adding More Subagents

To extend the system with additional specialized agents:

1. Create a new agent in **Agno Agents > Agents**
2. Configure it with appropriate role and instructions
3. Start the agent manually
4. The orchestrator can learn to delegate to it over time

## Troubleshooting

### Agent Not Responding with Data

**Problem**: Agent acknowledges questions but doesn't provide actual data

**Solution**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed solutions.

**Quick Fix**:
1. Go to Agno Agents > Agents
2. Edit the orchestrator agent
3. Update the Agent Role to include sample data
4. Restart the agent

The agent will then respond based on the sample data in its configuration.

### Agents Won't Start

**Problem**: Error when clicking "Start Agents"

**Solutions**:
1. Check if ports are already in use:
   ```bash
   ss -tulpn | grep 8000
   ```
2. Ensure API key is valid
3. Check agent logs in `/tmp/agno_agent_*.log`

### Bot Doesn't Respond

**Problem**: Bot user doesn't reply in Discussions

**Solutions**:
1. Verify orchestrator agent is running (status = "running")
2. Check that bot user is linked to orchestrator
3. Ensure you're mentioning the bot correctly (@bot_name)
4. Check orchestrator logs for errors

### Slow Responses

**Problem**: Bot takes a long time to respond

**Solutions**:
1. Check LLM API response times
2. Reduce `num_history_runs` in agent configuration
3. Consider using a faster model
4. Check network connectivity to LLM provider

### Agent Crashes

**Problem**: Agents stop unexpectedly

**Solutions**:
1. Check logs in `/tmp/agno_agent_*.log`
2. Verify Python dependencies are installed
3. Ensure sufficient system resources
4. Check for API rate limits

## Technical Details

### File Structure

```
activity_reporting/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── activity_reporter.py       # Main model
├── services/
│   ├── __init__.py
│   ├── odoo_tools.py              # Odoo data access tools
│   └── agent_runners.py           # Custom agent runners
├── views/
│   └── activity_reporting_views.xml
├── security/
│   └── ir.model.access.csv
└── data/
    └── activity_reporting_data.xml
```

### Database Structure

**Model**: `activity.reporter`

**Key Fields**:
- `orchestrator_agent_id`: Link to main agent
- `employee_agent_id`: Link to employee specialist
- `todo_agent_id`: Link to todo specialist
- `project_agent_id`: Link to project specialist
- `timesheet_agent_id`: Link to timesheet specialist
- `calendar_agent_id`: Link to calendar specialist
- `bot_user_id`: Link to bot user
- `state`: System status (draft/configured/running/stopped/error)

### Agent Communication

Agents communicate via HTTP:
- **User → Bot**: Through Odoo Discussions
- **Bot → Orchestrator**: HTTP POST to orchestrator endpoint
- **Orchestrator → Subagents**: HTTP POST to subagent endpoints
- **Subagents → Odoo**: Direct database queries via ORM

### Security Considerations

1. **API Keys**: Stored encrypted in Odoo database
2. **Agent Isolation**: Each agent runs in separate process
3. **Port Binding**: Agents bind to 0.0.0.0 (configurable)
4. **Access Control**: Respects Odoo user permissions

## Customization

### Adding Custom Queries

To add custom query capabilities:

1. Edit the appropriate subagent's role/instructions
2. Add new methods to the corresponding Odoo tool (in `odoo_tools.py`)
3. Restart the agent

### Changing LLM Provider

To use a different LLM provider:

1. Update `base_url` and `api_key` in Activity Reporter
2. Ensure the provider uses OpenAI-compatible API
3. Restart all agents

### Multi-Language Support

The agents support multiple languages based on the LLM model:
- User queries in any language
- Responses in the same language as the query
- To force a specific language, add instructions to the orchestrator

## Performance Optimization

### Caching

The agents use SQLite databases to cache:
- Conversation history
- Previous queries and responses
- Session information

### Resource Usage

Typical resource requirements:
- **Memory**: ~500MB per agent (3GB total for all 6 agents)
- **CPU**: Minimal when idle, spikes during inference
- **Network**: Depends on LLM API usage

### Scaling

For large deployments:
1. Run agents on separate servers
2. Use load balancing for multiple orchestrators
3. Implement agent pooling for high traffic
4. Cache frequently requested data

## API Reference

### Orchestrator Endpoints

- `POST /agents/{agent_name}/runs` - Send a query
  - Parameters: `message`, `session_id`, `stream`
  - Returns: Agent response (streamed or complete)

### Subagent Endpoints

Each subagent exposes the same endpoint structure as the orchestrator.

## Support

For issues or questions:
1. Check agent logs in `/tmp/`
2. Review Odoo logs
3. Consult Agno framework documentation
4. Contact your system administrator

## License

LGPL-3

## Credits

- Built on the Agno framework for multi-agent systems
- Integrates with Odoo ERP
- LLM provided by aiahura.com (or your provider)
