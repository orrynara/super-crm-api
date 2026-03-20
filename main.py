from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from routers import customers, activities, codes

app = FastAPI(
    title="SUPER CRM API",
    description="보험설계사 고객 관리 시스템 API",
    version="1.0.0",
)

# CORS — 개발: 모든 origin 허용 / 운영: 프론트 도메인만
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(customers.router)
app.include_router(activities.router)
app.include_router(codes.router)


@app.get("/")
def root():
    return {"message": "SUPER CRM API 정상 작동 중", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
