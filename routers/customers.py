from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import date
from models.schemas import CustomerCreate, CustomerUpdate, ApiResponse
from services.supabase_client import supabase

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


def _serialize_dates(data: dict) -> dict:
    """Pydantic date 필드를 PostgreSQL TEXT로 직렬화 (Supabase는 자동 변환 안함)"""
    return {
        k: (v.isoformat() if isinstance(v, date) else v)
        for k, v in data.items()
        if v is not None
    }


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
def get_customer(customer_id: str, with_relations: bool = Query(True, description="가족 정보 포함")):
    """고객 상세 조회 — 가족 정보(relations) 포함"""
    try:
        result = supabase.table("customers").select("*").eq("id", customer_id).single().execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="고객을 찾을 수 없습니다.")

        customer = result.data
        if with_relations:
            relations = supabase.table("customer_relations") \
                .select("*") \
                .eq("customer_id", customer_id) \
                .order("sort_order") \
                .execute()
            customer["relations"] = relations.data or []

        return ApiResponse(success=True, data=customer)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_customer(body: CustomerCreate):
    """
    고객 등록 — 가족 정보(relations) 함께 nested 입력 가능

    Body 예시:
    {
      "name": "강나정",
      "family_head": "강나정",
      "first_meeting_date": "2024-06-24",
      ...50+ 필드...
      "custom_data": {"실손세대 구분": "표준형", "부담보 해제일": "2026-12-31"},
      "relations": [
        {"relation_type": "self", "name": "강나정", "ssn": "1990-...", ...},
        {"relation_type": "spouse", "name": "송수진", ...}
      ]
    }
    """
    try:
        # 1) customer 본체 분리 (relations는 별도)
        customer_data = body.model_dump(exclude={"relations"}, exclude_none=True)
        customer_data = _serialize_dates(customer_data)

        result = supabase.table("customers").insert(customer_data).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="고객 등록 실패")

        new_customer = result.data[0]
        customer_id = new_customer["id"]

        # 2) relations nested insert
        if body.relations:
            relations_payload = []
            for rel in body.relations:
                rel_data = rel.model_dump(exclude_none=True)
                rel_data = _serialize_dates(rel_data)
                rel_data["customer_id"] = customer_id
                relations_payload.append(rel_data)

            if relations_payload:
                rel_result = supabase.table("customer_relations").insert(relations_payload).execute()
                new_customer["relations"] = rel_result.data or []
        else:
            new_customer["relations"] = []

        return ApiResponse(success=True, data=new_customer, message="고객이 등록되었습니다.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{customer_id}")
def update_customer(customer_id: str, body: CustomerUpdate):
    """고객 정보 수정 (relations는 /api/v1/relations 별도 endpoint 사용)"""
    try:
        data = body.model_dump(exclude_none=True)
        data = _serialize_dates(data)
        if not data:
            raise HTTPException(status_code=400, detail="수정할 항목이 없습니다.")

        result = supabase.table("customers").update(data).eq("id", customer_id).execute()
        return ApiResponse(success=True, data=result.data[0] if result.data else {}, message="수정되었습니다.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{customer_id}")
def delete_customer(customer_id: str):
    """고객 삭제 (CASCADE로 relations, contracts, medical_notes 모두 삭제)"""
    try:
        supabase.table("customers").delete().eq("id", customer_id).execute()
        return ApiResponse(success=True, message="삭제되었습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
