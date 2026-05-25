import os
import asyncio
from dotenv import load_dotenv
from agno.models.openai.like import OpenAILike
from agno.agent import Agent
import xmlrpc.client
import logging
# Configure logger for the module
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
load_dotenv()

# Odoo requirements
# url = 'http://localhost:8069'
# username = 'mahanbabelian@gmail.com'
# password = 'mahan1234'
# db = 'burna'
# API_KEY = '105455be154b024f12281829642cb134d41d8768'
# common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
# user_uid = common.authenticate(db, username, password, {})
# model = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

api_key = os.getenv("METIS_API_KEY")
base_url = os.getenv("METIS_BASE_URL")

model = OpenAILike(
    id="gpt-4o",  # Your model name
    api_key=api_key,
    base_url=base_url
)

async def atask1(delay: int):
    """Simulate a task that takes a random amount of time to complete
    Args:
        delay (int): The amount of time to delay the task
    """
    logger.info("Task 1 has started")
    for _ in range(delay):
        await asyncio.sleep(1)
        logger.info("Task 1 has slept for 1s")
    logger.info("Task 1 has completed")
    return f"Task 1 completed in {delay:.2f}s"


async def atask2(delay: int):
    """Simulate a task that takes a random amount of time to complete
    Args:
        delay (int): The amount of time to delay the task
    """
    logger.info("Task 2 has started")
    for _ in range(delay):
        await asyncio.sleep(1)
        logger.info("Task 2 has slept for 1s")
    logger.info("Task 2 has completed")
    return f"Task 2 completed in {delay:.2f}s"


async def atask3(delay: int):
    """Simulate a task that takes a random amount of time to complete
    Args:
        delay (int): The amount of time to delay the task
    """
    logger.info("Task 3 has started")
    for _ in range(delay):
        await asyncio.sleep(1)
        logger.info("Task 3 has slept for 1s")
    logger.info("Task 3 has completed")
    return f"Task 3 completed in {delay:.2f}s"

async_agent = Agent(
    model=model,
    tools=[atask2, atask1, atask3],
    markdown=True
)

asyncio.run(
    async_agent.aprint_response("Please run all tasks with a delay of 3s", stream=True)
)