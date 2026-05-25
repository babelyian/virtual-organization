#!/usr/bin/env python3
"""
Test Employee Agent Directly

This tests if the employee agent can actually retrieve data from Odoo.
"""

import requests
import json
import sys
import time


def test_employee_agent(cfg):
    """Test the employee agent directly"""

    if not cfg:
        print("❌ No config provided")
        return

    agent_name = cfg.get("agent_name")
    port = cfg.get("port", 8001)

    if not agent_name:
        print("❌ No agent_name in config")
        return

    url = f"http://localhost:{port}/agents/{agent_name}/runs"

    print("=" * 60)
    print(f"Testing Employee Agent: {agent_name}")
    print(f"Port: {port}")
    print(f"URL: {url}")
    print("=" * 60)

    # Test queries
    queries = [
        "List all departments",
        "Show all employees",
        "Who works in AI&Data?",
        "Tell me about ahmad"
    ]

    for query in queries:
        print(f"\n📝 Query: {query}")
        print("-" * 60)

        try:
            response = requests.post(
                url,
                data={
                    'message': query,
                    'session_id': f'test_{int(time.time())}',
                    'stream': 'true'  # Set to 'true' string for form data
                },
                timeout=30,
                stream=True  # Enable streaming in requests library
            )

            print(f"Status: {response.status_code}")

            if response.status_code != 200:
                print(f"❌ Error: {response.text[:200]}")
                continue

            # Parse SSE response
            content = ""
            for line in response.iter_lines():
                if not line:
                    continue

                decoded = line.decode('utf-8', errors='ignore').strip()

                if decoded.startswith('data:'):
                    data_str = decoded[5:].strip()
                    try:
                        event_data = json.loads(data_str)
                        if event_data.get('event') == 'RunContent':
                            content += event_data.get('content', '')
                        elif event_data.get('event') == 'RunCompleted':
                            final_content = event_data.get('content', '').strip()
                            if final_content:
                                content = final_content
                            break
                    except json.JSONDecodeError:
                        continue

            if content:
                print(f"✅ Response ({len(content)} chars):")
                # Print full response for short ones, truncate long ones
                if len(content) <= 500:
                    print(content)
                else:
                    print(content[:500])
                    print(f"... (truncated, total {len(content)} chars)")
            else:
                print("❌ No content in response")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

        # Small delay between queries
        time.sleep(0.5)


def check_agent_config(agent_id=13):
    """Check the agent configuration"""
    config_file = f"/tmp/agno_agent_{agent_id}.json"

    print("\n" + "=" * 60)
    print(f"Checking Agent Configuration: {config_file}")
    print("=" * 60)

    try:
        with open(config_file, 'r') as f:
            cfg = json.load(f)

        print(f"Agent Name: {cfg.get('agent_name')}")
        print(f"Agent Type: {cfg.get('agent_type')}")
        print(f"Port: {cfg.get('port')}")

        if 'odoo_config' in cfg:
            odoo_cfg = cfg['odoo_config']
            print("\n🔧 Odoo Configuration:")
            print(f"  URL: {odoo_cfg.get('url')}")
            print(f"  Database: {odoo_cfg.get('database')}")
            print(f"  Username: {odoo_cfg.get('username')}")
            print(f"  Password: {'***' if odoo_cfg.get('password') else 'NOT SET'}")
        else:
            print("⚠️  No odoo_config found")

        return cfg

    except FileNotFoundError:
        print(f"❌ Config file not found: {config_file}")
        return None
    except Exception as e:
        print(f"❌ Error reading config: {e}")
        return None


def test_odoo_connection_from_config(cfg):
    """Test Odoo connection using agent config"""
    if not cfg or 'odoo_config' not in cfg:
        print("\n❌ No odoo_config to test")
        return

    print("\n" + "=" * 60)
    print("Testing Odoo Connection from Config")
    print("=" * 60)

    odoo_cfg = cfg['odoo_config']

    try:
        import xmlrpc.client

        url = odoo_cfg['url']
        db = odoo_cfg['database']
        username = odoo_cfg['username']
        password = odoo_cfg['password']

        print(f"Connecting to {url}...")
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})

        if not uid:
            print(f"❌ Authentication failed")
            return

        print(f"✅ Authenticated as user {uid}")

        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

        # Test department query
        print("\nTesting hr.department query...")
        depts = models.execute_kw(
            db, uid, password,
            'hr.department', 'search_read',
            [[]],
            {'fields': ['name'], 'limit': 10}
        )

        print(f"✅ Found {len(depts)} departments:")
        for dept in depts:
            print(f"  - {dept.get('name')}")

        # Test employee query
        print("\nTesting hr.employee query...")
        emps = models.execute_kw(
            db, uid, password,
            'hr.employee', 'search_read',
            [[('active', '=', True)]],
            {'fields': ['name', 'department_id'], 'limit': 10}
        )

        print(f"✅ Found {len(emps)} employees:")
        for emp in emps[:5]:
            dept_name = emp.get('department_id')[1] if emp.get('department_id') else 'No department'
            print(f"  - {emp.get('name')} ({dept_name})")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    agent_id = int(sys.argv[1]) if len(sys.argv) > 1 else 2

    # Check config first
    cfg = check_agent_config(agent_id)

    # Test Odoo connection
    if cfg:
        test_odoo_connection_from_config(cfg)

    # Test agent
    if cfg:
        print("\n" + "=" * 60)
        print("Now testing the actual agent...")
        print("=" * 60)
        test_employee_agent(cfg)
    else:
        print("\n❌ Cannot test agent without valid config")
