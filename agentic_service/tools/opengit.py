from decouple import config
import requests
from datetime import datetime
from typing import Dict, List, Optional
from utils.time_intervals import TIME_INTERVALS
OPENGIT = "https://opengit.ir/api/v4"
TOKEN = config("OPENGIT_ACCESS_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}
#
# def parse_commit_date(date_string: str) -> datetime:
#     """Parse commit dates with or without timezone"""
#     try:
#         # Try with timezone first
#         return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%f%z")
#     except ValueError:
#         try:
#             # Try without timezone
#             return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%f")
#         except ValueError:
#             try:
#                 # Try without microseconds
#                 return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S")
#             except ValueError:
#                 # Try with just date
#                 return datetime.strptime(date_string, "%Y-%m-%d")


def filter_commits_by_date_simple(
        commits_dict: Dict,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
) -> Dict:
    """
    Simplified version - converts everything to naive datetime directly.
    """

    def to_naive(date_str: str) -> datetime:
        """Convert any datetime string to naive datetime"""
        # Remove timezone info
        if '+' in date_str:
            date_str = date_str.split('+')[0]
        elif date_str.endswith('Z'):
            date_str = date_str[:-1]

        # Try different formats
        formats = [
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d"
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        raise ValueError(f"Unable to parse date: {date_str}")

    if 'commits' not in commits_dict:
        return {'commits': []}

    filtered_commits = []

    for commit in commits_dict['commits']:
        commit_date = to_naive(commit['commit_creation'])

        if start_date:
            start = to_naive(start_date)
            if commit_date < start:
                continue

        if end_date:
            end = to_naive(end_date)
            if commit_date > end:
                continue

        filtered_commits.append(commit)

    return {'commits': filtered_commits}

# groups
def groups(opengit_url, headers):
    url = f"{opengit_url}/groups"
    group_response = requests.get(url,headers=headers)
    group_data = group_response.json()
    return group_data

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

def group_commits(opengit_url, group_id, headers, time_range=None):
    try:
        if time_range:
            start, end = TIME_INTERVALS[time_range]
        group_info_result = group_info(opengit_url, group_id, headers)
        result = {"group_id": group_info_result["group_id"], "group_name": group_info_result["group_name"], "projects":[]}
        for project in group_info_result.get("projects_list"):
            project_dict = {"project_id": project["project_id"], "project_name": project["project_name"]}
            commits = project_commits(opengit_url, project["project_id"], headers)
            if time_range and commits:
                commits = filter_commits_by_date_simple(commits, start, end)
            if commits.get("commits"):
                project_dict.update(commits)
                result["projects"].append(project_dict)
        return result
    except Exception as e:
        print("Error %s" % e)


def department_commits(department_name, time_range=None):
    """
    Retrieve commit statistics for all projects within a specific department group.

    This tool fetches all projects belonging to a department group in GitLab and
    calculates total commit counts across all repositories within that department.
    Useful for measuring development activity, team productivity, or generating
    department-level reports.

    Args:
        department_name (str): The exact name of the department/group as it appears
            in GitLab (e.g., 'Keyman_KMS', 'Engineering', 'Product_Team').
            Case-sensitive - must match the group name exactly.
        time_range: Optional time filter - one of ['last_week', 'last_month',
                   'next_week', 'next_month', 'today', 'yesterday']

    Returns:
        dict: A dictionary containing department commit statistics with the following keys:
            - department_name (str): Name of the department/group
            - projects_count (int): Total number of projects in the department
            - commits_count (int): Total number of commits across all projects
                (sum of commits in each project within the specified time range)

    Returns None if:
        - The specified department_name does not exist in OpenGit
        - The department has no accessible projects
        - Network/authentication error occurs (handled by called functions)
    """

    groups_result = groups(OPENGIT, HEADERS)
    department_id = None
    for item in groups_result:
        if item.get("name")==department_name:
            department_id = item.get("id")
            break
    if not department_id:
        return None
    else:
        commits =  group_commits(OPENGIT, department_id, HEADERS, time_range)
        total_commits = 0
        for project in commits['projects']:
            commits_count = len(project.get('commits', []))
            total_commits += commits_count
        result = {"department_name": commits.get("group_name"), "projects_count": len(commits.get("projects")), "commits_count":total_commits}
        return result

if __name__ == "__main__":

    # print(group_commits(OPENGIT, 1202, HEADERS,"last_week"))
    print(department_commits("Keyman_KMS", "last_week"))
