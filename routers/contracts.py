from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import date
from pydantic import BaseModel
from services.supabase_client import supabase
from models.schemas import ApiResponse

router = APIRouter(prefix="/api/v1/contracts", tags=["contracts"])


class ContractCreate(BaseModel):
    customer_id: str
    insurer: Optional[str] = None
    product_name: Optional[str] = None
    contract_date: Optional[date] = None
    monthly_premium: Optional[int] = None
    payment_period: Optional[str] = None
    insurance_period: Optional[str] = None
    policy_number: Optional[str] = None
    status: Optional[str] = "active"
    memo: Optional[str] = None


class ContractUpdate(BaseModel):
    insurer: Optional[str] = None
    product_name: Optional[str] = None
    contract_date: Optional[date] = None
    monthly_premium: Optional[int] = None
    payment_period: Optional[str] = None
    insurance_period: Optional[str] = None
    policy_number: Optional[str] = None
    status: Optional[str] = None
    memo: Optional[str] = None


@router.get("/customer/{customer_id}")
def list_contracts(customer_id: str):
    """고객별 계약 목록 조회"""
    try:
        result = supabase.table("contracts") \
            .select("*") \
            .eq("customer_id", customer_id) \
            .order("contract_date", desc=True) \
            .execute()
        return ApiResponse(success=True, data=result.data, message=f"{len(result.data)}건")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_contract(body: ContractCreate):
    """계약 등록"""
    try:
        payload = {k: str(v) if isinstance(v, date) else v
                   for k, v in body.dict().items() if v is not None}
        result = supabase.table("contracts").insert(payload).execute()
        return ApiResponse(success=True, data=result.data[0] if result.data else {}, message="계약 등록 완료")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{contract_id}")
def update_contract(contract_id: str, body: ContractUpdate):
    """계약 수정"""
    try:
        payload = {k: str(v) if isinstance(v, date) else v
                   for k, v in body.dict().items() if v is not None}
        if not payload:
            raise HTTPException(status_code=400, detail="수정할 항목이 없습니다.")
        result = supabase.table("contracts").update(payload).eq("id", contract_id).execute()
        return ApiResponse(success=True, data=result.data[0] if result.data else {}, message="수정 완료")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{contract_id}")
def delete_contract(contract_id: str):
    """계약 삭제"""
    try:
        supabase.table("contracts").delete().eq("id", contract_id).execute()
        return ApiResponse(success=True, message="삭제 완료")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
def contract_stats():
    """전체 계약 통계"""
    try:
        result = supabase.table("contracts").select("status, monthly_premium").execute()
        data = result.data or []
        total = len(data)
        active = sum(1 for r in data if r.get("status") == "active")
        total_premium = sum(r.get("monthly_premium") or 0 for r in data if r.get("status") == "active")
        return ApiResponse(success=True, data={
            "total": total, "active": active, "total_premium": total_premium
        }, message="통계 조회 완료")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
