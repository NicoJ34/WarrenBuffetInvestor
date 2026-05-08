from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api._lib.config import get_settings
from api.auth.router import router as auth_router
from api.profile.router import router as profile_router

app = FastAPI(title="WarrenBuffetInvestor API", version="1.0.0")

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PREFIX = "/api/v1"

app.include_router(auth_router, prefix=f"{PREFIX}/auth", tags=["auth"])
app.include_router(profile_router, prefix=f"{PREFIX}/profile", tags=["profile"])

# Routers ajoutés au fur et à mesure des phases :
# from api.portfolio.router import router as portfolio_router
# from api.analysis.router import router as analysis_router
# from api.allocation.router import router as allocation_router
# from api.cron.router import router as cron_router
# app.include_router(portfolio_router, prefix=f"{PREFIX}/portfolio", tags=["portfolio"])
# app.include_router(analysis_router, prefix=f"{PREFIX}/analysis", tags=["analysis"])
# app.include_router(allocation_router, prefix=f"{PREFIX}/allocation", tags=["allocation"])
# app.include_router(cron_router, prefix=f"{PREFIX}/cron", tags=["cron"])


@app.get(f"{PREFIX}/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
