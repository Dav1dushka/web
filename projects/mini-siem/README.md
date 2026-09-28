# Mini SIEM

A small security monitoring project I made to practice backend development and basic log detection.

It stores login events in SQLite and creates an alert when one IP has too many failed login attempts.

### Endpoints

```
GET  /events
GET  /alerts
GET  /summary
POST /ingest
```

### Run

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Then open:

```
http://127.0.0.1:8000/docs
```

### Import sample logs

```bash
python import_logs.py
```

### Built with

Python · FastAPI · SQLite

It's a learning project. The next steps are more event types, better detection rules and a small dashboard.
