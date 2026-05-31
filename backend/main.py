import os

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth import router as auth_router
from artists import router as artists_router
from concerts import router as concerts_router
from users import router as users_router

app = FastAPI(title="Concert Radar API")

_frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
_cors_origin = _frontend_url.split("/dashboard")[0]  # strip path, keep origin

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
