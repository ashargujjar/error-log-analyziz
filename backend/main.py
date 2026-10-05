import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent / ".env")


from db.db import mongo_client
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.auth_routes import router as auth_router


app = FastAPI(title="Error Log Analyzer API")

frontend_url = os.getenv("FRONTEND_URL", "http://127.0.0.1:5173")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.on_event("startup")
async def connect_to_mongodb() -> None:
    await mongo_client.admin.command("ping")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Error Log Analyzer API is running"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
