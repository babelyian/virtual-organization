import os
import requests
from dotenv import load_dotenv
import aiohttp
import asyncio
from datetime import datetime
# from concurrent.futures import ThreadPoolExecutor
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


async def get_list_of_projects(project_ids=None):
    """
    Fetch projects and their metadata from Odoo's project.project model.

    Args:
        project_ids (List[int], optional): Specific project IDs to retrieve.
                                          If None, returns all projects.

    Returns:
        dict: Project data with structure:
            {
                'projects': [
                    {
                        'project_id': int,
                        'project_name': str,
                        'project_stage': str,
                        'project_task_ids': List[int]  # Associated task IDs
                    }
                ]
            }
    """
    try:
        user_uid = await authenticate_async(
            url, db, username, password
        )
        if project_ids:
            domain = [['id', 'in', project_ids]]
        else:
            domain = []  # Empty domain returns all records
        search_read_projects = await execute_kw_async(
            url, db, user_uid, password,
            'project.project',
            'search_read',
            [domain]
        )
        tool_result = {}
        projects = []
        for project in search_read_projects:
            project_details = {}
            project_details['project_id'] = project.get("id")
            project_details['project_name'] = project.get("name")
            project_details['project_stage'] = project.get("stage_id")[-1]
            project_details['project_task_ids'] = project.get("task_ids")
            projects.append(project_details)
        tool_result['projects'] = projects
        return tool_result
    except Exception as e:
        print(f"Error: {e}")
        return None

async def get_list_of_project_tasks(tasks_list=None):
    """ connects to odoo project.task model to get details about tasks
        Args:
            tasks_list (List[int], optional): Specific Task IDs to retrieve.
                                          If None, returns all tasks.
        Returns:
            dict: Dictionary with 'tasks' key containing list of task details
        """
    try:
        user_uid = await authenticate_async(
            url, db, username, password
        )
        if tasks_list:
            domain = [['id', 'in', tasks_list]]
        else:
            domain = []  # Empty domain returns all records
        search_read_tasks = await execute_kw_async(
            url, db, user_uid, password,
            'project.task',
            'search_read',
            [domain]
        )
        tool_result  = {}
        tasks = []
        # print(search_read_tasks[0])
        for task in search_read_tasks:
            task_details = {}
            task_details['task_id'] = task.get("id")
            task_details['task_name'] = task.get("name")
            task_details['task_description'] = re.search(r'>(.*?)<', task.get("description")).group(1) if task.get("description") else False
            task_details['task_description'] = re.sub(r'&nbsp;', ' ', task_details['task_description']) if task_details['task_description'] else False
            # task_details['task_description'] = re.sub(r'\s+', ') ', task_details['task_description'])
            task_details['task_project_id'] = task.get("project_id")
            task_details['task_user_ids'] = task.get("user_ids")
            task_details['task_portal_user_names'] = task.get("portal_user_names")
            task_details['task_child_ids'] = task.get("child_ids")
            task_details['task_subtask_count'] = task.get("subtask_count")
            task_details['task_closed_subtask_count'] = task.get("closed_subtask_count")
            task_details['task_state'] = task.get("state")
            task_details['task_date_assign'] = task.get("date_assign")
            task_details['task_date_deadline'] = task.get("date_deadline")
            deadline_datetime = datetime.strptime(task_details['task_date_deadline'] , "%Y-%m-%d %H:%M:%S") if task_details['task_date_deadline'] else False
            task_details['task_deadline_passed'] = deadline_datetime < datetime.now() if deadline_datetime else False
            task_details['task_message_needaction'] = task.get("message_needaction")
            task_details['task_message_needaction_counter'] = task.get("message_needaction_counter")
            task_details['task_activity_ids'] = task.get("activity_ids")
            task_details['task_activity_state'] = task.get("activity_state")
            task_details['task_activity_user_id'] = task.get("activity_user_id")
            task_details['task_activity_type_id'] = task.get("activity_type_id")
            task_details['task_activity_date_deadline'] = task.get("activity_date_deadline")
            task_details['task_activity_summary'] = task.get("activity_summary")
            task_details['task_user_ids'] = task.get("user_ids")
            task_details['task_portal_user_names'] = task.get("portal_user_names")
            tasks.append(task_details)
        tool_result['tasks'] = tasks
        return tool_result
    except Exception as e:
        print(f"Error: {e}")

# Tools
async def get_projects_summary():
    """Returns lightweight project overview - suitable for initial context"""
    projects_data = await get_list_of_projects()
    result = {'projects': []}

    for proj in projects_data['projects']:
        # Get tasks once
        tasks = (await get_list_of_project_tasks(proj['project_task_ids'])).get('tasks', [])

        # Count task states and collect valid deadlines in one pass
        completed = in_progress = 0
        valid_deadlines = []

        for task in tasks:
            state = task.get('task_state', '')
            if state == '01_in_progress':
                in_progress += 1
            elif state == '1_done':
                completed += 1

            # Parse deadline if valid
            deadline = task.get('task_date_deadline', False)
            if deadline and isinstance(deadline, str):
                try:
                    valid_deadlines.append(datetime.strptime(deadline, '%Y-%m-%d %H:%M:%S'))
                except (ValueError, TypeError):
                    pass
            elif isinstance(deadline, datetime):
                valid_deadlines.append(deadline)

        # Build project entry
        result['projects'].append({
            'id': proj['project_id'],
            'name': proj['project_name'],
            'stage': proj['project_stage'],
            'stats': {
                'total_tasks': len(proj['project_task_ids']),
                'completed': completed,
                'in_progress': in_progress
            },
            'key_dates': {
                'earliest_deadline': min(valid_deadlines) if valid_deadlines else None,
                'latest_deadline': max(valid_deadlines) if valid_deadlines else None
            }
        })

    return result

async def get_project_tasks_headers(project_id):
    """
    Fetch lightweight task headers for a specific project.

    This function retrieves only essential task information including task names,
    basic status, deadlines, and activity states. It excludes detailed task content
    like descriptions, subtasks, attachments, and other heavy fields.

    Args:
        project_id (int): The ID of the project to fetch tasks from.

    Returns:
        dict: A dictionary containing a list of task headers with the following structure:
            {
                'tasks': [
                    {
                        'id': int,                              # Task ID
                        'name': str,                            # Task name/title
                        'state': str,                           # Task status ('in_progress' or 'done')
                        'deadline': str|False,                  # Task deadline or False if not set
                        'assigned_to_ids': list|False,          # Task assignee/s IDs
                        'assigned_to_usernames': str|False,     # Task assignee/s usernames
                        'has_activity': bool,                   # Whether task has pending activities
                        'activity_state': str|None              # Activity state if has_activity is True
                    }
                ]
            }

    Note:
        Task states are mapped as follows:
        - '01_in_progress' -> 'in_progress'
        - '1_done' -> 'done'
    """
    # Same as your tool 1 but with task names and basic status
    projects_data = (await get_list_of_projects(project_id)).get('projects',[])[0]
    tasks = (await get_list_of_project_tasks(projects_data['project_task_ids'])).get('tasks', [])
    states = {
        '01_in_progress':'in_progress',
        '1_done':'done',
    }
    result = {'tasks': []}
    for task in tasks:
        result['tasks'].append(
            {
                'id': task['task_id'],
                'name': task['task_name'],
                'state': states[task['task_state']],
                'deadline': task['task_date_deadline'],
                'has_deadline_passed': task['task_deadline_passed'],
                'assigned_to_ids': task['task_user_ids'],
                'assigned_to_usernames': task['task_portal_user_names'],
                'has_activity': True if task['task_activity_state'] else False,
                'activity_state': task['task_activity_state'] if task['task_activity_state'] else None
            }
        )
    return result

async def get_task_details(task_id):
    """
    Retrieve complete, detailed information for a single task.

    This function fetches all available task data including description, assignments,
    and activity state. Unlike lightweight task headers, this returns the full task
    object which is significantly larger and should be used sparingly (only when
    detailed task information is required).

    Args:
        task_id (int): The ID of the task to retrieve.

    Returns:
        dict: A dictionary containing complete task details with the following structure:
            {
                'task': {
                    'id': int,                      # Task unique identifier
                    'name': str,                    # Task name/title
                    'description': str,             # Full task description (may contain HTML)
                    'state': str,                   # Task status ('in_progress' or 'done')
                    'deadline': str|False,          # Task deadline or False if not set
                    'assigned_to_ids': list[int],   # List of assigned user IDs
                    'assigned_to_usernames': list[str],  # List of assigned usernames
                    'has_activity': bool,           # Whether task has pending activities
                    'activity_state': str|None      # Activity state if has_activity is True
                }
            }

    Note:
        This function has a high data cost and should only be called when
        complete task details are necessary. For listing or summary views,
        prefer get_project_tasks_headers() which is 80% smaller.
    """
    task = (await get_list_of_project_tasks(task_id)).get('tasks', [])[0]
    states = {
        '01_in_progress': 'in_progress',
        '1_done': 'done',
    }
    result = {
        'task':
            {
                'id': task['task_id'],
                'name': task['task_name'],
                'description': task['task_description'],
                'state': states[task['task_state']],
                'deadline': task['task_date_deadline'],
                'has_deadline_passed': task['task_deadline_passed'],
                'assigned_to_ids': task['task_user_ids'],
                'assigned_to_usernames': task['task_portal_user_names'],
                'has_activity': True if task['task_activity_state'] else False,
                'activity_state': task['task_activity_state'] if task['task_activity_state'] else None
            }
    }

    return result





if __name__ == '__main__':
    # projects = asyncio.run(get_list_of_projects())
    # print(f"get_list_of_projects\n {projects} \n")
    # print("*"*30, "\n", projects['projects'][1]['project_task_ids'])
    # task_details = asyncio.run(get_list_of_project_tasks())
    # print((task_details))
    # print(f"<= tool get_list_of_tasks => \n {task_details} \n")
    # all_tasks =  asyncio.run(get_list_of_project_tasks(1))
    # print((all_tasks['tasks']))s

    print("* "*30 + "get_projects_summary\n",asyncio.run(get_projects_summary()),"*"*30 + "\n")
    print("* "*30 + "get_project_tasks_headers\n", asyncio.run(get_project_tasks_headers(1)), "*"*30 + "\n")
    print("* "*30 + "get_task_details\n", asyncio.run(get_task_details(15)), "*"*30 + "\n")