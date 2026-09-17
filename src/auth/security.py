from pwdlib import PasswordHash
from fastapi import APIRouter
from src.auth.models import User
from src.auth.schemas import RegisterRequest,UserResponse,LoginRequest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from fastapi import Depends
from src.core.database import get_db



password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)
