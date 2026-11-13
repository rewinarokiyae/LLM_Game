"""
Command Handler for Terminal Slash Commands.
Handles:
/help, /whoami, /status, /summary, /workload, /timetable, /assignments,
/policy, /violations, /history, /analytics, /data-quality, /test, /logout, /exit.
"""

from typing import Optional, Dict, Any
from app.security.access_control import UserContext
from app.nlp.query_router import QueryRouter
from app.tools.registry import tool_registry
from app.response.response_generator import ResponseGenerator


class CommandHandler:
    @staticmethod
    def handle_command(cmd: str, user_context: UserContext) -> Optional[Dict[str, Any]]:
        clean_cmd = cmd.strip().lower()

        if clean_cmd in ["/whoami", "whoami"]:
            user_data = tool_registry.get_current_user(user_context)
            resp = (
                f"### Current Session Identity\n"
                f"- **Username:** {user_data['username']}\n"
                f"- **User ID:** {user_data['user_id']}\n"
                f"- **Role:** {user_data['role']}\n"
                f"- **Faculty ID:** {user_data['faculty_id'] or 'N/A'}\n"
                f"- **Faculty Name:** {user_data['faculty_name'] or 'N/A'}\n"
                f"- **Authorized Scope:** {user_data['department_scope']}"
            )
            return {"command": "whoami", "response": resp}

        elif clean_cmd in ["/workload", "workload"]:
            return QueryRouter.process_query(user_context, "How many hours am I teaching this week?")

        elif clean_cmd in ["/timetable", "timetable"]:
            return QueryRouter.process_query(user_context, "Show my timetable")

        elif clean_cmd in ["/violations", "violations"]:
            if user_context.is_faculty():
                return QueryRouter.process_query(user_context, "Am I exceeding my weekly teaching-hour limit?")
            else:
                return QueryRouter.process_query(user_context, "Which faculty members exceed policy limits?")

        elif clean_cmd in ["/assignments", "assignments"]:
            return QueryRouter.process_query(user_context, "Which assignments are pending for me?")

        elif clean_cmd in ["/policy", "policy"]:
            return QueryRouter.process_query(user_context, "What is the workload policy for my designation?")

        elif clean_cmd in ["/history", "history"]:
            return QueryRouter.process_query(user_context, "Show my historical workload trends")

        elif clean_cmd in ["/analytics", "analytics"]:
            if user_context.is_admin():
                return QueryRouter.process_query(user_context, "Which department has the highest total scheduled teaching hours?")
            else:
                return QueryRouter.process_query(user_context, "Show department workload distribution")

        elif clean_cmd in ["/data-quality", "data-quality"]:
            return QueryRouter.process_query(user_context, "Show data quality and integrity report")

        elif clean_cmd in ["/help", "help", "/?"]:
            return QueryRouter.process_query(user_context, "/help")

        elif clean_cmd in ["/summary", "summary"]:
            if user_context.is_faculty():
                return QueryRouter.process_query(user_context, "How many hours am I teaching this week?")
            else:
                return QueryRouter.process_query(user_context, "Show department workload summary")

        return None

