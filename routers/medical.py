from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import date
from pydantic import BaseModel
from services.supabase_client import supabase
from models.schemas import ApiResponse

router = APIRouter(prefix="/api/v1/medical", tags=["medical"])


class MedicalCreate(BaseModel):
    customer_id: str
    incident_date: Optional[date] = None
    disease_name: Optional[str] = None
    treatment_date: Optional[date] = None
    treatment_name: Optional[str] = None
    hospital_days: Optional[int] = None
    claim_amount: Optional[int] = None
    paid_amount: Optional[int] = None
    insurer: Optional[str] = None
    memo: Optional[str] = None


class MedicalUpdate(BaseModel):
    incident_date: Optional[date] = None
    disease_name: Optional[str] = None
    treatment_date: Optional[date] = None
    treatment_name: Optional[str] = None
    hospital_days: Optional[int] = None
    claim_amount: Optional[int] = None
    paid_amount: Optional[int] = None
    insurer: Optional[str] = None
    memo: Optional[str] = None


@router.get("/customer/{customer_id}")
def list_medical(customer_id: str):
    """고객별 의료정보 조회"""
    try:
        result = supabase.table("medical_records") \
            .select("*") \
            .eq("customer_id", customer_id) \
            .order("incident_date", desc=True) \
            .execute()
        return ApiResponse(success=True, data=result.data, message=f"{len(result.data)}건")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_medical(body: MedicalCreate):
    """의료정보 등록"""
    try:
        payload = {k: str(v) if isinstance(v, date) else v
                   for k, v in body.dict().items() if v is not None}
        result = supabase.table("medical_records").insert(payload).execute()
        return ApiResponse(success=True, data=result.data[0] if result.data else {}, message="의료정보 등록 완료")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{record_id}")
def update_medical(record_id: str, body: MedicalUpdate):
    """의료정보 수정"""
    try:
        payload = {k: str(v) if isinstance(v, date) else v
                   for k, v in body.dict().items() if v is not None}
        if not payload:
            raise HTTPException(status_code=400, detail="수정할 항목이 없습니다.")
        result = supabase.table("medical_records").update(payload).eq("id", record_id).execute()
        return ApiResponse(success=True, data=result.data[0] if result.data else {}, message="수정 완료")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{record_id}")
def delete_medical(record_id: str):
    """의료정보 삭제"""
    try:
        supabase.table("medical_records").delete().eq("id", record_id).execute()
        return ApiResponse(success=True, message="삭제 완료")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
