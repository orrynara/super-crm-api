from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Optional
import pandas as pd
import io
from services.supabase_client import supabase
from models.schemas import ApiResponse

router = APIRouter(prefix="/api/v1/import", tags=["import"])


# ── 고객등급 → category 매핑 ─────────────────────────
def map_category(grade: str) -> str:
    if not grade or pd.isna(grade):
        return "new"
    g = str(grade).strip()
    if "01" in g or "우수" in g or "VIP" in g.upper():
        return "vip"
    if "02" in g or "기왕" in g or "기존" in g:
        return "existing"
    if "03" in g or "관리" in g:
        return "existing"
    if "04" in g or "DB" in g.upper() or "신규" in g:
        return "new"
    if "휴면" in g or "05" in g:
        return "dormant"
    return "new"


# ── 주민번호 앞자리 → 생년월일 변환 ─────────────────
def parse_birth(resident_no) -> Optional[str]:
    try:
        s = str(resident_no).replace("-", "").replace(".", "").strip()
        # 앞 6자리만 사용
        s = s[:6]
        if len(s) < 6:
            return None
        yy = int(s[0:2])
        mm = int(s[2:4])
        dd = int(s[4:6])
        if mm < 1 or mm > 12 or dd < 1 or dd > 31:
            return None
        # 00~24 → 2000년대, 25~99 → 1900년대 (보험설계사 고객 기준)
        year = 2000 + yy if yy <= 24 else 1900 + yy
        return f"{year:04d}-{mm:02d}-{dd:02d}"
    except Exception:
        return None


# ── 전화번호 정규화 ───────────────────────────────────
def normalize_phone(phone) -> Optional[str]:
    if not phone or pd.isna(phone):
        return None
    p = str(phone).replace(" ", "").replace("-", "")
    # 숫자만 남기기
    digits = "".join(c for c in p if c.isdigit())
    if len(digits) == 11 and digits.startswith("010"):
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return str(phone).strip() if str(phone).strip() else None


@router.post("/excel/preview")
async def preview_excel(file: UploadFile = File(...)):
    """엑셀 파일 업로드 → 파싱 미리보기 (저장 안함)"""
    if not file.filename.endswith((".xlsx", ".xls", ".xlsm")):
        raise HTTPException(status_code=400, detail="Excel 파일(.xlsx, .xls, .xlsm)만 업로드 가능합니다.")
    try:
        contents = await file.read()

        # 시트 목록 가져오기
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(contents), read_only=True, data_only=True)
        sheet_names = wb.sheetnames
        wb.close()

        # 모든 시트 × 헤더 행(0~19) 순회
        df = None
        col_map = {}
        found_sheet = None
        for sheet in sheet_names:
            for header_row in range(20):
                try:
                    _df = pd.read_excel(io.BytesIO(contents), sheet_name=sheet,
                                        header=header_row, engine="openpyxl")
                    _df.columns = [str(c).strip() for c in _df.columns]
                    _map = {}
                    for col in _df.columns:
                        c = col.strip()
                        if c in ["이름", "성명", "고객이름", "name", "고객명"]:
                            _map["name"] = col
                        elif c in ["휴대폰", "전화", "연락처", "핸드폰", "휴대전화", "phone", "전화번호", "연락처(휴대)"]:
                            _map["phone"] = col
                        elif c in ["고객등급", "등급", "고객구분", "category", "구분"]:
                            _map["category"] = col
                        elif c in ["주민번호앞", "주민앞", "생년월일", "birth", "주민번호", "생년월일(주민앞)"]:
                            _map["birth"] = col
                        elif c in ["직업", "job"]:
                            _map["job"] = col
                        elif c in ["성별", "gender"]:
                            _map["gender"] = col
                        elif c in ["소개자", "introducer", "소개"]:
                            _map["introducer"] = col
                        elif c in ["그룹분류", "그룹", "group"]:
                            _map["group"] = col
                        elif c in ["주소", "집주소", "address", "거주지"]:
                            _map["address"] = col
                        elif c in ["특이사항", "특이사항1", "메모", "memo", "비고"]:
                            _map["memo"] = col
                    if "name" in _map:
                        df = _df
                        col_map = _map
                        found_sheet = sheet
                        break
                except Exception:
                    continue
            if df is not None:
                break

        if df is None or "name" not in col_map:
            # 시트 목록과 각 시트의 첫 행 샘플을 에러에 포함
            try:
                sheet_info = {}
                for sheet in sheet_names[:5]:
                    _df_raw = pd.read_excel(io.BytesIO(contents), sheet_name=sheet,
                                            header=None, engine="openpyxl")
                    for i in range(min(10, len(_df_raw))):
                        vals = [str(v).strip() for v in _df_raw.iloc[i].tolist()
                                if str(v).strip() not in ["nan", "", "None", "NaT"]]
                        if vals:
                            sheet_info[f"{sheet}/row{i}"] = vals[:8]
                raise HTTPException(status_code=422,
                    detail=f"'이름' 컬럼을 찾을 수 없습니다. 시트: {sheet_names}, 샘플: {sheet_info}")
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=422, detail="'이름' 또는 '성명' 컬럼을 찾을 수 없습니다.")

        # ── 데이터 파싱 ─────────────────────────────────
        records = []
        skipped = 0
        for _, row in df.iterrows():
            name = str(row.get(col_map["name"], "")).strip()
            if not name or name in ["nan", "None", ""]:
                skipped += 1
                continue

            # 메모 조합 (직업 + 소개자 + 그룹)
            memo_parts = []
            if "job" in col_map:
                v = str(row.get(col_map["job"], "")).strip()
                if v and v != "nan": memo_parts.append(f"직업: {v}")
            if "gender" in col_map:
                v = str(row.get(col_map["gender"], "")).strip()
                if v and v != "nan": memo_parts.append(f"성별: {v}")
            if "introducer" in col_map:
                v = str(row.get(col_map["introducer"], "")).strip()
                if v and v != "nan": memo_parts.append(f"소개자: {v}")
            if "group" in col_map:
                v = str(row.get(col_map["group"], "")).strip()
                if v and v != "nan": memo_parts.append(f"그룹: {v}")

            rec = {
                "name":       name,
                "phone":      normalize_phone(row.get(col_map.get("phone"))) if "phone" in col_map else None,
                "category":   map_category(row.get(col_map.get("category"))) if "category" in col_map else "new",
                "status":     "active",
                "birth_date": parse_birth(row.get(col_map.get("birth"))) if "birth" in col_map else None,
                "address":    str(row.get(col_map["address"], "")).strip() if "address" in col_map else None,
                "memo":       " | ".join(memo_parts) if memo_parts else None,
            }
            records.append(rec)

        return ApiResponse(
            success=True,
            data={
                "total":    len(records),
                "skipped":  skipped,
                "columns_found": list(col_map.keys()),
                "preview":  records[:10],   # 미리보기 10건
                "all":      records,        # 전체 (임포트용)
            },
            message=f"총 {len(records)}건 파싱 완료 (빈 행 {skipped}건 제외)"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 파싱 오류: {str(e)}")


@router.post("/excel/confirm")
async def confirm_import(file: UploadFile = File(...)):
    """엑셀 파일 → Supabase 일괄 저장"""
    if not file.filename.endswith((".xlsx", ".xls", ".xlsm")):
        raise HTTPException(status_code=400, detail="Excel 파일만 업로드 가능합니다.")
    try:
        contents = await file.read()

        import openpyxl as _openpyxl
        _wb = _openpyxl.load_workbook(io.BytesIO(contents), read_only=True, data_only=True)
        sheet_names = _wb.sheetnames
        _wb.close()

        df = None
        col_map = {}
        for sheet in sheet_names:
            for header_row in range(20):
                try:
                    _df = pd.read_excel(io.BytesIO(contents), sheet_name=sheet,
                                        header=header_row, engine="openpyxl")
                    _df.columns = [str(c).strip() for c in _df.columns]
                    _map = {}
                    for col in _df.columns:
                        c = col.strip()
                        if c in ["이름", "성명", "고객이름", "name", "고객명"]:         _map["name"] = col
                        elif c in ["휴대폰", "전화", "연락처", "핸드폰", "휴대전화", "phone", "전화번호", "연락처(휴대)"]: _map["phone"] = col
                        elif c in ["고객등급", "등급", "고객구분", "category", "구분"]: _map["category"] = col
                        elif c in ["주민번호앞", "주민앞", "생년월일", "birth", "주민번호", "생년월일(주민앞)"]: _map["birth"] = col
                        elif c in ["직업", "job"]:                                       _map["job"] = col
                        elif c in ["성별", "gender"]:                                    _map["gender"] = col
                        elif c in ["소개자", "introducer", "소개"]:                      _map["introducer"] = col
                        elif c in ["그룹분류", "그룹", "group"]:                         _map["group"] = col
                        elif c in ["주소", "집주소", "address", "거주지"]:               _map["address"] = col
                        elif c in ["특이사항", "특이사항1", "메모", "memo", "비고"]:     _map["memo"] = col
                    if "name" in _map:
                        df = _df
                        col_map = _map
                        break
                except Exception:
                    continue
            if df is not None:
                break

        if df is None or "name" not in col_map:
            raise HTTPException(status_code=422, detail="'이름' 컬럼을 찾을 수 없습니다.")

        records = []
        skipped = 0
        for _, row in df.iterrows():
            name = str(row.get(col_map["name"], "")).strip()
            if not name or name in ["nan", "None", ""]:
                skipped += 1
                continue

            memo_parts = []
            for key, label in [("job","직업"),("gender","성별"),("introducer","소개자"),("group","그룹")]:
                if key in col_map:
                    v = str(row.get(col_map[key], "")).strip()
                    if v and v != "nan": memo_parts.append(f"{label}: {v}")

            rec = {
                "name":       name,
                "phone":      normalize_phone(row.get(col_map.get("phone"))) if "phone" in col_map else None,
                "category":   map_category(row.get(col_map.get("category"))) if "category" in col_map else "new",
                "status":     "active",
                "birth_date": parse_birth(row.get(col_map.get("birth"))) if "birth" in col_map else None,
                "address":    str(row.get(col_map.get("address",""), "")).strip() or None if "address" in col_map else None,
                "memo":       " | ".join(memo_parts) or None,
            }
            # None 값 제거
            rec = {k: v for k, v in rec.items() if v is not None}
            records.append(rec)

        if not records:
            raise HTTPException(status_code=422, detail="임포트할 유효한 데이터가 없습니다.")

        # Supabase bulk insert (100건씩 청크)
        inserted = 0
        errors = []
        chunk_size = 100
        for i in range(0, len(records), chunk_size):
            chunk = records[i:i+chunk_size]
            try:
                result = supabase.table("customers").insert(chunk).execute()
                inserted += len(result.data)
            except Exception as e:
                errors.append(f"청크 {i//chunk_size+1} 오류: {str(e)[:100]}")

        return ApiResponse(
            success=True,
            data={"inserted": inserted, "skipped": skipped, "errors": errors},
            message=f"{inserted}건 임포트 완료" + (f" ({len(errors)}건 오류)" if errors else "")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"임포트 오류: {str(e)}")
