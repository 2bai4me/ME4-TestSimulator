"""
ME4 TestSimulator — REST API Server
RPA Service auf Port 5521
"""

import json
import threading
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from .core import recorder, player, manager, SERVICE_NAME, VERSION

app = FastAPI(title=SERVICE_NAME, version=VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ─── Models ─────────────────────────────────────────────────────
class RecordStartRequest(BaseModel):
    capture_mouse_move: bool = False

class PlayRequest(BaseModel):
    speed: float = 1.0

class WorkflowStep(BaseModel):
    type: str  # "click", "type", "wait", "click_text", "navigate"
    selector: str = ""
    text: str = ""
    url: str = ""
    wait: float = 0

class WorkflowRunRequest(BaseModel):
    name: str
    steps: list[WorkflowStep] = []

class AutorunRequest(BaseModel):
    url: str = "http://localhost:5173"
    channel: str = "technews"
    youtube: str = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    headless: bool = False


# ─── Health ──────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": VERSION,
        "workflows": len(manager.list_all()),
        "recording": recorder.recording,
        "playing": player.playing
    }


# ─── Recording ───────────────────────────────────────────────────
@app.post("/record/start")
def start_recording(req: RecordStartRequest = RecordStartRequest()):
    if recorder.recording:
        raise HTTPException(400, "Already recording")
    threading.Thread(target=recorder.start, args=(req.capture_mouse_move,), daemon=True).start()
    return {"status": "recording"}


@app.post("/record/stop")
def stop_recording():
    if not recorder.recording:
        raise HTTPException(400, "Not recording")
    macro = recorder.stop()
    path = manager.save(macro)
    return {"status": "saved", "name": macro["name"], "events": macro["event_count"], "path": path}


@app.get("/record/status")
def record_status():
    return {"recording": recorder.recording, "events": len(recorder.events)}


# ─── Playback ────────────────────────────────────────────────────
@app.post("/play/{name}")
def play_macro(name: str, req: PlayRequest = PlayRequest()):
    macro = manager.load(name)
    if not macro:
        raise HTTPException(404, f"Workflow '{name}' not found")
    if player.playing:
        raise HTTPException(400, "Already playing")
    
    def _play():
        result = player.play(macro, req.speed)
        print(f"[Playback] Done: {result}")
    
    threading.Thread(target=_play, daemon=True).start()
    return {"status": "playing", "name": name, "events": macro.get("event_count", 0)}


@app.post("/play/{name}/stop")
def stop_playback(name: str):
    player.stop()
    return {"status": "stopped"}


# ─── Workflows ───────────────────────────────────────────────────
@app.get("/workflows")
def list_workflows():
    return {"workflows": manager.list_all()}


@app.get("/workflows/{name}")
def get_workflow(name: str):
    macro = manager.load(name)
    if not macro:
        raise HTTPException(404, f"Workflow '{name}' not found")
    return macro


@app.delete("/workflows/{name}")
def delete_workflow(name: str):
    if manager.delete(name):
        return {"status": "deleted", "name": name}
    raise HTTPException(404, f"Workflow '{name}' not found")


# ─── Autorun (SMproducer) ────────────────────────────────────────
@app.post("/autorun/smproducer")
def autorun_smproducer(req: AutorunRequest):
    """Run complete SMproducer test workflow."""
    from .autorun import run_smproducer_test
    
    def _run():
        result = run_smproducer_test(
            youtube_url=req.youtube,
            headless=req.headless
        )
        print(f"[Autorun] Result: {result}")
    
    threading.Thread(target=_run, daemon=True).start()
    return {"status": "running", "message": "SMproducer Test-Workflow gestartet"}


# ─── Main ────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print(f"[{SERVICE_NAME}] Starting on port 5521...")
    uvicorn.run(app, host="127.0.0.1", port=5521, log_level="info")
