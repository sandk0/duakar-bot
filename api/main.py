from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import logging
from database.connection import init_db, close_db
from api.routers import users, subscriptions, payments, stats, settings, admin
from api.dependencies import get_current_admin_user
from bot.config import settings as app_settings

logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting FastAPI application...")
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down FastAPI application...")
    await close_db()


# Create FastAPI app
app = FastAPI(
    title="VPN Bot API",
    description="API for VPN Telegram Bot management",
    version="1.0.0",
    docs_url="/docs" if app_settings.debug else None,
    redoc_url="/redoc" if app_settings.debug else None,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if app_settings.debug else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "testing_mode": app_settings.testing_mode
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "VPN Bot API", "docs": "/docs"}


# Include routers
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(subscriptions.router, prefix="/api/v1/subscriptions", tags=["subscriptions"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(stats.router, prefix="/api/v1/stats", tags=["statistics"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])

# Admin only endpoint to toggle testing mode
@app.post("/api/v1/admin/toggle-testing-mode")
async def toggle_testing_mode(
    current_admin = Depends(get_current_admin_user)
):
    """Toggle testing mode for payments"""
    try:
        from database.connection import async_session_maker
        from database.models import SystemSetting
        from sqlalchemy import select
        import json
        
        async with async_session_maker() as session:
            # Get or create testing mode setting
            result = await session.execute(
                select(SystemSetting).where(SystemSetting.key == "testing_mode")
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                current_mode = json.loads(setting.value).get("enabled", False)
                new_mode = not current_mode
                setting.value = json.dumps({"enabled": new_mode})
            else:
                new_mode = True
                setting = SystemSetting(
                    key="testing_mode",
                    value=json.dumps({"enabled": new_mode}),
                    description="Enable/disable testing mode for payments"
                )
                session.add(setting)
            
            await session.commit()
            
            # Update runtime setting
            app_settings.testing_mode = new_mode
            
            return {
                "success": True,
                "testing_mode": new_mode,
                "message": f"Testing mode {'enabled' if new_mode else 'disabled'}"
            }
    
    except Exception as e:
        logger.error(f"Error toggling testing mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to toggle testing mode"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=app_settings.debug
    )