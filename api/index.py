from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api._lib.config import get_settings

app = FastAPI(title="WarrenBuffetInvestor API", version="1.0.0")

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers — importés ici au fur et à mesure des phases
# from api.auth.router import router as auth_router
# from api.portfolio.router import router as portfolio_router
# from api.analysis.router import router as analysis_router
# from api.allocation.router import router as allocation_router
# from api.cron.router import router as cron_router
# app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
# app.include_router(portfolio_router, prefix="/api/portfolio", tags=["portfolio"])
# app.include_router(analysis_router, prefix="/api/analysis", tags=["analysis"])
# app.include_router(allocation_router, prefix="/api/allocation", tags=["allocation"])
# app.include_router(cron_router, prefix="/api/cron", tags=["cron"])


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
