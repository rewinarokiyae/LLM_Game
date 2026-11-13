"""
Security and Access Control Models.
Defines user context, roles, permissions, and scope enforcement rules.
"""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class RoleEnum(str, Enum):
    FACULTY = "FACULTY"
    HOD = "HOD"
    ADMIN = "ADMIN"


class UserContext(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    username: str
    role: RoleEnum
    department_scope: str  # e.g., "DEP-CSE", "DEP-AIML", "DEP-DS", "ALL"
    faculty_id: Optional[str] = None
    faculty_name: Optional[str] = None

    def is_admin(self) -> bool:
        return self.role == RoleEnum.ADMIN

    def is_hod(self) -> bool:
        return self.role == RoleEnum.HOD

    def is_faculty(self) -> bool:
        return self.role == RoleEnum.FACULTY

    def can_access_faculty(self, target_faculty_id: str, target_department_id: Optional[str] = None) -> bool:
        """
        Check if current authenticated context can access data for target_faculty_id.
        - ADMIN can access all faculty.
        - HOD can access faculty in their department_scope.
        - FACULTY can only access their own records.
        """
        if self.is_admin():
            return True
        if self.is_faculty():
            return self.faculty_id == target_faculty_id
        if self.is_hod():
            if target_department_id:
                return self.department_scope == "ALL" or self.department_scope == target_department_id
            # If target department not provided, must be verified by caller or same faculty
            return self.faculty_id == target_faculty_id
        return False

    def can_access_department(self, target_department_id: str) -> bool:
        """
        Check if current context can access department-level data.
        - ADMIN: all departments.
        - HOD: only their department_scope.
        - FACULTY: none (unless viewing generic public info).
        """
        if self.is_admin():
            return True
        if self.is_hod():
            return self.department_scope == "ALL" or self.department_scope == target_department_id
        return False


class AccessDeniedError(Exception):
    """Raised when an operation violates role-based access control policies."""
    def __init__(self, message: str = "Access Denied: You do not have permission to view or execute this resource."):
        super().__init__(message)
        self.message = message

