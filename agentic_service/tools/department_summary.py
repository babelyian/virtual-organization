from typing import Any, Dict, List, Optional
import asyncio

from tools.calendar_module import get_list_of_events
from tools.project_module import department_tasks


async def get_department_activity_summary(
    department_id: Optional[List[Any]] = None,
    time_range: Optional[str] = None
) -> dict[str, int | dict[str, int]]:
    """
     Get combined task and meeting activity summary for departments.

    Use this tool when users want productivity overviews, team comparisons,
    or workload analysis across departments.

    Args:
        department_id: List of department IDs (None = all departments)
        time_range: 'today', 'yesterday', 'last_week', 'last_month', 'next_week', 'next_month'

    Returns:
        {
            "department_task_summary": {
                "number_of_projects": int,
                "number_of_tasks": int,
                "task_stats": {"in_progress": int, "completed": int, "deadline_passed": int}
            },
            "department_meetings_summary": {
                "number_of_meetings": int,
                "total_duration_of_meetings": float  # hours
            }
        }
    Note:
        to use this tool with input department_id first get department ID from tool "department_id_by_name"
    """
    tasks_summary = await department_tasks(department_id, time_range)
    events_result = await get_list_of_events(department_id, time_range)
    events_summary = {
        "number_of_meetings": len(events_result.get("events", 0)),
        "total_duration_of_meetings": sum(event['duration_in_hours'] for event in events_result['events'])
    }
    result = {
        "department_task_summary": tasks_summary,
        "department_meetings_summary": events_summary,
    }
    return result

if __name__ == "__main__":
    print(asyncio.run(get_department_activity_summary(department_id=[4],time_range="next_week")))