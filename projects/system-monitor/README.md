# System Monitor

A small backend service that exposes basic system metrics through an API.

### Endpoints

```
GET /metrics
GET /processes
```

### Built with

Python, FastAPI and psutil.

The idea is to collect real system information and later connect it to a small web dashboard.

Run it with:

```bash
pip install -r requirements.txt
uvicorn monitor:app --reload
```

Then open:

```
http://127.0.0.1:8000/docs
```
