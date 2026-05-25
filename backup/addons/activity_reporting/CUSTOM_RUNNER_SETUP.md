# How to Use Custom Agent Runners

## Problem
The default `agno_runner.py` doesn't know about Odoo tools or inter-agent communication.

## Solution
We need to modify `agno_agents/services/agno_services.py` to use our custom runners.

## Steps

### 1. Find the runner_path() method

In `/path/to/odoo/addons/agno_agents/services/agno_services.py`, find:

```python
@staticmethod
def runner_path():
    return os.path.join(os.path.dirname(__file__), "agno_runner.py")
```

### 2. Modify to use custom runner based on agent name

Replace with:

```python
@staticmethod
def runner_path():
    # Default runner
    return os.path.join(os.path.dirname(__file__), "agno_runner.py")

@staticmethod
def get_runner_for_agent(agent):
    """Get appropriate runner based on agent type"""
    agent_name = agent.agent_name or ""
    
    # Check if this is an activity reporting agent
    if "activity_orchestrator" in agent_name:
        # Use custom orchestrator runner
        runner_path = "/mnt/extra-addons/activity_reporting/services/agent_runners.py"
        if os.path.exists(runner_path):
            os.environ["AGENT_TYPE"] = "orchestrator"
            return runner_path
    elif "employee_agent" in agent_name:
        # Use custom employee runner
        runner_path = "/mnt/extra-addons/activity_reporting/services/agent_runners.py"
        if os.path.exists(runner_path):
            os.environ["AGENT_TYPE"] = "employee"
            return runner_path
    
    # Default runner for other agents
    return AgnoAgentService.runner_path()
```

### 3. Update start_agent_process to use the custom runner

Find the `start_agent_process` method and change:

```python
runner = cls.runner_path()
```

To:

```python
runner = cls.get_runner_for_agent(agent)
```

### 4. Add Odoo connection config to agent config

In the `write_config` method, add Odoo connection details:

```python
cfg = {
    # ... existing fields ...
    "odoo_url": "http://127.0.0.1:8069",
    "odoo_database": "odoo",
    "odoo_username": "admin",
    "odoo_password": "admin",  # CHANGE THIS!
}
```

## Alternative: Simpler Approach

Instead of modifying agno_services.py, we can:

1. **Copy the runner to the agno_agents module**
2. **Override the default runner**

### Option A: Replace Default Runner (Simplest)

```bash
# Backup original
cp /path/to/addons/agno_agents/services/agno_runner.py /path/to/addons/agno_agents/services/agno_runner.py.bak

# Copy our custom runner
cp /path/to/addons/activity_reporting/services/agent_runners.py /path/to/addons/agno_agents/services/agno_runner.py
```

Then restart agents.

### Option B: Symlink (Linux only)

```bash
cd /path/to/addons/agno_agents/services/
mv agno_runner.py agno_runner.py.bak
ln -s /path/to/addons/activity_reporting/services/agent_runners.py agno_runner.py
```

## Configuration

Add to your agent configuration (in Odoo UI):

**For Employee Agent:**
- In the "Instructions" field, you can leave as is
- The runner will automatically connect to Odoo

**For Orchestrator Agent:**
- Update the "Agent Role" to mention the `ask_employee_agent` tool:

```
You are an Orchestrator Agent for Activity Reporting.

AVAILABLE TOOLS:
1. ask_employee_agent(query: str) - Delegates employee questions to the Employee Agent

When users ask about employees:
1. Call ask_employee_agent() with a clear question
2. Wait for the response
3. Present the information to the user

Example:
User: "Who are the employees?"
You: [Call ask_employee_agent("List all active employees")]
[Present the results]
```

## Testing

1. Stop all agents
2. Start employee agent first (it needs to be running)
3. Start orchestrator agent
4. Ask a question via the bot: "Who are the employees?"

Check logs:
```bash
tail -f /tmp/agno_agent_*.log
```

You should see:
- Employee agent connecting to Odoo
- Employee agent registering tools
- Orchestrator calling employee agent
- Employee agent querying Odoo
- Response flowing back
