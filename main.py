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

# CORS — Netlify 프론트 + 로컬 개발 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://super-crm-app.netlify.app",
        "http://localhost:3200",
        "http://localhost:5173",
    ],
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
