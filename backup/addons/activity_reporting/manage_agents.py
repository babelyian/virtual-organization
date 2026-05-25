#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Activity Reporting Agent Management Utility

This script provides command-line utilities for managing activity reporting agents.
Usage examples:
    python3 manage_agents.py --list
    python3 manage_agents.py --start-all
    python3 manage_agents.py --stop-all
    python3 manage_agents.py --status
"""

import argparse
import json
import sys
import requests
from typing import List, Dict, Any


class AgentManager:
    """Manages activity reporting agents via HTTP API"""
    
    def __init__(self, base_url: str = "http://localhost:8069", token: str = None):
        self.base_url = base_url.rstrip('/')
        self.token = token or "CHANGE_ME_TO_A_LONG_RANDOM_STRING"
        self.headers = {
            "Content-Type": "application/json",
            "X-Agno-Token": self.token,
        }
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents"""
        url = f"{self.base_url}/agno_agents/status"
        try:
            response = requests.post(url, headers=self.headers, json={})
            response.raise_for_status()
            data = response.json()
            if data.get("success"):
                return data.get("agents", [])
            else:
                print(f"Error: {data.get('error')}")
                return []
        except Exception as e:
            print(f"Failed to list agents: {e}")
            return []
    
    def start_agent(self, agent_id: int) -> bool:
        """Start a specific agent"""
        url = f"{self.base_url}/agno_agents/start/{agent_id}"
        try:
            response = requests.post(url, headers=self.headers, json={})
            response.raise_for_status()
            data = response.json()
            if data.get("success"):
                print(f"✓ Started agent {agent_id}: {data.get('message')}")
                return True
            else:
                print(f"✗ Failed to start agent {agent_id}: {data.get('error')}")
                return False
        except Exception as e:
            print(f"✗ Error starting agent {agent_id}: {e}")
            return False
    
    def stop_agent(self, agent_id: int) -> bool:
        """Stop a specific agent"""
        url = f"{self.base_url}/agno_agents/stop/{agent_id}"
        try:
            response = requests.post(url, headers=self.headers, json={})
            response.raise_for_status()
            data = response.json()
            if data.get("success"):
                print(f"✓ Stopped agent {agent_id}: {data.get('message')}")
                return True
            else:
                print(f"✗ Failed to stop agent {agent_id}: {data.get('error')}")
                return False
        except Exception as e:
            print(f"✗ Error stopping agent {agent_id}: {e}")
            return False
    
    def get_agent_info(self, agent_id: int) -> Dict[str, Any]:
        """Get detailed info about an agent"""
        url = f"{self.base_url}/agno_agents/agent/{agent_id}/info"
        try:
            response = requests.post(url, headers=self.headers, json={})
            response.raise_for_status()
            data = response.json()
            if data.get("success"):
                return data.get("agent", {})
            else:
                print(f"Error: {data.get('error')}")
                return {}
        except Exception as e:
            print(f"Failed to get agent info: {e}")
            return {}
    
    def print_status(self):
        """Print status of all agents"""
        agents = self.list_agents()
        if not agents:
            print("No agents found or unable to retrieve agent list")
            return
        
        print("\n" + "=" * 80)
        print("ACTIVITY REPORTING AGENTS STATUS")
        print("=" * 80)
        
        # Categorize agents
        orchestrator = []
        subagents = []
        
        for agent in agents:
            name = agent.get("name", "")
            if "orchestrator" in name.lower():
                orchestrator.append(agent)
            else:
                subagents.append(agent)
        
        # Print orchestrator
        if orchestrator:
            print("\n🎯 ORCHESTRATOR AGENT:")
            print("-" * 80)
            for agent in orchestrator:
                self._print_agent_details(agent)
        
        # Print subagents
        if subagents:
            print("\n🤖 SPECIALIZED AGENTS:")
            print("-" * 80)
            for agent in subagents:
                self._print_agent_details(agent)
        
        print("\n" + "=" * 80)
    
    def _print_agent_details(self, agent: Dict[str, Any]):
        """Print formatted agent details"""
        name = agent.get("name", "Unknown")
        status = agent.get("status", "unknown")
        is_active = agent.get("is_active", False)
        port = agent.get("port", "N/A")
        model = agent.get("model_id", "N/A")
        error = agent.get("error_message")
        
        # Status emoji
        status_emoji = "✓" if is_active else "✗"
        status_color = "\033[92m" if is_active else "\033[91m"
        reset_color = "\033[0m"
        
        print(f"\n{status_emoji} {status_color}{name}{reset_color}")
        print(f"   Status: {status.upper()}")
        print(f"   Port: {port}")
        print(f"   Model: {model}")
        if error:
            print(f"   ⚠️  Error: {error}")
    
    def start_all(self):
        """Start all stopped agents"""
        print("\n🚀 Starting all agents...")
        agents = self.list_agents()
        
        # Start subagents first
        subagents = [a for a in agents if "orchestrator" not in a.get("name", "").lower()]
        for agent in subagents:
            if not agent.get("is_active"):
                self.start_agent(agent["id"])
        
        # Start orchestrator last
        orchestrators = [a for a in agents if "orchestrator" in a.get("name", "").lower()]
        for agent in orchestrators:
            if not agent.get("is_active"):
                self.start_agent(agent["id"])
        
        print("\n✓ Start sequence completed")
    
    def stop_all(self):
        """Stop all running agents"""
        print("\n🛑 Stopping all agents...")
        agents = self.list_agents()
        
        # Stop orchestrator first
        orchestrators = [a for a in agents if "orchestrator" in a.get("name", "").lower()]
        for agent in orchestrators:
            if agent.get("is_active"):
                self.stop_agent(agent["id"])
        
        # Stop subagents
        subagents = [a for a in agents if "orchestrator" not in a.get("name", "").lower()]
        for agent in subagents:
            if agent.get("is_active"):
                self.stop_agent(agent["id"])
        
        print("\n✓ Stop sequence completed")


def main():
    parser = argparse.ArgumentParser(
        description="Activity Reporting Agent Management Utility"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8069",
        help="Odoo base URL (default: http://localhost:8069)"
    )
    parser.add_argument(
        "--token",
        help="API token (default: from agno_controller.py)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all agents"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show detailed status of all agents"
    )
    parser.add_argument(
        "--start-all",
        action="store_true",
        help="Start all stopped agents"
    )
    parser.add_argument(
        "--stop-all",
        action="store_true",
        help="Stop all running agents"
    )
    parser.add_argument(
        "--start",
        type=int,
        metavar="AGENT_ID",
        help="Start specific agent by ID"
    )
    parser.add_argument(
        "--stop",
        type=int,
        metavar="AGENT_ID",
        help="Stop specific agent by ID"
    )
    parser.add_argument(
        "--info",
        type=int,
        metavar="AGENT_ID",
        help="Get detailed info about specific agent"
    )
    
    args = parser.parse_args()
    
    # Create manager
    manager = AgentManager(base_url=args.url, token=args.token)
    
    # Execute commands
    if args.list:
        agents = manager.list_agents()
        print("\nAgents:")
        for agent in agents:
            print(f"  ID: {agent['id']}, Name: {agent['name']}, Status: {agent['status']}")
    
    elif args.status:
        manager.print_status()
    
    elif args.start_all:
        manager.start_all()
    
    elif args.stop_all:
        manager.stop_all()
    
    elif args.start:
        manager.start_agent(args.start)
    
    elif args.stop:
        manager.stop_agent(args.stop)
    
    elif args.info:
        info = manager.get_agent_info(args.info)
        if info:
            print(json.dumps(info, indent=2))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
