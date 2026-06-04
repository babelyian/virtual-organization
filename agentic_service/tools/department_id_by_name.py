import os
from typing import Any, Optional, List, Dict, Coroutine
import requests
from dotenv import load_dotenv
import aiohttp
import asyncio
from datetime import datetime
import re

load_dotenv()

url = os.getenv("ODOO_URL")
db = os.getenv("ODOO_DB")
username = os.getenv("ODOO_USERNAME")
password = os.getenv("ODOO_PASSWORD")

async def call_odoo_rpc(url, db, service, method, args):
    """Generic Odoo RPC caller"""
    json_endpoint = f"{url}/jsonrpc"

    # For 'common' service, db is NOT needed in args
    # For 'object' service, db MUST be first argument
    # Let's handle this dynamically
    full_args = args

    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": service,
            "method": method,
            "args": full_args
        },
        "id": 1
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(json_endpoint, json=payload) as response:
            result = await response.json()
            if 'error' in result:
                raise Exception(f"Odoo error: {result['error']}")
            return result.get('result')

async def authenticate_async(url, db, username, password):
    """Authenticate and get user ID"""
    # For 'common.login', args = [db, username, password]
    result = await call_odoo_rpc(
        url=url,
        db=db,  # Passed but not used by common service
        service='common',
        method='login',
        args=[db, username, password]  # db IS needed here
    )
    return result

async def execute_kw_async(url, db, uid, password, model, method, args, kwargs=None):
    """Execute Odoo model method"""
    # For 'object.execute_kw', args = [db, uid, password, model, method, args, kwargs]
    full_args = [db, uid, password, model, method, args, kwargs or {}]

    result = await call_odoo_rpc(
        url=url,
        db=db,
        service='object',
        method='execute_kw',
        args=full_args
    )
    return result


async def get_department_id_by_name():
    """
    **CRITICAL: Call this tool FIRST before any department-specific operations**

    Retrieve department IDs by name or list all departments.


    Returns:
        Dictionary with department information:
        {
            "departments": [
                {"department_id": 1, "department_name": "Administration"},
                {"department_id": 3, "department_name": "AI Team"}
            ]
        }

    **WORKFLOW INSTRUCTION:**
    When a user asks about a specific department (e.g., "Show me AI team tasks"):
    1. Call this tool FIRST to get the department_id
    2. Extract the department_id from the result
    3. Pass that department_id to department_tasks()

    Example workflow:
        # Step 1: Get department ID
        depts = await get_department_id_by_name()
        dept_id = depts["departments"][0]["department_id"]

        # Step 2: Use with department_tasks
        tasks = await department_tasks(department_id=[dept_id], time_range="next_week")
    """
    user_uid = await authenticate_async(
        url, db, username, password
    )
    search_read_departments = await execute_kw_async(
        url, db, user_uid, password,
        'hr.department',
        'search_read',
        [[]],
        {'fields': ['id', 'display_name']}
    )

    result = {"departments": []}
    for item in search_read_departments:
        result["departments"].append({"department_id": item.get("id"), "department_name": item.get("display_name")})

    return result


if __name__ == "__main__":
    asyncio.run(get_department_id())