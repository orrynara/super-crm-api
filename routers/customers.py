from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from models.schemas import CustomerCreate, CustomerUpdate, ApiResponse
from services.supabase_client import supabase

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@router.get("")
def get_customers(
    status: Optional[str] = Query(None, description="관리상태 필터"),
    category: Optional[str] = Query(None, description="고객구분 필터"),
    search: Optional[str] = Query(None, description="이름/연락처 검색"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """고객 목록 조회 (검색/필터/페이징)"""
    try:
        query = supabase.table("customers").select("*")
        if status:
            query = query.eq("status", status)
        if category:
            query = query.eq("category", category)
        if search:
            query = query.or_(f"name.ilike.%{search}%,phone.ilike.%{search}%")
        offset = (page - 1) * size
        result = query.order("created_at", desc=True).range(offset, offset + size - 1).execute()
        return ApiResponse(success=True, data=result.data, message=f"{len(result.data)}건 조회")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{customer_id}")
def get_customer(customer_id: str):
    """고객 상세 조회"""
    try:
        result = supabase.table("customers").select("*").eq("id", customer_id).single().execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="고객을 찾을 수 없습니다.")
        return ApiResponse(success=True, data=result.data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_customer(body: CustomerCreate):
    """고객 등록"""
    try:
        data = body.model_dump(exclude_none=True)
        if body.birth_date:
            data["birth_date"] = str(body.birth_date)
        result = supabase.table("customers").insert(data).execute()
        return ApiResponse(success=True, data=result.data[0], message="고객이 등록되었습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{customer_id}")
def update_customer(customer_id: str, body: CustomerUpdate):
    """고객 정보 수정"""
    try:
        data = body.model_dump(exclude_none=True)
        if body.birth_date:
            data["birth_date"] = str(body.birth_date)
        result = supabase.table("customers").update(data).eq("id", customer_id).execute()
        return ApiResponse(success=True, data=result.data[0], message="수정되었습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{customer_id}")
def delete_customer(customer_id: str):
    """고객 삭제"""
    try:
        supabase.table("customers").delete().eq("id", customer_id).execute()
        return ApiResponse(success=True, message="삭제되었습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
