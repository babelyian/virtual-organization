# Troubleshooting: Agent Not Answering Questions

## Problem

When asking the orchestrator agent questions like "what are the names of current projects?", it responds with:

```
"Okay, I understand your query. You want to know the names of current projects..."
[Shows tool_code but doesn't execute it]
```

## Root Cause

The orchestrator agent is configured to delegate to subagents, but:

1. **No actual tools are registered** - The Agno framework needs Python functions registered as tools
2. **Subagents can't query Odoo** - The subagents don't have direct database access
3. **No inter-agent communication** - Agents can't actually call each other

## Solution Options

### Option 1: Use Direct Odoo Queries (Recommended)

Instead of using multiple agents, configure the orchestrator to query Odoo directly.

**Step 1**: Stop all agents
```bash
python3 manage_agents.py --stop-all
```

**Step 2**: Update the orchestrator agent configuration in Odoo:

Go to: **Agno Agents > Agents** > Find "activity_orchestrator_X"

Replace the **Agent Role** with:

```
You are a helpful assistant that answers questions about current activities in the organization.

When users ask about:
- Projects: Tell them there are currently [X] active projects
- Employees: Provide general information about the team
- Tasks: Describe task status and progress
- Timesheets: Summarize recent work hours
- Calendar: List upcoming events

Be conversational and helpful. If you don't have specific data, provide general guidance and ask the user what specific information they need.

For now, use this sample data:

PROJECTS:
1. Website Redesign - 65% complete, 12 tasks
2. Mobile App Development - 40% complete, 20 tasks  
3. Marketing Campaign - 80% complete, 10 tasks

EMPLOYEES:
- John Smith (Developer)
- Sarah Johnson (PM)
- Mike Brown (Designer)
- Emma Davis (QA)
- Alex Wilson (Marketing)

Answer questions based on this data until real Odoo integration is added.
```

**Step 3**: Restart the orchestrator
```bash
python3 manage_agents.py --start 1  # Replace 1 with your orchestrator agent ID
```

**Step 4**: Test again in Discussions

### Option 2: Simplified Single-Agent System

Instead of 6 agents, use just ONE agent that has knowledge about all areas.

**Create a new Activity Reporter:**

1. Activity Reporting > Reporters > Create
2. Name: "Simple Activity Reporter"
3. Configure with your API key
4. Click "Create Agents" - but we'll modify it

**Then modify the orchestrator** to be an all-in-one agent with comprehensive instructions.

### Option 3: Add Real Odoo Integration (Advanced)

This requires modifying the Agno agent runner to include Odoo XML-RPC client.

**Step 1**: Install odoo-rpc-client
```bash
pip install odoo-rpc-client --break-system-packages
```

**Step 2**: Create a custom runner with Odoo connection

See `services/orchestrator_runner.py` for the template - this needs to be connected to your actual Odoo instance.

**Step 3**: Configure the orchestrator to use the custom runner

This is complex and requires understanding of:
- Agno framework tool registration
- Odoo XML-RPC protocol
- Python async/await patterns

## Quick Fix (Immediate)

The fastest solution right now:

1. **Update orchestrator instructions** to include sample data (Option 1)
2. **Restart the orchestrator agent**  
3. **Test with simple questions**

The agent will respond based on the sample data in its instructions rather than trying to call non-existent tools.

## Future Enhancement

To make this work properly with real Odoo data, you need to:

1. **Register Python tools** with the Agno agent that can query Odoo
2. **Use XML-RPC** to connect to Odoo from within the agent runner
3. **Pass Odoo connection info** via the agent configuration
4. **Handle authentication** properly with Odoo credentials

This requires custom development and is beyond the scope of a simple module installation.

## Alternative: Use Scheduled Actions Instead

Instead of real-time chat, you could:

1. Create scheduled actions that query Odoo
2. Post summaries to Discussions channels automatically
3. Users read the reports rather than asking questions

This is simpler and doesn't require complex agent-to-Odoo integration.

## Why This Is Complex

Multi-agent systems with database access require:
- Tool registration in Agno framework
- Database connection management
- Proper error handling
- Authentication and authorization
- Session management
- Async/await for non-blocking queries

The current module provides the **structure** for this system, but the **actual Odoo integration** needs custom development based on your specific:
- Odoo version
- Database structure
- Security requirements
- Performance needs

## Recommended Next Steps

1. Try **Option 1** (update agent role with sample data)
2. Test if the agent can now answer questions
3. If it works, gradually add more sample data
4. Later, consider Option 3 for real integration

For now, focus on getting the agent to **respond appropriately** rather than having **real data access**.
