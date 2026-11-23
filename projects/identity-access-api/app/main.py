from fastapi import FastAPI
from .routers import admin, auth, users

app = FastAPI(
    title="Identity Access API",
    version="1.0.0",
    description="A portfolio IAM backend demonstrating secure password storage, JWT sessions, refresh rotation, RBAC and audit events.",
)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(admin.router)


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": "identity-access-api"}
