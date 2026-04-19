from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str

class FolderCreate(BaseModel):
    name: str
    description: Optional[str] = None

class FolderUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class FolderJudgmentAdd(BaseModel):
    judgment_id: int
    case_number: str
    court: Optional[str] = None
    date: Optional[date] = None
    note: Optional[str] = None

class SearchHistorySave(BaseModel):
    user_id: int
    query: str
    filters: Optional[dict] = None
    answer: Optional[str] = None
    case_numbers: Optional[list[str]] = None

class ChatHistorySave(BaseModel):
    user_id: int
    judgment_id: int
    case_number: str
    court: Optional[str] = None
    question: str
    answer: str