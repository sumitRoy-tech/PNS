from fastapi import FastAPI
from database import init_db
from requirement import router as requirement_router

app = FastAPI(title="RFP Creation Project")
#initialize DB
init_db()

app.include_router(requirement_router)


@app.get("/")
def root():
    return {"message": "RFP Creation Backend Running"}

