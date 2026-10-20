# FastAPI startup with json-logging

`json_logging.init_fastapi()` can only run once per process. This example puts the app and its initialisation in one
module, `app/main.py`, and shows how to start it with uvicorn without importing that module twice.

## Working patterns

Run these from the `example/fastapi_startup` directory.

1. **Import string, started by uvicorn (recommended):**

   ```bash
   python -m uvicorn app.main:app --port 8000
   ```

   uvicorn imports `app.main` once, so the module body runs once.

2. **Pass the app object** from a separate launcher, [`run.py`](run.py), that does not contain the app:

   ```python
   import uvicorn

   from app.main import app

   if __name__ == "__main__":
       uvicorn.run(app, host="127.0.0.1", port=8000)
   ```

   ```bash
   python run.py
   ```

   uvicorn receives the app object, not an import string, so it does not import `app.main` again.

## Pattern that fails

```python
# app/main.py, executed directly
...
if __name__ == "__main__":
    uvicorn.run("app.main:app")   # imports app.main again, so init_fastapi() runs twice
```

This raises `RuntimeError: Can not call init more than once` (issue #106). The module runs once as `__main__` and
again as `app.main`. Either use one of the working patterns above, or keep the launch code out of the module that
creates the app.

## Verify

```bash
python -m pytest tests/test_fastapi_startup.py -q
```
