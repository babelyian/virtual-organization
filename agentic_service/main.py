import os
import asyncio
from dotenv import load_dotenv
from agno.models.openai.like import OpenAILike
from agno.agent import Agent

from tools.project_module_tools import get_projects_summary, get_project_tasks_headers, get_task_details

import logging
# Configure logger for the module
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
load_dotenv()

url = os.getenv("ODOO_URL")
db = os.getenv("ODOO_DB")
username = os.getenv("ODOO_USERNAME")
password = os.getenv("ODOO_PASSWORD")
api_key = os.getenv("METIS_API_KEY")
base_url = os.getenv("METIS_BASE_URL")

model = OpenAILike(
    id="gpt-4o-mini",  # Your model name
    api_key=api_key,
    base_url=base_url
)

async_agent = Agent(
    model=model,
    tools=[get_projects_summary, get_project_tasks_headers, get_task_details],
    markdown=True
)

## tools check before toke burn
try:
    print("*"*30 + "get_projects_summary\n",asyncio.run(get_projects_summary()),"*"*30 + "\n")
    print("*"*30 + "get_project_tasks_headers\n", asyncio.run(get_project_tasks_headers(1)), "*"*30 + "\n")
    print("*"*30 + "get_task_details\n", asyncio.run(get_task_details(8)), "*"*30 + "\n")
    # asyncio.run(
    #     async_agent.aprint_response("List all ongoing projects and their ongoing tasks, highlight overdue ones", stream=True)
    # )
except Exception as e:
    print("Error", e)
