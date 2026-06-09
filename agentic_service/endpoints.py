# endpoints.py
import asyncio
import logging
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from contextlib import asynccontextmanager

# Import your agent components
from agno.models.openai.like import OpenAILike
from agno.agent import Agent
from tools.project_module import get_projects_summary, get_project_tasks_headers, get_task_details, department_tasks
from tools.calendar_module import get_list_of_events
from tools.department_id_by_name import get_department_id_by_name
from tools.department_summary import get_department_activity_summary
from tools.opengit import department_commits

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# Configuration models
class AgentConfig(BaseModel):
    agent_name: str
    instructions: str = ""
    model_name: str = "gpt-4o-mini"
    base_url: str
    api_key: str
    add_history_to_context: bool = True
    add_datetime_to_context: bool = False
    markdown: bool = True
    debug_mode: bool = False
    num_history_runs: int = 5


class RunPromptRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


# Store active agents and their configurations
active_agents: Dict[str, Dict] = {}  # agent_id -> {"agent": Agent, "config": AgentConfig, "status": str}
sessions: Dict[str, Dict] = {}  # session_id -> {"agent_id": str, "history": list}

# Environment variables for Odoo connection
import os
from dotenv import load_dotenv

load_dotenv()

ODOO_URL = os.getenv("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.getenv("ODOO_DB", "odoo")
ODOO_USERNAME = os.getenv("ODOO_USERNAME", "admin")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "admin")
API_KEY = os.getenv("METIS_API_KEY")
BASE_URL = os.getenv("METIS_BASE_URL", "https://api.metisai.ir/openai/v1")


def create_agent_from_config(config: AgentConfig):
    """Create an Agno Agent instance from configuration"""
    try:
        with open('prompts/system_prompt.md', 'r', encoding='utf-8') as file:
            system_prompt = file.read()

        model = OpenAILike(
            id=config.model_name,
            api_key=config.api_key,
            base_url=config.base_url
        )

        # Use the tools from your tools module
        tools = [
            get_projects_summary, get_project_tasks_headers, get_task_details,
            get_list_of_events, get_department_id_by_name, department_tasks, get_department_activity_summary,
            department_commits
        ]
        print("config.markdown:", config.markdown)
        agent = Agent(
            model=model,
            tools=tools,
            markdown=config.markdown,
            debug_mode=config.debug_mode,
            instructions=f"""
            here is the system prompt in markdown format providing you the ESSENTIAL guardrails:\n
                {system_prompt}
            \nand here is the user instruction for you:\n
                {config.instructions}""",
            name=config.agent_name,
            add_history_to_context=config.add_history_to_context,
            add_datetime_to_context=config.add_datetime_to_context,
            num_history_runs=config.num_history_runs,
        )

        return agent
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    logger.info("Starting Agent Service...")
    yield
    # Cleanup on shutdown
    logger.info("Shutting down Agent Service...")
    for agent_id in list(active_agents.keys()):
        await stop_agent_internal(agent_id)


app = FastAPI(
    title="Agno Agent Service",
    description="External agent service for Odoo integration",
    version="1.0.0",
    lifespan=lifespan
)


async def start_agent_internal(agent_id: str, config: AgentConfig) -> Dict:
    """Internal function to start an agent"""
    try:
        # Check if agent already exists
        if agent_id in active_agents:
            return {"success": False, "error": "Agent already running"}

        # Create and store the agent
        agent = create_agent_from_config(config)
        active_agents[agent_id] = {
            "agent": agent,
            "config": config,
            "status": "running",
            "started_at": asyncio.get_event_loop().time()
        }

        logger.info(f"Agent {agent_id} started successfully")
        return {"success": True, "status": "running", "agent_id": agent_id}

    except Exception as e:
        logger.error(f"Failed to start agent {agent_id}: {e}")
        return {"success": False, "error": str(e)}


async def stop_agent_internal(agent_id: str) -> Dict:
    """Internal function to stop an agent"""
    if agent_id not in active_agents:
        return {"success": False, "error": "Agent not found"}

    # Remove agent from active agents
    active_agents.pop(agent_id)
    logger.info(f"Agent {agent_id} stopped")

    return {"success": True, "status": "stopped"}


# API Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "active_agents": len(active_agents)}


@app.post("/agents/{agent_id}/start")
async def start_agent(
        agent_id: str,
        config: AgentConfig,
        background_tasks: BackgroundTasks = None
):
    logger.info(f"Received start request for agent_id: {agent_id}")
    logger.info(f"Config received: {config}")

    # Check if agent already exists in memory
    if agent_id in active_agents:
        existing_status = active_agents[agent_id].get("status")
        logger.warning(f"Agent {agent_id} already exists with status: {existing_status}")
        # Stop it first
        await stop_agent_internal(agent_id)

    result = await start_agent_internal(agent_id, config)

    if not result["success"]:
        logger.error(f"Failed to start agent: {result.get('error')}")
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@app.post("/agents/{agent_id}/stop")
async def stop_agent(
        agent_id: str
):
    """Stop an agent instance"""
    result = await stop_agent_internal(agent_id)

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@app.get("/agents/{agent_id}/status")
async def get_agent_status(
        agent_id: str
):
    """Get agent status"""
    if agent_id not in active_agents:
        return {"status": "stopped", "agent_id": agent_id}

    agent_info = active_agents[agent_id]
    return {
        "status": agent_info["status"],
        "agent_id": agent_id,
        "started_at": agent_info.get("started_at"),
        "config": {
            "agent_name": agent_info["config"].agent_name,
            "model_name": agent_info["config"].model_name
        }
    }


from fastapi import Request, Form

# endpoint accepts both form data and json
@app.post("/agents/{agent_id}/runs")
async def run_prompt(
        agent_id: str,
        request: Request = None,
        message: Optional[str] = Form(None),
        session_id: Optional[str] = Form(None)
):
    """Send prompt to agent and get response (accepts JSON or form data)"""
    # Log everything
    logger.info(f"Headers: {dict(request.headers)}")
    # Parse request body based on content type
    if request.headers.get("content-type", "").startswith("application/json"):
        # Handle JSON
        body = await request.json()
        prompt_message = body.get("message", "")
        prompt_session_id = body.get("session_id")
    else:
        # Handle form data
        prompt_message = message or ""
        prompt_session_id = session_id

    if not prompt_message:
        raise HTTPException(status_code=422, detail="message field is required")

    # Check if agent is running
    if agent_id not in active_agents:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not running")

    agent_info = active_agents[agent_id]
    agent = agent_info["agent"]

    try:
        # Use session_id for conversation history
        session_id = prompt_session_id or f"session_{agent_id}_{asyncio.get_event_loop().time()}"

        # Store session if needed
        if session_id not in sessions:
            sessions[session_id] = {
                "agent_id": agent_id,
                "history": []
            }

        # Update last used timestamp
        agent_info["last_used"] = asyncio.get_event_loop().time()

        # Run the agent response
        response = await agent.arun(prompt_message)

        # Extract just the content from the response
        if hasattr(response, 'content'):
            response_content = response.content
        elif isinstance(response, dict):
            response_content = response.get('content', str(response))
        else:
            response_content = str(response)

        # Store in history
        sessions[session_id]["history"].append({
            "user": prompt_message,
            "agent": response_content,
            "timestamp": asyncio.get_event_loop().time()
        })
        print(response_content)
        return {
            "success": True,
            "response": response_content,
            "session_id": session_id,
            "agent_id": agent_id
        }

    except Exception as e:
        logger.error(f"Error processing prompt for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/{agent_id}/run/stream")
async def run_prompt_stream(
        agent_id: str,
        request: RunPromptRequest
):
    """Send prompt to agent and stream response"""
    if agent_id not in active_agents:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not running")

    agent_info = active_agents[agent_id]
    agent = agent_info["agent"]

    async def generate():
        try:
            # Update last used timestamp
            agent_info["last_used"] = asyncio.get_event_loop().time()

            # Stream the response
            async for chunk in agent.arun_stream(request.message):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/agents")
async def list_agents():
    """List all active agents"""
    agents_list = []
    for agent_id, info in active_agents.items():
        agents_list.append({
            "agent_id": agent_id,
            "agent_name": info["config"].agent_name,
            "status": info["status"],
            "started_at": info.get("started_at")
        })

    return {"success": True, "agents": agents_list}


@app.delete("/agents/{agent_id}/sessions/{session_id}")
async def clear_session(
        agent_id: str,
        session_id: str
):
    """Clear session history for an agent"""
    if session_id in sessions:
        # Verify the session belongs to the agent
        if sessions[session_id]["agent_id"] == agent_id:
            sessions.pop(session_id)
            return {"success": True, "message": f"Session {session_id} cleared"}

    raise HTTPException(status_code=404, detail="Session not found")


# Cleanup idle agents periodically
async def cleanup_idle_agents():
    """Clean up agents that haven't been used for a while"""
    while True:
        await asyncio.sleep(300)  # Check every 5 minutes
        current_time = asyncio.get_event_loop().time()
        idle_threshold = 3600  # 1 hour idle timeout

        for agent_id, info in list(active_agents.items()):
            last_used = info.get("last_used", info.get("started_at", 0))
            if current_time - last_used > idle_threshold:
                logger.info(f"Cleaning up idle agent: {agent_id}")
                await stop_agent_internal(agent_id)


@app.on_event("startup")
async def startup_event():
    """Start background task to cleanup idle agents"""
    asyncio.create_task(cleanup_idle_agents())


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Log validation errors"""
    logger.error(f"Validation error for request to {request.url}")

    # Safely get request body
    body_text = ""
    try:
        body = await request.body()
        body_text = body.decode('utf-8', errors='ignore')
    except Exception:
        body_text = "<could not read body>"

    logger.error(f"Request body: {body_text}")
    logger.error(f"Validation errors: {exc.errors()}")

    # Return serializable response
    return JSONResponse(
        status_code=422,
        content={
            "detail": [
                {
                    "loc": err.get("loc", []),
                    "msg": err.get("msg", ""),
                    "type": err.get("type", "")
                }
                for err in exc.errors()
            ],
            "body": body_text[:1000]  # Truncate long bodies
        },
    )