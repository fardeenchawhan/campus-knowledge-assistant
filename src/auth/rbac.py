from fastapi import Depends, HTTPException, status

from src.auth.dependencies import get_current_user
from src.auth.models import User, UserRole


def require_roles(*allowed_roles: UserRole):

    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:

        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )

        return current_user

    return role_checker


def get_allowed_access_levels(role: UserRole) -> list[str]:
    if role == UserRole.STUDENT:
        return ["student"]

    if role == UserRole.PROFESSOR:
        return ["student", "professor"]

    if role == UserRole.ADMIN:
        return ["student", "professor", "admin"]

    return []