"""Cross-platform task runner (works on Windows without make).

    python scripts/dev.py setup   # create .venv and install backend + dev deps
    python scripts/dev.py test    # run pytest
    python scripts/dev.py lint    # run ruff
    python scripts/dev.py api     # run the FastAPI backend on 127.0.0.1:8000
    python scripts/dev.py web     # serve the frontend on 127.0.0.1:3000
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV = ROOT / ".venv"
BIN = VENV / ("Scripts" if os.name == "nt" else "bin")
PY = BIN / ("python.exe" if os.name == "nt" else "python")


def run(*cmd: str | Path, cwd: Path = ROOT) -> None:
    print("$", " ".join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], cwd=cwd, check=True)


def python() -> Path | str:
    # Use the project venv when it exists; fall back to the current interpreter (CI)
    return PY if PY.exists() else sys.executable


def setup() -> None:
    if not PY.exists():
        run(sys.executable, "-m", "venv", VENV)
    run(PY, "-m", "pip", "install", "-q", "-r", ROOT / "backend" / "requirements-dev.txt")
    env = ROOT / "backend" / ".env"
    if not env.exists():
        env.write_text((ROOT / "backend" / ".env.example").read_text())
        print("Created backend/.env from .env.example: fill in your keys before running the API.")


def test() -> None:
    run(python(), "-m", "pytest", "-q")


def lint() -> None:
    run(python(), "-m", "ruff", "check", ".")


def api() -> None:
    run(python(), "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000", "--reload",
        cwd=ROOT / "backend")


def web() -> None:
    print("Open http://127.0.0.1:3000 (add ?demo to run without a backend)")
    run(sys.executable, "-m", "http.server", "3000", "--bind", "127.0.0.1", "--directory", ROOT / "frontend")


TASKS = {"setup": setup, "test": test, "lint": lint, "api": api, "web": web}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in TASKS:
        sys.exit(__doc__)
    TASKS[sys.argv[1]]()
