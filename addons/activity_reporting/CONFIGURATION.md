# Activity Reporting Configuration Examples

## Example 1: Basic Setup with Gemma-3

```json
{
  "name": "Activity Reporter - Production",
  "model_name": "gemma-3:27b",
  "base_url": "https://chat.aiahura.com/api/v1",
  "api_key": "your-api-key-here",
  "base_port": 8000
}
```

## Example 2: High Performance Setup

```json
{
  "name": "Activity Reporter - High Performance",
  "model_name": "Qwen3-Instruct:30b",
  "base_url": "https://chat.aiahura.com/api/v1",
  "api_key": "your-api-key-here",
  "base_port": 8000
}
```

## Example 3: Cost-Optimized Setup

```json
{
  "name": "Activity Reporter - Budget",
  "model_name": "gpt-oss:20b",
  "base_url": "https://chat.aiahura.com/api/v1",
  "api_key": "your-api-key-here",
  "base_port": 8000
}
```

## Port Allocation

The system automatically allocates ports starting from `base_port`:

| Agent                | Port Offset | Default Port |
|---------------------|-------------|--------------|
| Orchestrator        | +0          | 8000         |
| Employee Agent      | +1          | 8001         |
| Todo Agent          | +2          | 8002         |
| Project Agent       | +3          | 8003         |
| Timesheet Agent     | +4          | 8004         |
| Calendar Agent      | +5          | 8005         |

## Custom Agent Instructions

### Orchestrator - More Detailed Responses

Edit the orchestrator agent and add to instructions:

```
When responding to users:
- Always provide detailed explanations
- Include relevant context and background
- Suggest follow-up actions
- Format responses with clear sections and bullet points
```

### Employee Agent - Privacy-Focused

Edit the employee agent and add to instructions:

```
Privacy rules:
- Never share personal contact information (phone, email) unless explicitly requested
- Only share work-related information
- Respect organizational hierarchy
```

### Project Agent - Metrics-Focused

Edit the project agent and add to instructions:

```
When reporting on projects:
- Always include percentage completion
- Highlight critical path items
- Show resource allocation
- Flag any projects behind schedule
```

### Timesheet Agent - Billing Focus

Edit the timesheet agent and add to instructions:

```
When analyzing timesheets:
- Categorize hours as billable vs non-billable
- Calculate hourly rates where applicable
- Show cost breakdowns by project
- Flag any unusual time entries
```

## Environment-Specific Configurations

### Development Environment

```python
# Less strict, faster responses
{
  "model_name": "gpt-oss:20b",  # Faster model
  "debug_mode": True,
  "num_history_runs": 3,  # Less context
}
```

### Production Environment

```python
# More accurate, detailed responses
{
  "model_name": "Qwen3-Instruct:30b",  # Better model
  "debug_mode": False,
  "num_history_runs": 10,  # More context
}
```

## Advanced: Custom Subagent

To add a custom subagent (e.g., for Sales data):

1. Create the agent manually in Odoo:
   - Name: `sales_agent_1`
   - Role: "Sales data specialist"
   - Port: 8006 (base_port + 6)

2. Update orchestrator instructions:
```
You have access to these subagents:
...existing agents...
- Sales Agent: Handles sales orders, invoices, and customer data
```

3. Start the custom agent

4. The orchestrator will learn to use it based on user queries

## Firewall Configuration

If agents are accessed from external networks:

```bash
# Allow agent ports (example for base_port=8000)
sudo ufw allow 8000:8005/tcp comment 'Activity Reporting Agents'

# Or for specific IPs only
sudo ufw allow from 192.168.1.0/24 to any port 8000:8005
```

## Nginx Reverse Proxy (Optional)

To expose agents through Nginx:

```nginx
# /etc/nginx/sites-available/activity-agents

upstream orchestrator {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name agents.yourdomain.com;
    
    location /orchestrator/ {
        proxy_pass http://orchestrator/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;
    }
}
```

## Docker Deployment

Example Dockerfile for containerized deployment:

```dockerfile
FROM python:3.11-slim

# Install dependencies
RUN pip install agno odoo-client

# Copy module
COPY activity_reporting /opt/odoo/addons/activity_reporting

# Expose ports
EXPOSE 8000-8005

# Environment variables
ENV ODOO_URL=http://odoo:8069
ENV API_KEY=your-api-key

CMD ["python3", "-m", "activity_reporting.services.agent_runners"]
```

## Monitoring

### Healthcheck Script

```python
import requests
import sys

def check_agent_health(port):
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

ports = [8000, 8001, 8002, 8003, 8004, 8005]
all_healthy = all(check_agent_health(p) for p in ports)

sys.exit(0 if all_healthy else 1)
```

### Prometheus Metrics (Advanced)

Add to agent runners for monitoring:

```python
from prometheus_client import Counter, Gauge

agent_requests = Counter('agent_requests_total', 'Total requests', ['agent'])
agent_response_time = Gauge('agent_response_seconds', 'Response time', ['agent'])
```

## Security Best Practices

1. **API Keys**: Store in environment variables, not in code
2. **Network**: Bind to 127.0.0.1 for local-only access
3. **Authentication**: Use strong tokens for HTTP endpoints
4. **Logs**: Rotate and secure log files
5. **Updates**: Keep Agno framework updated

## Performance Tuning

### For Large Organizations (1000+ users)

```python
{
  "num_history_runs": 5,  # Reduce context window
  "add_history_to_context": False,  # Disable for stateless queries
  "markdown": False,  # Faster response formatting
}
```

### For Complex Queries

```python
{
  "num_history_runs": 15,  # More context
  "add_datetime_to_context": True,  # Time-aware responses
  "debug_mode": True,  # Detailed logging
}
```
