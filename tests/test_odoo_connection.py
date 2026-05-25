#!/usr/bin/env python3
"""
Test Odoo XML-RPC Connection for Activity Reporting Agents

This script tests if the agents can actually retrieve data from Odoo.
"""

import xmlrpc.client
import sys

def test_odoo_connection(url="http://localhost:8069", db="odoo", username="admin", password="admin"):
    """Test connection to Odoo and retrieve department data"""
    
    print("=" * 60)
    print("Testing Odoo XML-RPC Connection")
    print("=" * 60)
    print(f"URL: {url}")
    print(f"Database: {db}")
    print(f"Username: {username}")
    print("-" * 60)
    
    try:
        # Connect to common endpoint
        print("\n1. Connecting to Odoo...")
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        
        # Get version
        version = common.version()
        print(f"   ✅ Connected! Odoo version: {version['server_version']}")
        
        # Authenticate
        print("\n2. Authenticating...")
        uid = common.authenticate(db, username, password, {})
        
        if uid:
            print(f"   ✅ Authenticated! User ID: {uid}")
        else:
            print("   ❌ Authentication failed! Check username/password")
            return False
        
        # Connect to object endpoint
        print("\n3. Connecting to object endpoint...")
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        print("   ✅ Connected to object endpoint")
        
        # Test: Get departments
        print("\n4. Testing department retrieval...")
        departments = models.execute_kw(
            db, uid, password,
            'hr.department', 'search_read',
            [[]],  # Empty domain = all records
            {'fields': ['name', 'manager_id', 'parent_id'], 'limit': 50}
        )
        
        if departments:
            print(f"   ✅ Found {len(departments)} departments:")
            for dept in departments:
                print(f"      - {dept['name']} (ID: {dept['id']})")
                if dept.get('manager_id'):
                    print(f"        Manager: {dept['manager_id'][1]}")
        else:
            print("   ⚠️  No departments found in database")
            print("      This explains why agents return empty results!")
        
        # Test: Get employees
        print("\n5. Testing employee retrieval...")
        employees = models.execute_kw(
            db, uid, password,
            'hr.employee', 'search_read',
            [[('active', '=', True)]],
            {'fields': ['name', 'department_id', 'job_title', 'work_email'], 'limit': 10}
        )
        
        if employees:
            print(f"   ✅ Found {len(employees)} active employees:")
            for emp in employees[:5]:  # Show first 5
                print(f"      - {emp['name']}")
                if emp.get('department_id'):
                    print(f"        Department: {emp['department_id'][1]}")
                if emp.get('job_title'):
                    print(f"        Job: {emp['job_title']}")
                if emp.get('work_email'):
                    print(f"        Email: {emp['work_email']}")
        else:
            print("   ⚠️  No employees found in database")
            print("      This explains why agents might hallucinate data!")
        
        # Test: Get projects
        print("\n6. Testing project retrieval...")
        projects = models.execute_kw(
            db, uid, password,
            'project.project', 'search_read',
            [[('active', '=', True)]],
            {'fields': ['name', 'user_id', 'task_count'], 'limit': 10}
        )
        
        if projects:
            print(f"   ✅ Found {len(projects)} active projects:")
            for proj in projects[:5]:
                print(f"      - {proj['name']} (ID: {proj['id']})")
        else:
            print("   ⚠️  No projects found in database")
        
        print("\n" + "=" * 60)
        print("Connection Test Summary")
        print("=" * 60)
        print(f"✅ Connection: OK")
        print(f"✅ Authentication: OK")
        print(f"{'✅' if departments else '⚠️ '} Departments: {len(departments) if departments else 0} found")
        print(f"{'✅' if employees else '⚠️ '} Employees: {len(employees) if employees else 0} found")
        print(f"{'✅' if projects else '⚠️ '} Projects: {len(projects) if projects else 0} found")
        
        if not departments and not employees and not projects:
            print("\n⚠️  WARNING: Database appears empty!")
            print("   Agents will hallucinate data because there's nothing to retrieve.")
            print("   Solution: Add some test data to your Odoo database.")
        
        return True
        
    except xmlrpc.client.Fault as e:
        print(f"\n❌ XML-RPC Error: {e.faultCode} - {e.faultString}")
        return False
    except ConnectionRefusedError:
        print(f"\n❌ Connection refused. Is Odoo running on {url}?")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_config():
    """Check the agent configuration for Odoo connection details"""
    print("\n" + "=" * 60)
    print("Checking Agent Configuration")
    print("=" * 60)
    
    import json
    import glob
    
    # Find agent config files
    config_files = glob.glob("/tmp/agno_agent_*.json")
    
    if not config_files:
        print("⚠️  No agent config files found in /tmp/")
        print("   Agents may not be configured yet.")
        return
    
    print(f"Found {len(config_files)} agent config files:")
    
    for cfg_file in config_files:
        try:
            with open(cfg_file, 'r') as f:
                cfg = json.load(f)
            
            agent_type = cfg.get('agent_type', 'unknown')
            agent_name = cfg.get('agent_name', 'unknown')
            
            print(f"\n📄 {cfg_file}")
            print(f"   Type: {agent_type}")
            print(f"   Name: {agent_name}")
            
            # Check if it has Odoo config
            if 'odoo_config' in cfg:
                odoo_cfg = cfg['odoo_config']
                print(f"   Odoo URL: {odoo_cfg.get('url', 'NOT SET')}")
                print(f"   Odoo DB: {odoo_cfg.get('database', 'NOT SET')}")
                print(f"   Odoo User: {odoo_cfg.get('username', 'NOT SET')}")
                print(f"   Odoo Pass: {'***' if odoo_cfg.get('password') else 'NOT SET'}")
            else:
                print(f"   ⚠️  No odoo_config found (orchestrator doesn't need it)")
                
        except Exception as e:
            print(f"   ❌ Error reading config: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Odoo connection for agents")
    parser.add_argument("--url", default="http://localhost:8069", help="Odoo URL")
    parser.add_argument("--db", default="odoo", help="Database name")
    parser.add_argument("--user", default="admin", help="Username")
    parser.add_argument("--password", default="admin", help="Password")
    
    args = parser.parse_args()
    
    # Test connection
    success = test_odoo_connection(args.url, args.db, args.user, args.password)
    
    # Test agent configs
    test_agent_config()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All tests passed! Agents should be able to retrieve data.")
    else:
        print("❌ Connection failed. Fix the issues above.")
    print("=" * 60)
