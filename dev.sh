#!/usr/bin/env bash
# dev.sh — single entry point for all project tasks
#
# Usage:
#   ./dev.sh <command>
#
# Commands:
#   install          Install all three services
#   install:be       Install backend only
#   install:fe       Install frontend only
#   install:admin    Install admin only
#
#   start            Start all three services (Ctrl+C to stop all)
#   start:be         Start backend only  (http://localhost:8000)
#   start:fe         Start frontend only (http://localhost:5174)
#   start:admin      Start admin only    (http://localhost:5173)

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

# ── helpers ──────────────────────────────────────────────────────────────────

install_backend() {
  echo "==> [backend] Setting up virtual environment..."
  cd "$ROOT/backend"

  if [ ! -d .venv ]; then
    python3 -m venv .venv
    echo "    Created .venv"
  fi

  echo "==> [backend] Installing dependencies into .venv..."
  .venv/bin/python -m pip install --upgrade pip setuptools wheel
  .venv/bin/python -m pip install -e ".[dev]"

  if [ ! -f .env ]; then
    cp .env.example .env
    echo "    ⚠  Created backend/.env — set SECRET_KEY before running."
  fi

  echo "==> [backend] Running database migrations..."
  .venv/bin/python -m alembic upgrade head

  echo "✓ Backend ready."
}

install_frontend() {
  echo "==> [frontend] Installing npm dependencies..."
  cd "$ROOT/frontend"
  npm install
  if [ ! -f .env ]; then cp .env.example .env; fi
  echo "✓ Frontend ready."
}

install_admin() {
  echo "==> [admin] Installing npm dependencies..."
  cd "$ROOT/admin"
  npm install
  if [ ! -f .env ]; then cp .env.example .env; fi
  echo "✓ Admin ready."
}

# ── commands ─────────────────────────────────────────────────────────────────

case "${1:-}" in

  install)
    install_backend
    echo ""
    install_frontend
    echo ""
    install_admin
    echo ""
    echo "========================================"
    echo " All services installed."
    echo " Edit backend/.env and set SECRET_KEY,"
    echo " then run:  ./dev.sh start"
    echo "========================================"
    ;;

  install:be)    install_backend ;;
  install:fe)    install_frontend ;;
  install:admin) install_admin ;;

  start:be)
    echo "==> Starting backend on http://localhost:8000  (docs: http://localhost:8000/docs)"
    cd "$ROOT/backend"
    .venv/bin/python -m uvicorn app.main:app --reload --port 8000
    ;;

  start:fe)
    echo "==> Starting frontend on http://localhost:5174"
    cd "$ROOT/frontend"
    npm run dev
    ;;

  start:admin)
    echo "==> Starting admin on http://localhost:5173"
    cd "$ROOT/admin"
    npm run dev
    ;;

  start)
    echo "========================================"
    echo " Starting all services"
    echo "   Backend  → http://localhost:8000"
    echo "   Docs     → http://localhost:8000/docs"
    echo "   Frontend → http://localhost:5174"
    echo "   Admin    → http://localhost:5173"
    echo " Press Ctrl+C to stop all."
    echo "========================================"
    trap 'echo ""; echo "Stopping all..."; kill 0' INT TERM
    (cd "$ROOT/backend"  && .venv/bin/python -m uvicorn app.main:app --reload --port 8000) &
    (cd "$ROOT/frontend" && npm run dev) &
    (cd "$ROOT/admin"    && npm run dev) &
    wait
    ;;

  *)
    echo "Usage: ./dev.sh <command>"
    echo ""
    echo "  install          Install all three services"
    echo "  install:be       Install backend only"
    echo "  install:fe       Install frontend only"
    echo "  install:admin    Install admin only"
    echo ""
    echo "  start            Start all three services"
    echo "  start:be         Start backend  (http://localhost:8000)"
    echo "  start:fe         Start frontend (http://localhost:5174)"
    echo "  start:admin      Start admin    (http://localhost:5173)"
    exit 1
    ;;
esac
