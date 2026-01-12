from fastapi import FastAPI
from database import init_db
from requirement import router
import uvicorn

app = FastAPI(title="RFP Creation Project")


# ✅ Run DB initialization ONLY once on app startup
@app.on_event("startup")
def on_startup():
    init_db()


# ✅ Register routers
app.include_router(router)


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
