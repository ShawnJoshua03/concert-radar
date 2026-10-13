import os
from urllib.parse import urlsplit

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from artists import router as artists_router
from auth import router as auth_router
from concerts import router as concerts_router
from users import router as users_router

app = FastAPI(title="Concert Radar API")


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


_cors_origin = _origin(os.getenv("FRONTEND_URL", "http://127.0.0.1:3000/dashboard.html"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=[_cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth")
app.include_router(artists_router, prefix="/artists")
app.include_router(concerts_router, prefix="/concerts")
app.include_router(users_router, prefix="/user")


@app.get("/")
def root():
    return {"status": "ok", "app": "Concert Radar"}
