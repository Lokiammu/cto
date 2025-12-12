from fastapi import FastAPI
from contextlib import asynccontextmanager
from backend.auth.router import router as auth_router
from backend.db.database import db
from backend.config import config

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    config.validate()
    db.connect()
    yield
    # Shutdown
    db.close()

app = FastAPI(title="AI Sales Chatbot API", lifespan=lifespan)

app.include_router(auth_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to AI Sales Chatbot API"}
