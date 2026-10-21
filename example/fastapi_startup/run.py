"""Launcher that passes the app object to uvicorn. The app and json-logging are set up in app/main.py, imported once."""
import uvicorn

from app.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
