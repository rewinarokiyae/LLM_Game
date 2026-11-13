"""
Authentication Service.
Implements demo authentication with seeded identities from Users_Roles.
Enforces validation and displays clear security notices.
"""

from typing import Optional, List, Dict, Any
from app.config.settings import settings
from app.config.logging_config import logger
from app.database.connection import get_db_session
from app.database.models import UserRole, Faculty
from app.security.access_control import UserContext, RoleEnum, AccessDeniedError


class AuthenticationService:
    DEMO_SECURITY_WARNING = "WARNING: DEMO AUTHENTICATION MODE IS ACTIVE. Passwords are not verified. This mode is strictly for development, testing, and evaluation."

    @classmethod
    def get_demo_users(cls) -> List[Dict[str, Any]]:
        """Return list of seeded demo users for interactive terminal selection."""
        with get_db_session() as session:
            users = session.query(UserRole, Faculty).outerjoin(
                Faculty, UserRole.faculty_id == Faculty.faculty_id
            ).all()

            results = []
            for u, f in users:
                results.append({
                    "user_id": u.user_id,
                    "username": u.username,
                    "role": u.role,
                    "department_scope": u.department_scope,
                    "faculty_id": u.faculty_id,
                    "faculty_name": f.faculty_name if f else ("Institution Administrator" if u.role == "ADMIN" else None),
                    "designation": f.designation if f else ("Administrator" if u.role == "ADMIN" else None)
                })
            return results

    @classmethod
    def authenticate_demo(cls, identifier: str) -> UserContext:
        """
        Authenticate a seeded demo user by user_id, username, or faculty_id.
        """
        if not settings.DEMO_AUTH_ENABLED:
            raise AccessDeniedError("Demo authentication is disabled.")

        clean_id = identifier.strip().lower()

        with get_db_session() as session:
            # Query by user_id, username, faculty_id, or "admin"
            if clean_id == "admin":
                user = session.query(UserRole).filter(UserRole.role == "ADMIN").first()
            else:
                user = session.query(UserRole).filter(
                    (UserRole.user_id.ilike(clean_id)) |
                    (UserRole.username.ilike(clean_id)) |
                    (UserRole.faculty_id.ilike(clean_id)) |
                    (UserRole.username.ilike(f"%{clean_id}%"))
                ).first()

                # If still not found, check by faculty name
                if not user:
                    clean_name = clean_id.replace(".", " ")
                    fac_match = session.query(Faculty).filter(
                        (Faculty.faculty_name.ilike(f"%{clean_id}%")) |
                        (Faculty.faculty_name.ilike(f"%{clean_name}%"))
                    ).first()
                    if fac_match:
                        user = session.query(UserRole).filter(UserRole.faculty_id == fac_match.faculty_id).first()

            if not user:
                raise AccessDeniedError(f"User identity '{identifier}' not found in seeded demo database.")

            faculty_name = None
            if user.faculty_id:
                fac = session.query(Faculty).filter(Faculty.faculty_id == user.faculty_id).first()
                if fac:
                    faculty_name = fac.faculty_name
            elif user.role == "ADMIN":
                faculty_name = "System Administrator"

            context = UserContext(
                user_id=user.user_id,
                username=user.username,
                role=RoleEnum(user.role),
                department_scope=user.department_scope,
                faculty_id=user.faculty_id,
                faculty_name=faculty_name
            )

            logger.info(f"Authenticated demo user: {context.username} (Role: {context.role.value}, Scope: {context.department_scope})")
            return context

