from fastapi import FastAPI
import psutil

app = FastAPI(title="System Monitor")


@app.get("/metrics")
def get_metrics():
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    return {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "memory_percent": memory.percent,
        "memory_available_mb": round(memory.available / 1024 / 1024, 1),
        "disk_percent": disk.percent,
    }


@app.get("/processes")
def get_processes():
    processes = []

    for process in psutil.process_iter(["pid", "name", "memory_percent"]):
        try:
            info = process.info
            processes.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return sorted(
        processes,
        key=lambda item: item.get("memory_percent") or 0,
        reverse=True,
    )[:20]
