# Quick Start Guide - Activity Reporting

## 5-Minute Setup

### 1. Prerequisites Check
```bash
# Ensure Agno is installed
pip list | grep agno

# If not installed:
pip install agno --break-system-packages
```

### 2. Install Module

1. Copy `activity_reporting` to your Odoo addons directory
2. Restart Odoo
3. Update Apps List: Settings > Apps > Update Apps List
4. Install: Apps > Search "Current Activity Reporting" > Install

### 3. Configure Reporter

**Via UI:**
1. Go to: Activity Reporting > Reporters
2. Click: Create
3. Fill in:
   - Name: "My Activity Reporter"
   - Model: "Gemma-3 27B" (or your choice)
   - API Base URL: `https://chat.aiahura.com/api/v1`
   - API Key: [Your API Key]
   - Base Port: 8000
4. Click: Save

### 4. Create & Start Agents

1. Click: **Create Agents** button (creates 6 agents)
2. Wait for confirmation
3. Click: **Start Agents** button (starts all agents)
4. Wait ~30 seconds for agents to initialize

### 5. Create Bot User

1. Click: **Create Bot User** button
2. Note the bot username (e.g., "activity_bot_1")

### 6. Test in Discussions

1. Open: Discuss app
2. Create new channel or open existing
3. Add participants: Add the bot user
4. Send test message:
   ```
   @activity_bot_1 Hello! What can you help me with?
   ```

### 7. Try Sample Queries

```
@activity_bot_1 Show me all active projects

@activity_bot_1 Who is working on the website redesign project?

@activity_bot_1 What are my upcoming meetings this week?

@activity_bot_1 How many hours did I log yesterday?

@activity_bot_1 Are there any overdue tasks?
```

## Troubleshooting Quick Fixes

### Bot doesn't respond
```bash
# Check agent status
python3 /path/to/activity_reporting/manage_agents.py --status

# Restart agents
python3 /path/to/activity_reporting/manage_agents.py --stop-all
python3 /path/to/activity_reporting/manage_agents.py --start-all
```

### Port conflicts
1. Edit Reporter record
2. Change "Base Port" to different value (e.g., 9000)
3. Stop and restart agents

### Check logs
```bash
# View agent logs
tail -f /tmp/agno_agent_*.log
```

## Command Line Management

```bash
# Status check
python3 manage_agents.py --status

# Start all agents
python3 manage_agents.py --start-all

# Stop all agents
python3 manage_agents.py --stop-all

# List agents
python3 manage_agents.py --list
```

## Next Steps

1. Add sample data to your Odoo modules:
   - Create employees (HR app)
   - Create projects (Project app)
   - Add tasks (Project app)
   - Log timesheets (Timesheets app)
   - Schedule meetings (Calendar app)

2. Customize agent instructions:
   - Go to: Agno Agents > Agents
   - Edit agent instructions for your use case
   - Restart affected agents

3. Monitor performance:
   - Check agent logs
   - Review response times
   - Adjust model if needed

## Common Use Cases

### Daily Standup
```
@bot What did the team work on yesterday?
@bot What meetings do we have today?
@bot Are there any blockers or overdue tasks?
```

### Weekly Report
```
@bot Summarize team activities this week
@bot Show timesheet summary by project
@bot What's the status of all active projects?
```

### Project Management
```
@bot What tasks are assigned to me?
@bot Show progress on the mobile app project
@bot Who's working on what this week?
```

### Resource Planning
```
@bot How are hours distributed across projects?
@bot Who has availability this week?
@bot What's our team's utilization rate?
```

## Tips

- **Be specific**: "Show tasks for project X" works better than "show tasks"
- **Use names**: Mention specific employees, projects, or dates
- **Ask follow-ups**: The bot maintains conversation context
- **Multiple questions**: The orchestrator can handle complex multi-part queries

## Support

For detailed documentation, see the full [README.md](README.md)
