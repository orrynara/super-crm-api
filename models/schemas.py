from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


# ─── Customers ───────────────────────────────
class CustomerCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    category: Optional[str] = "new"
    status: Optional[str] = "active"
    address: Optional[str] = None
    birth_date: Optional[date] = None

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    address: Optional[str] = None
    birth_date: Optional[date] = None

class CustomerResponse(BaseModel):
    id: str
    name: str
    phone: Optional[str]
    category: Optional[str]
    status: Optional[str]
    address: Optional[str]
    birth_date: Optional[date]
    agent_id: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


# ─── Activities ──────────────────────────────
class ActivityCreate(BaseModel):
    customer_id: str
    activity_date: date
    activity_type: Optional[str] = "call"
    content: Optional[str] = None
    next_step: Optional[str] = None
    manager_name: Optional[str] = None

class ActivityUpdate(BaseModel):
    activity_date: Optional[date] = None
    activity_type: Optional[str] = None
    content: Optional[str] = None
    next_step: Optional[str] = None
    manager_name: Optional[str] = None

class ActivityResponse(BaseModel):
    id: str
    customer_id: str
    activity_date: date
    activity_type: Optional[str]
    content: Optional[str]
    next_step: Optional[str]
    manager_name: Optional[str]
    agent_id: Optional[str]
    created_at: Optional[datetime]


# ─── Common Codes ─────────────────────────────
class CodeCreate(BaseModel):
    group_name: str
    item_name: str
    item_value: str
    sort_order: Optional[int] = 0

class CodeResponse(BaseModel):
    id: int
    group_name: str
    item_name: str
    item_value: str
    sort_order: int
    is_active: bool


# ─── API 공통 응답 형식 ─────────────────────
class ApiResponse(BaseModel):
    success: bool
    data: Optional[object] = None
    message: str = ""
