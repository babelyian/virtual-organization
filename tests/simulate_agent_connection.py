#!/usr/bin/env python3
"""
Simulate What Employee Agent Does

This replicates the exact steps the employee agent takes to connect to Odoo.
"""

import xmlrpc.client
import json
import sys

def test_agent_odoo_connection(config_file="/tmp/agno_agent_8.json"):
    """Test the exact connection the agent would make"""
    
    print("=" * 70)
    print("SIMULATING EMPLOYEE AGENT ODOO CONNECTION")
    print("=" * 70)
    
    # Step 1: Read config
    print(f"\n1. Reading config: {config_file}")
    try:
        with open(config_file, 'r') as f:
            cfg = json.load(f)
        print(f"   ✅ Config loaded")
        print(f"   Agent: {cfg.get('agent_name')}")
        print(f"   Type: {cfg.get('agent_type')}")
    except FileNotFoundError:
        print(f"   ❌ Config file not found")
        print(f"   Available configs:")
        import glob
        for f in glob.glob("/tmp/agno_agent_*.json"):
            print(f"     - {f}")
        return
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Step 2: Get Odoo config
    print("\n2. Getting Odoo configuration...")
    odoo_config = cfg.get('odoo_config')
    if not odoo_config:
        print("   ❌ No odoo_config found!")
        print("   This agent won't be able to connect to Odoo")
        return
    
    url = odoo_config.get('url')
    database = odoo_config.get('database')
    username = odoo_config.get('username')
    password = odoo_config.get('password')
    
    print(f"   URL: {url}")
    print(f"   Database: {database}")
    print(f"   Username: {username}")
    print(f"   Password: {'***' if password else 'NOT SET'}")
    
    # Step 3: Connect to common endpoint
    print("\n3. Connecting to XML-RPC common endpoint...")
    try:
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        version = common.version()
        print(f"   ✅ Connected!")
        print(f"   Odoo version: {version.get('server_version')}")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        print(f"   Is Odoo running on {url}?")
        return
    
    # Step 4: Authenticate
    print("\n4. Authenticating...")
    try:
        uid = common.authenticate(database, username, password, {})
        if uid:
            print(f"   ✅ Authenticated! User ID: {uid}")
        else:
            print(f"   ❌ Authentication failed!")
            print(f"   Check username/password")
            return
    except Exception as e:
        print(f"   ❌ Authentication error: {e}")
        return
    
    # Step 5: Connect to models endpoint
    print("\n5. Connecting to models endpoint...")
    try:
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        print(f"   ✅ Connected to models endpoint")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return
    
    # Step 6: Test department query (what search_employees would do)
    print("\n6. Testing department query (search_read)...")
    try:
        print("   Querying hr.department...")
        depts = models.execute_kw(
            database, uid, password,
            'hr.department', 'search_read',
            [[]],  # Empty domain = all records
            {'fields': ['name', 'manager_id', 'parent_id'], 'limit': 50}
        )
        
        print(f"   ✅ Query successful!")
        print(f"   Found {len(depts)} departments:")
        
        if depts:
            for dept in depts[:10]:  # Show first 10
                print(f"      - {dept['name']} (ID: {dept['id']})")
                if dept.get('manager_id'):
                    print(f"        Manager: {dept['manager_id'][1]}")
        else:
            print("      (No departments in database)")
            print("      ⚠️  This is why agent returns empty results!")
            
    except Exception as e:
        print(f"   ❌ Query failed: {e}")
        print("   Check if HR module is installed")
        return
    
    # Step 7: Test employee query
    print("\n7. Testing employee query...")
    try:
        print("   Querying hr.employee...")
        emps = models.execute_kw(
            database, uid, password,
            'hr.employee', 'search_read',
            [[('active', '=', True)]],
            {'fields': ['name', 'department_id', 'job_title', 'work_email'], 'limit': 50}
        )
        
        print(f"   ✅ Query successful!")
        print(f"   Found {len(emps)} active employees:")
        
        if emps:
            for emp in emps[:10]:
                print(f"      - {emp['name']}")
                if emp.get('department_id'):
                    print(f"        Department: {emp['department_id'][1]}")
                if emp.get('job_title'):
                    print(f"        Job: {emp['job_title']}")
        else:
            print("      (No employees in database)")
            print("      ⚠️  This is why agent returns empty results!")
            
    except Exception as e:
        print(f"   ❌ Query failed: {e}")
        return
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    if depts or emps:
        print(f"✅ Connection works! Found data:")
        print(f"   - {len(depts)} departments")
        print(f"   - {len(emps)} employees")
        print("\nIf agent still returns empty, check:")
        print("1. Agent logs for errors")
        print("2. LLM is working (API key valid)")
        print("3. Agent is actually using these tools")
    else:
        print("⚠️  Connection works but database is EMPTY!")
        print("   This is why agents return nothing or hallucinate.")
        print("\nSolution: Add test data")
        print(f"   python3 /tmp/add_test_data.py http://localhost:8069 {database} admin admin")

if __name__ == "__main__":
    # Try to find an employee agent config
    import glob
    
    configs = glob.glob("/tmp/agno_agent_*.json")
    employee_configs = []
    
    for cfg_path in configs:
        try:
            with open(cfg_path, 'r') as f:
                cfg = json.load(f)
            if cfg.get('agent_type') == 'employee':
                employee_configs.append(cfg_path)
        except:
            pass
    
    if employee_configs:
        print(f"Found {len(employee_configs)} employee agent config(s)")
        print(f"Testing with: {employee_configs[0]}\n")
        test_agent_odoo_connection(employee_configs[0])
    else:
        print("No employee agent config found")
        print("Available configs:")
        for cfg in configs:
            print(f"  - {cfg}")
