# Agno Agents Odoo Module

This Odoo module provides integration with Agno AI agents, allowing users to define, configure, and manage AI agents directly from the Odoo interface.

## API Requests

curl -sS -X POST "http://127.0.0.1:8069/agno_agents/status" -H "Content-Type: application/json" -H "X-Agno-Token: CHANGE_ME_TO_A_LONG_RANDOM_STRING" -d '{"jsonrpc":"2.0","id":1,"params":{}}'


curl -sS -X POST "http://127.0.0.1:8069/agno_agents/start/1" -H "Content-Type: application/json" -H "X-Agno-Token: CHANGE_ME_TO_A_LONG_RANDOM_STRING" -d '{"jsonrpc":"2.0","id":2,"params":{}>


curl -sS -X POST "http://127.0.0.1:8069/agno_agents/stop/1" -H "Content-Type: application/json" -H "X-Agno-Token: CHANGE_ME_TO_A_LONG_RANDOM_STRING" -d '{"jsonrpc":"2.0","id":3,"params":{}}'



curl -sS -X POST "http://127.0.0.1:8069/agno_agents/agent/1/info" -H "Content-Type: application/json" -H "X-Agno-Token: CHANGE_ME_TO_A_LONG_RANDOM_STRING" -d '{"jsonrpc":"2.0","id":4,"param>


curl -sS -X POST "http://127.0.0.1:8069/agno_agents/create" -H "Content-Type: application/json" -H "X-Agno-Token: CHANGE_ME_TO_A_LONG_RANDOM_STRING" -d '{"jsonrpc":"2.0","id":5,"params":{"a>



/opt/odoo19/odoo-src/odoo-bin -c /etc/odoo19/odoo.conf -d burna -u agno_user --stop-after-init

