import os
from dotenv import load_dotenv
import aiohttp
import asyncio
from utils.time_intervals import TIME_INTERVALS
from datetime import datetime
from typing import Any


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


async def get_list_of_events(department_ids:list[Any] = None, time_range: str = None):
    """
        Fetch calendar events and meetings from Odoo with optional filtering for a specific department or list of departments

    Args:
        department_ids: Optional list of department IDs to filter by
        time_range: Optional time filter - one of ['last_week', 'last_month',
                   'next_week', 'next_month', 'today', 'yesterday']

    Returns:
        Dictionary with 'events' key containing list of enriched events, or None if error
        Each event includes: id, display_name, start, stop, partner_ids,
                            employee_ids, department_ids, duration_in_hours
    Note:
        to use this tool with input department_id first get department ID from tool "department_id_by_name"
    """
    try:
        user_uid = await authenticate_async(
            url, db, username, password
        )
        events_domain = []

        # Add date range conditions if provided
        if time_range:
            start , end = TIME_INTERVALS[time_range]
            events_domain.append(('start', '>=', start))
            events_domain.append(('start', '<=', end))

        search_read_events = await execute_kw_async(
            url, db, user_uid, password,
            'calendar.event',
            'search_read',
            [events_domain],
            {'fields': ['id', 'display_name', 'start', 'stop', 'partner_ids']}
        )
        users_domain = []
        user_partner_ids = []
        for event in search_read_events:
            for partner_id in event.get('partner_ids'):
                user_partner_ids.append(partner_id) if partner_id not in user_partner_ids else None

        users_domain.append(('user_partner_id', 'in', user_partner_ids))

        search_read_users = await execute_kw_async(
            url, db, user_uid, password,
            'hr.employee',
            'search_read',
            [users_domain],
            {'fields': ['user_partner_id', 'employee_id', 'department_id']}
        )
        # Build lookup dictionaries from user data
        partner_to_employee = {}
        partner_to_department = {}

        for user in search_read_users:
            # user_partner_id = [partner_id, user_name]
            partner_id = user['user_partner_id'][0]

            # employee_id = [emp_id, emp_name]
            if user.get('employee_id'):
                partner_to_employee[partner_id] = user['employee_id'][0]

            # department_id = [dept_id, dept_name]
            if user.get('department_id'):
                partner_to_department[partner_id] = user['department_id'][0]

        # Now enrich events efficiently
        for event in search_read_events:
            # Transform partner_ids using the lookup maps
            event['employee_ids'] = [
                partner_to_employee[pid]
                for pid in event['partner_ids']
                if pid in partner_to_employee
            ]

            event['department_ids'] = [
                partner_to_department[pid]
                for pid in event['partner_ids']
                if pid in partner_to_department
            ]

        # Add duration to each meeting
        for event in search_read_events:
            start = datetime.strptime(event['start'], '%Y-%m-%d %H:%M:%S')
            stop = datetime.strptime(event['stop'], '%Y-%m-%d %H:%M:%S')
            duration = stop - start
            event['duration_in_hours'] = duration.total_seconds()/3600

        result = {"events": search_read_events}
        if not department_ids:
            return result
        else:
            result = {"events": [
                event for event in result['events']
                if any(dept_id in department_ids for dept_id in event['department_ids'])
            ]}
            return result

    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    print(asyncio.run(get_list_of_events(department_ids=[3],time_range='last_week')))