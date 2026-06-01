import json
import requests

url = "http://localhost:8069"  # Replace with your Odoo server URL
db = "your_database"  # Replace with your database name
username = "your_username"  # Replace with your username
password = "your_password"  # Replace with your password

# JSON-RPC endpoint
json_endpoint = f"{url}/jsonrpc"


def json_rpc_call(service, method, params):
    """Helper function to make JSON-RPC calls"""
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": service,
            "method": method,
            "args": params
        },
        "id": 1
    }

    response = requests.post(json_endpoint, json=payload, headers=headers)
    response.raise_for_status()
    result = response.json()

    if 'error' in result:
        raise Exception(f"JSON-RPC error: {result['error']}")

    return result.get('result')


# Authenticate
def authenticate(db, username, password):
    params = [db, username, password]
    user_uid = json_rpc_call("common", "login", params)
    return user_uid


# Execute model method
def execute_kw(db, user_uid, password, model, method, args, kwargs=None):
    if kwargs is None:
        kwargs = {}
    params = [db, user_uid, password, model, method, args, kwargs]
    result = json_rpc_call("object", "execute_kw", params)
    return result


# Main execution
try:
    # Authenticate
    user_uid = authenticate(db, username, password)
    print(f"Authenticated with UID: {user_uid}")

    print("*" * 65)
    print("JSON RPC")
    print("*" * 65)

    # search function
    employee_ids = execute_kw(db, user_uid, password, 'hr.employee', 'search', [[]])
    print("search function ==>", employee_ids)

    # search with pagination function
    pagination_employee_ids = execute_kw(db, user_uid, password, 'hr.employee', 'search', [[]],
                                         {'offset': 0, 'limit': 1})
    print("search with pagination function ==>", pagination_employee_ids)

    # count function
    count_employee_ids = execute_kw(db, user_uid, password, 'hr.employee', 'search_count', [[]])
    print("count function ==>", count_employee_ids)

    # read and filter function
    read_filter_employee_ids = execute_kw(db, user_uid, password, 'hr.employee', 'read',
                                          [employee_ids], {'fields': ['department_id']})
    print("read and filter function ==>", read_filter_employee_ids)

    # search and read function
    search_read_employee_ids = execute_kw(db, user_uid, password, 'hr.employee', 'search_read',
                                          [[]], {'fields': ['department_id', 'name']})
    print("search and read function ==>", search_read_employee_ids)

    # create function (commented out)
    # create_employee_ids = execute_kw(db, user_uid, password, 'hr.employee', 'create',
    #                                 [{'name': 'rpc_test'}])
    # print("create function ==>", create_employee_ids)

    # write function (commented out)
    # write_employee_ids = execute_kw(db, user_uid, password, 'hr.employee', 'write',
    #                                [[14], {'name': 'rpc_test_changed', 'department_id': 5}])
    # print("write function ==>", write_employee_ids)

    # unlink function (commented out)
    # unlink_employee_ids = execute_kw(db, user_uid, password, 'hr.employee', 'unlink', [[14]])
    # print("unlink function ==>", unlink_employee_ids)

except Exception as e:
    print(f"Error: {e}")