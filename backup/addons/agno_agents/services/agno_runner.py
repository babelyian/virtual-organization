# -*- coding: utf-8 -*-
import argparse
import json
import os
import sys
import time
import logging
import traceback
from agno.agent import Agent
from agno.models.openai.like import OpenAILike
from agno.os import AgentOS
from agno.db.sqlite import SqliteDb


def mask_secret(value: str, show: int = 6):
    if not value:
        return "<EMPTY>"
    if len(value) <= show:
        return "*" * len(value)
    return value[:show] + ("*" * (len(value) - show))


def setup_logging(log_path: str, debug: bool = True):
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.getLogger("httpx").setLevel(logging.DEBUG if debug else logging.INFO)
    logging.getLogger("httpcore").setLevel(logging.DEBUG if debug else logging.INFO)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to JSON config")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    log_path = cfg["log_path"]
    setup_logging(log_path, debug=bool(cfg.get("debug_mode", False)))
    log = logging.getLogger("agno_runner")

    os.environ.setdefault("AGNO_TELEMETRY", "false")
    os.environ.setdefault("PYTHONUNBUFFERED", "1")

    log.info("=== Agno Agent starting ===")
    log.info("time=%s", time.strftime("%Y-%m-%d %H:%M:%S"))
    log.info("python=%s", sys.executable)
    log.info("cwd=%s", os.getcwd())
    log.info("config_path=%s", args.config)
    log.info("log_path=%s", log_path)

    api_key = cfg.get("api_key", "")
    log.info("agent_name=%s", cfg.get("agent_name", ""))
    log.info("host=%s", cfg.get("host", "0.0.0.0"))
    log.info("port=%s", cfg.get("port", 7777))
    log.info("model_name=%s", cfg.get("model_name", ""))
    log.info("base_url=%s", cfg.get("base_url", ""))
    log.info("db_file=%s", cfg.get("db_file", "agent.db"))
    log.info("api_key_length=%s", len(api_key))
    log.info("api_key_preview=%s", mask_secret(api_key, 6))

    model = OpenAILike(
        id=cfg.get("model_name", ""),
        base_url=cfg.get("base_url", ""),
        api_key=api_key,
    )

    db = SqliteDb(db_file=cfg.get("db_file", "agent.db"))

    agent_obj = Agent(
        id=cfg.get("agent_name", ""),
        name=cfg.get("agent_name", ""),
        role=cfg.get("agent_role", ""),
        model=model,
        instructions=cfg.get("instructions", ""),
        db=db,
        add_history_to_context=bool(cfg.get("add_history_to_context", True)),
        add_datetime_to_context=bool(cfg.get("add_datetime_to_context", False)),
        markdown=bool(cfg.get("markdown", True)),
        debug_mode=bool(cfg.get("debug_mode", False)),
        num_history_runs=int(cfg.get("num_history_runs", 5)),
    )
    log.info("Agent OS serving agent with ID: %s", agent_obj.id)
    
    agent_os = AgentOS(agents=[agent_obj])
    app = agent_os.get_app()

    host = cfg.get("host", "0.0.0.0")
    port = int(cfg.get("port", 7777))

    log.info("Serving on http://%s:%s", host, port)
    agent_os.serve(app=app, host=host, port=port, reload=False)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.getLogger("agno_runner").error("Agent crashed: %s", e)
        logging.getLogger("agno_runner").error(traceback.format_exc())
        raise
