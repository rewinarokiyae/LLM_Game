"""
Audit Logging Service.
Logs all queries, tool executions, and security checks into the audit_logs table.
"""

from datetime import datetime
from typing import Optional
from app.config.logging_config import logger
from app.database.connection import get_db_session
from app.database.models import AuditLog
from app.security.access_control import UserContext


class AuditLogger:
    @staticmethod
    def log_event(
        action: str,
        user_context: Optional[UserContext] = None,
        resource: Optional[str] = None,
        details: Optional[str] = None,
        status: str = "SUCCESS"
    ):
        try:
            with get_db_session() as session:
                log = AuditLog(
                    timestamp=datetime.utcnow(),
                    user_id=user_context.user_id if user_context else None,
                    username=user_context.username if user_context else "anonymous",
                    role=user_context.role.value if user_context else None,
                    department_scope=user_context.department_scope if user_context else None,
                    action=action,
                    resource=resource,
                    details=details,
                    status=status
                )
                session.add(log)
            logger.debug(f"Audit event logged: action={action}, status={status}, user={user_context.username if user_context else 'None'}")
        except Exception as e:
            logger.error(f"Failed to record audit log: {e}")

