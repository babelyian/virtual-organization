# Agno Agents Odoo Module

This Odoo module provides integration with Agno AI agents, allowing users to define, configure, and manage AI agents directly from the Odoo interface.

## API Requests

curl -sS -X POST "http://127.0.0.1:8069/agno_agents/status" \
  -H "Content-Type: application/json" \
  -H "X-Agno-Token: CHANGE_ME_TO_A_LONG_RANDOM_STRING" \
  -d '{}'


curl -sS -X POST "http://127.0.0.1:8069/agno_agents/start/1" \
  -H "Content-Type: application/json" \
  -H "X-Agno-Token: CHANGE_ME_TO_A_LONG_RANDOM_STRING" \
  -d '{}'


curl -sS -X POST "http://127.0.0.1:8069/agno_agents/stop/1" \
  -H "Content-Type: application/json" \
  -H "X-Agno-Token: CHANGE_ME_TO_A_LONG_RANDOM_STRING" \
  -d '{}'



curl -sS -X POST "http://127.0.0.1:8069/agno_agents/agent/1/info" \
  -H "Content-Type: application/json" \
  -H "X-Agno-Token: CHANGE_ME_TO_A_LONG_RANDOM_STRING" \
  -d '{}'
