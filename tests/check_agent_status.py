#!/usr/bin/env python3
"""
Check Agent Status and Logs
"""

import os
import glob
import json

def check_agent_logs():
    """Check all agent log files"""
    log_files = sorted(glob.glob("/tmp/agno_agent_*.log"))
    
    print("=" * 70)
    print("AGENT LOG FILES")
    print("=" * 70)
    
    if not log_files:
        print("❌ No log files found!")
        return
    
    for log_file in log_files:
        print(f"\n📄 {log_file}")
        print("-" * 70)
        
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                
            if not lines:
                print("  (empty log)")
                continue
            
            # Show last 30 lines
            print("  Last 30 lines:")
            for line in lines[-30:]:
                print(f"  {line.rstrip()}")
                
        except Exception as e:
            print(f"  ❌ Error reading: {e}")

def check_agent_configs():
    """Check all agent config files"""
    config_files = sorted(glob.glob("/tmp/agno_agent_*.json"))
    
    print("\n" + "=" * 70)
    print("AGENT CONFIGURATIONS")
    print("=" * 70)
    
    if not config_files:
        print("❌ No config files found!")
        return
    
    for config_file in config_files:
        try:
            with open(config_file, 'r') as f:
                cfg = json.load(f)
            
            agent_name = cfg.get('agent_name', 'unknown')
            agent_type = cfg.get('agent_type', 'unknown')
            
            print(f"\n📄 {config_file}")
            print(f"   Name: {agent_name}")
            print(f"   Type: {agent_type}")
            print(f"   Port: {cfg.get('port', 'N/A')}")
            
            if 'odoo_config' in cfg:
                odoo = cfg['odoo_config']
                print(f"   Odoo DB: {odoo.get('database', 'N/A')}")
                print(f"   Odoo URL: {odoo.get('url', 'N/A')}")
            
        except Exception as e:
            print(f"\n📄 {config_file}")
            print(f"   ❌ Error: {e}")

def check_agent_processes():
    """Check if agent processes are running"""
    print("\n" + "=" * 70)
    print("AGENT PROCESSES")
    print("=" * 70)
    
    import subprocess
    
    try:
        result = subprocess.run(
            ['ps', 'aux'], 
            capture_output=True, 
            text=True
        )
        
        lines = [l for l in result.stdout.split('\n') if 'enhanced_runner' in l or 'orchestrator_runner' in l]
        
        if lines:
            print("\n✅ Found agent processes:")
            for line in lines:
                print(f"  {line}")
        else:
            print("\n⚠️  No agent processes found!")
            print("  (Agents may not be running)")
            
    except Exception as e:
        print(f"❌ Error checking processes: {e}")

def check_ports():
    """Check which ports are listening"""
    print("\n" + "=" * 70)
    print("LISTENING PORTS")
    print("=" * 70)
    
    import subprocess
    
    try:
        result = subprocess.run(
            ['ss', '-tlnp'],
            capture_output=True,
            text=True
        )
        
        lines = [l for l in result.stdout.split('\n') if ':800' in l]
        
        if lines:
            print("\n✅ Agent ports:")
            for line in lines:
                print(f"  {line}")
        else:
            print("\n⚠️  No agent ports listening!")
            
    except Exception as e:
        print(f"❌ Error checking ports: {e}")

if __name__ == "__main__":
    check_agent_configs()
    check_agent_processes()
    check_ports()
    check_agent_logs()
    
    print("\n" + "=" * 70)
    print("DIAGNOSIS")
    print("=" * 70)
    print("""
Common issues:
1. If configs exist but no processes → Agents crashed, check logs for errors
2. If ports not listening → Agents not started or crashed immediately
3. If timeout errors → Agent is stuck (check logs for what it's stuck on)
4. If "No config files" → Agents were never created
    """)
