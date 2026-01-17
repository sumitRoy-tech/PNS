from fastapi import FastAPI
from database import init_db
from requirement import router as requirement_router
from functional import router as functional_router
from technical_committee_review import router as technical_review_router
from tender_drafting import router as tender_router
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from publish_rfp import router as publish_router


app = FastAPI(title="RFP Creation Project")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(requirement_router)
app.include_router(functional_router)
app.include_router(technical_review_router)
app.include_router(tender_router)
app.include_router(publish_router)



@app.get("/health")
def root():
    return {"message": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=True
    )