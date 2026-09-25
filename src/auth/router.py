from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request
from src.auth.security import hash_password, verify_password
from src.auth.schemas import ChangePasswordRequest, RegisterRequest, UpdateProfileRequest, UserResponse
from src.auth.service import authenticate_user, register_student
from src.core.database import get_db
from src.core.rate_limit import LOGIN_LIMITER, REGISTER_LIMITER, get_client_ip
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
    ip_request: Request,
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):

    await REGISTER_LIMITER.check(
    f"register:ip:{get_client_ip(ip_request)}"
    )

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
    ip_request: Request,
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):

    await LOGIN_LIMITER.check(
    f"login:ip:{get_client_ip(ip_request)}"
    )

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




@router.patch("/me", response_model=UserResponse)
async def update_me(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.name = request.name

    await db.commit()
    await db.refresh(current_user)

    return current_user


@router.patch("/me/password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(
        request.current_password,
        current_user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    if request.current_password == request.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password.",
        )

    current_user.hashed_password = hash_password(request.new_password)

    await db.commit()

    return {
        "message": "Password updated successfully."
    }