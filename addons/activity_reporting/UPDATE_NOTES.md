# Activity Reporting v1.1 - Tool Integration Update

## What's Fixed

The agents now have **actual working tools** to query Odoo data and communicate with each other!

### Changes Made

1. **Enhanced Agent Runner** (`services/enhanced_runner.py`)
   - Orchestrator gets `call_agent()` tool to query subagents via HTTP
   - Subagents get real Odoo data access via XML-RPC
   - Tools include: `get_projects()`, `get_project_tasks()`, `get_employees()`, `get_timesheets()`, `get_calendar_events()`

2. **Activity Agent Service** (`services/activity_agent_service.py`)
   - Custom service that uses the enhanced runner
   - Passes agent type and Odoo config to each agent
   - Integrates with existing agno_agents infrastructure

3. **Updated Agent Roles**
   - Orchestrator: Clear instructions on using `call_agent()`
   - Project Agent: Simplified role focused on tool usage
   - All agents: Better prompts for using their specific tools

4. **Odoo Configuration**
   - Added system parameters for Odoo connection
   - Default values: localhost:8069, admin/admin
   - Can be changed in Settings > Technical > Parameters > System Parameters

## How It Works Now

### Orchestrator Flow
```
User: "What are the current projects?"
  ↓
Orchestrator calls: call_agent("project", "List all active projects")
  ↓
HTTP Request to Project Agent (port 8003)
  ↓
Project Agent uses get_projects() tool
  ↓
Tool queries Odoo via XML-RPC
  ↓
Data returned to Project Agent
  ↓
Project Agent formats response
  ↓
Response sent back to Orchestrator
  ↓
Orchestrator presents to user
```

### Direct Subagent Query
```
Orchestrator: "call_agent('project', 'List projects')"
  ↓
Project Agent receives query
  ↓
Calls get_projects() tool
  ↓
Tool executes: search_read('project.project', [('active', '=', True)])
  ↓
Returns formatted list of projects
```

## Installation/Update

### Fresh Install
1. Install module normally
2. Check Odoo connection parameters (Settings > Technical > Parameters)
3. Create Activity Reporter
4. Create Agents
5. Start Agents (they'll use the enhanced runner automatically)
6. Create Bot User
7. Test in Discussions

### Updating Existing Installation
1. Stop all agents
2. Replace module files with new version
3. Restart Odoo
4. Upgrade module (Apps > Activity Reporting > Upgrade)
5. Check/update Odoo connection parameters if needed
6. Start agents again (they'll now use enhanced runner)
7. Test queries

## Configuration

### Odoo Connection Parameters

The agents need credentials to access Odoo data. Configure these in:
**Settings > Technical > Parameters > System Parameters**

1. `activity_reporting.odoo_url` (default: http://localhost:8069)
2. `activity_reporting.odoo_username` (default: admin)
3. `activity_reporting.odoo_password` (default: admin)

**Important:** Use an Odoo user with read access to all relevant models:
- hr.employee
- project.project
- project.task
- account.analytic.line (timesheets)
- calendar.event

## Testing

### Test Project Queries
```
@bot What projects are currently active?
@bot How many tasks does the Website Redesign project have?
@bot List all projects and their task counts
```

### Test Employee Queries  
```
@bot Who are the employees?
@bot List employees in the Engineering department
@bot How many people work here?
```

### Test Timesheet Queries
```
@bot Show timesheet hours for last week
@bot How many hours were logged to the Mobile App project?
@bot Who logged the most hours this week?
```

### Test Calendar Queries
```
@bot What meetings are coming up?
@bot Show events for the next 3 days
@bot Are there any meetings today?
```

### Test Multi-Agent Queries
```
@bot Give me a complete status update
@bot What are John's tasks and how many hours did he log?
@bot Show project status and upcoming project meetings
```

## Troubleshooting

### "Agent returns no data"
- Check Odoo connection parameters
- Verify credentials have read access
- Check agent logs: `/tmp/agno_agent_*.log`
- Test XML-RPC connection:
```python
import xmlrpc.client
common = xmlrpc.client.ServerProxy('http://localhost:8069/xmlrpc/2/common')
uid = common.authenticate('odoo', 'admin', 'admin', {})
print(f"Connected as user {uid}")
```

### "Cannot connect to agent"
- Ensure all agents are running (check ports 8000-8005)
- Check firewall settings
- Review agent startup logs

### "Tool not found" or "call_agent not working"
- Verify using enhanced runner (check logs for "Enhanced")
- Restart agents to ensure they pick up new runner
- Check agent_type is set correctly in config

## What Each Tool Does

### Orchestrator Tools
- `call_agent(agent_type, query)`: Sends query to specialized agent

### Project Agent Tools
- `get_projects()`: Lists all active projects
- `get_project_tasks(project_name)`: Gets tasks for a project

### Employee Agent Tools
- `get_employees(department)`: Lists employees, optionally filtered

### Timesheet Agent Tools
- `get_timesheets(employee, project, days)`: Retrieves timesheet entries

### Calendar Agent Tools
- `get_calendar_events(days_ahead)`: Gets upcoming calendar events

## Technical Details

### XML-RPC Connection
Agents connect to Odoo using XML-RPC protocol:
```python
common = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/object')
records = models.execute_kw(db, uid, password, model, 'search_read', [domain])
```

### Agent Communication
Orchestrator communicates with subagents via HTTP:
```python
requests.post(
    f"http://127.0.0.1:{port}/agents/{agent_name}/runs",
    data={'message': query, 'session_id': session_id}
)
```

### Tool Registration
Tools are registered when agents are created:
```python
agent = Agent(
    ...,
    tools=[get_projects, get_project_tasks]  # Functions passed as tools
)
```

## Known Limitations

1. **Read-Only**: Agents can only READ data, not modify it
2. **No File Access**: Agents cannot access uploaded files
3. **Limited Context**: Each agent call is independent (orchestrator manages context)
4. **Timeout**: Agent calls timeout after 60 seconds
5. **Concurrent Limits**: Subagents process one request at a time

## Future Enhancements

- Add more specialized tools (sales, inventory, etc.)
- Implement caching for frequently requested data
- Add write capabilities (with proper permissions)
- Support for more complex queries
- Integration with external APIs
- Advanced analytics and reporting

## Version History

### v1.1 (Current)
- Added enhanced runner with real tool integration
- Implemented Odoo data access via XML-RPC
- Added agent communication via HTTP
- Updated agent roles and instructions
- Added configuration parameters

### v1.0
- Initial release
- Basic multi-agent structure
- UI and management interfaces
