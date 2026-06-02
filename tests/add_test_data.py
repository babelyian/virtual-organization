#!/usr/bin/env python3
"""
Add Test Data to Odoo for Agent Testing
"""

import xmlrpc.client

def add_test_data(url="http://localhost:8069", db="burna", username="admin", password="admin"):
    """Add test departments, employees, and projects to Odoo"""
    
    print("Connecting to Odoo...")
    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
    uid = common.authenticate(db, username, password, {})
    model = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
    
    if not uid:
        print("Authentication failed!")
        return
    
    print(f"Authenticated as user {uid}\n")
    
    # Create Departments
    print("Creating departments...")
    departments = {
        'Engineering': None,
        'Sales': None,
        'Marketing': None,
        'Human Resources': None,
        'Operations': None,
    }
    
    for dept_name in departments.keys():
        try:
            dept_id = models.execute_kw(
                db, uid, password,
                'hr.department', 'create',
                [{'name': dept_name}]
            )
            departments[dept_name] = dept_id
            print(f"  ✅ Created: {dept_name} (ID: {dept_id})")
        except Exception as e:
            print(f"  ⚠️  {dept_name}: {e}")
    
    # Create Employees
    print("\nCreating employees...")
    employees_data = [
        {'name': 'John Smith', 'department': 'Engineering', 'job': 'Senior Developer', 'email': 'john.smith@company.com'},
        {'name': 'Sarah Johnson', 'department': 'Engineering', 'job': 'Team Lead', 'email': 'sarah.j@company.com'},
        {'name': 'Mike Brown', 'department': 'Sales', 'job': 'Sales Manager', 'email': 'mike.b@company.com'},
        {'name': 'Emma Davis', 'department': 'Marketing', 'job': 'Marketing Specialist', 'email': 'emma.d@company.com'},
        {'name': 'Alex Wilson', 'department': 'Human Resources', 'job': 'HR Manager', 'email': 'alex.w@company.com'},
        {'name': 'Lisa Chen', 'department': 'Engineering', 'job': 'Developer', 'email': 'lisa.c@company.com'},
        {'name': 'David Lee', 'department': 'Operations', 'job': 'Operations Manager', 'email': 'david.l@company.com'},
        {'name': 'Rachel Green', 'department': 'Sales', 'job': 'Sales Representative', 'email': 'rachel.g@company.com'},
    ]
    
    for emp_data in employees_data:
        try:
            dept_id = departments.get(emp_data['department'])
            emp_id = models.execute_kw(
                db, uid, password,
                'hr.employee', 'create',
                [{
                    'name': emp_data['name'],
                    'department_id': dept_id if dept_id else False,
                    'job_title': emp_data['job'],
                    'work_email': emp_data['email'],
                }]
            )
            print(f"  ✅ Created: {emp_data['name']} - {emp_data['job']}")
        except Exception as e:
            print(f"  ⚠️  {emp_data['name']}: {e}")
    
    # Create Projects
    print("\nCreating projects...")
    projects_data = [
        {'name': 'Website Redesign', 'description': 'Complete redesign of company website'},
        {'name': 'Mobile App Development', 'description': 'New mobile app for customers'},
        {'name': 'CRM Implementation', 'description': 'Implement new CRM system'},
    ]
    
    for proj_data in projects_data:
        try:
            proj_id = models.execute_kw(
                db, uid, password,
                'project.project', 'create',
                [{
                    'name': proj_data['name'],
                    'description': proj_data['description'],
                }]
            )
            print(f"  ✅ Created: {proj_data['name']} (ID: {proj_id})")
        except Exception as e:
            print(f"  ⚠️  {proj_data['name']}: {e}")
    
    print("\n✅ Test data created successfully!")
    print("\nNow test your agents with queries like:")
    print("  - 'List all departments'")
    print("  - 'Who works in Engineering?'")
    print("  - 'What projects are active?'")

if __name__ == "__main__":
    import sys
    #
    # url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8069"
    # db = sys.argv[2] if len(sys.argv) > 2 else "burna"
    # user = sys.argv[3] if len(sys.argv) > 3 else "admin "
    # pwd = sys.argv[4] if len(sys.argv) > 4 else "admin"
    
    add_test_data()
