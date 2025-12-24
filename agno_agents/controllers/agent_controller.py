from odoo import http
from odoo.http import request
import json


class AgnoAgentController(http.Controller):

    @http.route('/agno_agents/status', type='json', auth='user', methods=['GET'])
    def get_agents_status(self):
        """Get status of all agents via JSON endpoint"""
        agents = request.env['agno.agent'].search([])
        
        result = []
        for agent in agents:
            result.append({
                'id': agent.id,
                'name': agent.agent_name,
                'status': agent.status,
                'is_active': agent.is_active,
                'port': agent.port,
                'model_id': agent.model_id,
                'last_started': agent.last_started.isoformat() if agent.last_started else None,
                'error_message': agent.error_message or None,
            })
        
        return {'agents': result}

    @http.route('/agno_agents/start/<int:agent_id>', type='json', auth='user', methods=['POST'])
    def start_agent(self, agent_id):
        """Start an agent via JSON endpoint"""
        try:
            agent = request.env['agno.agent'].browse(agent_id)
            if not agent.exists():
                return {'success': False, 'error': 'Agent not found'}
            
            agent.action_start_agent()
            return {'success': True, 'message': f'Agent {agent.agent_name} started successfully'}
        
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/agno_agents/stop/<int:agent_id>', type='json', auth='user', methods=['POST'])
    def stop_agent(self, agent_id):
        try:
            agent = request.env['agno.agent'].browse(agent_id)
            if not agent.exists():
                return {'success': False, 'error': 'Agent not found'}
            
            agent.action_stop_agent()
            return {'success': True, 'message': f'Agent {agent.agent_name} stopped successfully'}
        
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/agno_agents/agent/<int:agent_id>/info', type='json', auth='user')
    def get_agent_info(self, agent_id):
        try:
            agent = request.env['agno.agent'].browse(agent_id)
            if not agent.exists():
                return {'success': False, 'error': 'Agent not found'}
            
            return {
                'success': True,
                'agent': {
                    'id': agent.id,
                    'name': agent.agent_name,
                    'role': agent.agent_role,
                    'instructions': agent.instructions,
                    'model_id': agent.model_id,
                    'base_url': agent.base_url,
                    'status': agent.status,
                    'is_active': agent.is_active,
                    'port': agent.port,
                    'host': agent.host,
                    'last_started': agent.last_started.isoformat() if agent.last_started else None,
                    'last_stopped': agent.last_stopped.isoformat() if agent.last_stopped else None,
                    'error_message': agent.error_message,
                }
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/agno_agents/dashboard', type='http', auth='user', website=True)
    def dashboard(self):
        """Simple dashboard to view agents status"""
        agents = request.env['agno.agent'].search([])
        
        return request.render('agno_agents.dashboard_template', {
            'agents': agents
        })