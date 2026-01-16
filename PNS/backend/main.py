import logging
from fastapi import FastAPI, Request
from database import init_db
from requirement import router as requirement_router
from functional import router as functional_router
from technical_committee_review import router as technical_review_router
from tender_drafting import router as tender_router
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from publish_rfp import router as publish_router
from purchase import router as purchase_router
import time

# ==================== LOGGING CONFIGURATION ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info("RFP CREATION PROJECT - APPLICATION STARTUP")
logger.info("=" * 60)

logger.info("Importing modules...")
logger.info("  - FastAPI imported")
logger.info("  - database.init_db imported")
logger.info("  - requirement_router imported")
logger.info("  - functional_router imported")
logger.info("  - technical_review_router imported")
logger.info("  - tender_router imported")
logger.info("  - publish_router imported")
logger.info("  - purchase_router imported")
logger.info("All modules imported successfully")

logger.info("-" * 60)
logger.info("Creating FastAPI application instance...")
app = FastAPI(title="RFP Creation Project")
logger.info("FastAPI application created")
logger.info("  - Title: RFP Creation Project")

logger.info("-" * 60)
logger.info("Configuring CORS middleware...")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("CORS middleware configured:")
logger.info("  - allow_origins: ['*']")
logger.info("  - allow_credentials: True")
logger.info("  - allow_methods: ['*']")
logger.info("  - allow_headers: ['*']")


# ==================== REQUEST LOGGING MIDDLEWARE ====================
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log all incoming HTTP requests and responses"""
    start_time = time.time()
    
    # Log incoming request
    logger.info("-" * 40)
    logger.info("INCOMING REQUEST")
    logger.info(f"  - Method: {request.method}")
    logger.info(f"  - URL: {request.url}")
    logger.info(f"  - Path: {request.url.path}")
    logger.info(f"  - Client: {request.client.host if request.client else 'Unknown'}:{request.client.port if request.client else 'Unknown'}")
    logger.info(f"  - Headers Content-Type: {request.headers.get('content-type', 'N/A')}")
    
    # Process the request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log response
    logger.info("RESPONSE")
    logger.info(f"  - Status Code: {response.status_code}")
    logger.info(f"  - Processing Time: {process_time:.4f} seconds")
    logger.info("-" * 40)
    
    return response


@app.on_event("startup")
def on_startup():
    logger.info("=" * 60)
    logger.info("APPLICATION STARTUP EVENT TRIGGERED")
    logger.info("=" * 60)
    
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialization completed")
    
    logger.info("=" * 60)
    logger.info("APPLICATION STARTUP COMPLETE - READY TO ACCEPT REQUESTS")
    logger.info("=" * 60)


logger.info("-" * 60)
logger.info("Including routers...")

logger.info("Including requirement_router...")
logger.info("  - Prefix: /requirements")
logger.info("  - Tags: ['Requirements']")
app.include_router(requirement_router)
logger.info("requirement_router included successfully")

logger.info("Including functional_router...")
logger.info("  - Prefix: /functional")
logger.info("  - Tags: ['Functional Assessment']")
app.include_router(functional_router)
logger.info("functional_router included successfully")

logger.info("Including technical_review_router...")
logger.info("  - Prefix: /technical-review")
logger.info("  - Tags: ['Technical Committee Review']")
app.include_router(technical_review_router)
logger.info("technical_review_router included successfully")

logger.info("Including tender_router...")
logger.info("  - Prefix: /tender")
logger.info("  - Tags: ['Tender Drafting']")
app.include_router(tender_router)
logger.info("tender_router included successfully")

logger.info("Including publish_router...")
logger.info("  - Prefix: /publish")
logger.info("  - Tags: ['Publish RFP']")
app.include_router(publish_router)
logger.info("publish_router included successfully")

logger.info("Including purchase_router...")
logger.info("  - Prefix: /purchase")
logger.info("  - Tags: ['Purchase Order']")
app.include_router(purchase_router)
logger.info("purchase_router included successfully")

logger.info("-" * 60)
logger.info("All routers included successfully")
logger.info("Total routers: 6")
logger.info("-" * 60)



@app.get("/health")
def root():
    logger.info("=" * 60)
    logger.info("API CALLED: GET /health")
    logger.info("=" * 60)
    logger.info("Health check endpoint called")
    logger.info("Returning status: healthy")
    logger.info("=" * 60)
    return {"message": "healthy"}


logger.info("=" * 60)
logger.info("APPLICATION CONFIGURATION COMPLETE")
logger.info("=" * 60)
logger.info("Registered Endpoints:")
logger.info("  - GET  /health")
logger.info("  - Requirements API: /requirements/*")
logger.info("  - Functional API: /functional/*")
logger.info("  - Technical Review API: /technical-review/*")
logger.info("  - Tender API: /tender/*")
logger.info("  - Publish API: /publish/*")
logger.info("  - Purchase API: /purchase/*")
logger.info("=" * 60)


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("STARTING UVICORN SERVER")
    logger.info("=" * 60)
    logger.info("Server Configuration:")
    logger.info("  - Host: 0.0.0.0")
    logger.info("  - Port: 8003")
    logger.info("  - Reload: True")
    logger.info("  - App: main:app")
    logger.info("=" * 60)
    logger.info("Starting server...")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=True
    )
