from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.schemas import RegisterRequest, UserResponse
from src.auth.service import authenticate_user, register_student
from src.core.database import get_db

from src.auth.schemas import LoginRequest, RegisterRequest, UserResponse
from src.auth.jwt import create_access_token

from src.auth.dependencies import get_current_user
from src.auth.models import User

from src.auth.rbac import require_roles
from src.auth.models import User, UserRole

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await register_student(
            db=db,
            name=request.name,
            email=request.email,
            password=request.password,
        )

        return user

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )



@router.post("/login")
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await authenticate_user(
        db=db,
        email=request.email,
        password=request.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    access_token = create_access_token(user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user