from decouple import config
from typing import List, Dict, Optional
import requests

OPENGIT = "https://opengit.ir/api/v4"
TOKEN = config("OPENGIT_ACCESS_TOKEN")

HEADERS = {

    "Authorization": f"Bearer {TOKEN}",

    "Content-Type": "application/json"

}
GROUP_ID = 1202
PROJECT_ID =  3062

# groups
def groups(opengit_url, headers):
    url = f"{opengit_url}/groups"
    group_response = requests.get(url,headers=headers)
    group_data = group_response.json()
    return group_data

# groups/:id info
def group_info(opengit_url, group_id, headers):
    url = f"{opengit_url}/groups/{group_id}"
    group_response = requests.get(url,headers=headers)
    group_data = group_response.json()
    result = {"group_id": group_data["id"], "group_name": group_data.get("name"),
              "description": group_data.get("description"),
              "group_creation_date": group_data.get("created_at"), "projects_list": []}
    for project in group_data.get("projects"):
        project_brief = {
            "project_id": project.get("id"),
            "project_description": project.get("description"),
            "project_name": project.get("name"),
            "project_creation_date": project.get("created_at"),
            "project_last_activity_date": project.get("last_activity_at"),
        }
        result["projects_list"].append(project_brief)
    return result

# 'https://opengit.ir/api/v4/projects/3062/users'
def project_users(opengit_url, project_id, headers):
    url = f"{opengit_url}/projects/{project_id}/users"
    project_users_response = requests.get(url, headers=headers)
    project_users_data = project_users_response.json()
    result = {"users" : []}
    for user in project_users_data:
        user_info = {"name": user.get("name")}
        result["users"].append(user_info)
    return result

# 'https://opengit.ir/api/v4/projects/3062/commits'
def project_commits(opengit_url, project_id, headers):
    url = f"{opengit_url}/projects/{project_id}/repository/commits"
    project_commits_response = requests.get(url, headers=headers)
    project_commits_data = project_commits_response.json()
    result = {"commits" : []}
    for commit in project_commits_data:
        commits_info = {"commit_creation": commit.get("created_at"),
                        "commit_title": commit.get("title"),
                        "commit_author": commit.get("author_name"),
                        "commit_author_email": commit.get("author_email"),
                        }
        result["commits"].append(commits_info)
    return result

# ToDo: create sample issues and add issues to project_id_info
# 'https://opengit.ir/api/v4/projects/3062/issues'
def project_issues(opengit_url, project_id, headers):
    url = f"{opengit_url}/projects/{project_id}/issues"
    project_issues_response = requests.get(url, headers=headers)
    project_issues_data = project_issues_response.json()
    return project_issues_data

# projects/:id
def project_id_info(opengit_url, project_id, headers):
    """
    Retrieve comprehensive information about a specific GitLab project including its details, users, and commit history.

    This tool fetches and aggregates data from multiple GitLab API endpoints to provide a complete overview
    of a project. It combines project metadata, user list, and recent commit information into a single
    structured result.

    Args:
        opengit_url (str): The base URL of the GitLab instance (e.g., "https://opengit.ir/api/v4").
        project_id (int): The unique identifier of the GitLab project to retrieve information for.
        headers (dict): HTTP headers containing authentication credentials (e.g., Authorization Bearer token)
                       and content type specifications.

    Returns:
        dict: A dictionary containing the following keys:
            - project_group_id (int): The ID of the group/namespace that owns the project.
            - project_group_name (str): The name of the group/namespace that owns the project.
            - project_id (int): The unique identifier of the project.
            - project_name (str): The name of the project.
            - project_description (str or None): The project's description, if any.
            - project_creation_date (str): ISO timestamp of when the project was created.
            - project_last_activity_date (str): ISO timestamp of the project's last activity.
            - project_users (dict): Dictionary containing a 'users' list, each with a 'name' key for project members.
            - project_commits (list): List of commit dictionaries, each containing 'commit_creation' timestamp,
                                     'commit_title' message, and 'commit_author' name.
    """
    url = f"{opengit_url}/projects/{project_id}"
    project_id_info_response = requests.get(url, headers=headers)
    project_id_info_data = project_id_info_response.json()
    project_id_users = project_users(opengit_url, project_id, headers)
    project_id_commits = project_commits(opengit_url, project_id, headers)
    result = {"project_group_id": project_id_info_data.get("namespace").get("id"),
              "project_group_name": project_id_info_data.get("namespace").get("name"),
              "project_id": project_id_info_data.get("id"),
              "project_name": project_id_info_data.get("name"),
              "project_description": project_id_info_data.get("description"),
              "project_creation_date": project_id_info_data.get("created_at"),
              "project_last_activity_date": project_id_info_data.get("last_activity_at"),
              "project_users" : project_id_users,
              "project_commits" : project_id_commits.get("commits"),
              }

    return result


if __name__ == "__main__":
    print(groups(OPENGIT, HEADERS))
    # print(group_info(OPENGIT, GROUP_ID, headers=HEADERS))
    # projects_info(OPENGIT, HEADERS)
    # print(project_issues(OPENGIT, PROJECT_ID, HEADERS))
    # print(project_users(OPENGIT, 3171, HEADERS))
    # print(project_members(OPENGIT, 3171, HEADERS))
    # print(project_commits(OPENGIT, PROJECT_ID, HEADERS))
    # print(project_id_info(OPENGIT, 3171, HEADERS))
