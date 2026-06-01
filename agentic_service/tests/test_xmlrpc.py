import xmlrpc.client

url = 'http://localhost:8069'
username = 'admin'
password = 'admin'
db = 'burna'
# API_KEY = '105455be154b024f12281829642cb134d41d8768'

common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
# print(common.version())

user_uid = common.authenticate(db, username, password, {})
# print(user_uid)

model = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

# search function
employee_ids = model.execute_kw(db, user_uid, password, 'hr.employee', 'search', [[]])
print("search function ==>", employee_ids)

# search with pagination function
pagination_employee_ids = model.execute_kw(db, user_uid, password, 'hr.employee', 'search', [[]], {'offset':0, 'limit':1})
print("search with pagination function ==>", pagination_employee_ids)

# count function
count_employee_ids = model.execute_kw(db, user_uid, password, 'hr.employee', 'search_count', [[]])
print("count function ==>", count_employee_ids)

# read and filter function
read_filter_employee_ids = model.execute_kw(db, user_uid, password, 'hr.employee', 'read', [employee_ids], {'fields':['department_id']})
print("read and filter function ==>", read_filter_employee_ids)

# search and read function
search_read_employee_ids = model.execute_kw(db, user_uid, password, 'hr.employee', 'search_read', [[]], {'fields':['department_id','name']})
print("search and read function ==>", search_read_employee_ids)

# create function
# create_employee_ids = model.execute_kw(db, user_uid, password, 'hr.employee', 'create', [{'name': 'rpc_test'}] )
# print("create function ==>", create_employee_ids)

# write function
# write_employee_ids = model.execute_kw(db, user_uid, password, 'hr.employee', 'write', [[14], {'name': 'rpc_test_changed','department_id':5}])
# print("write function ==>", write_employee_ids)

# unlink function
# unlink_employee_ids = model.execute_kw(db, user_uid, password, 'hr.employee', 'unlink', [[14]])
# print("write function ==>", unlink_employee_ids)