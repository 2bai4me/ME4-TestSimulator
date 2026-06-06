"""
ME4 TestSimulator — RPA Service
Robotic Process Automation: Macro Recorder + Playback Engine

Port: 5521
"""

import json
import os
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

import pyautogui as pg
from pynput import mouse, keyboard

# ─── Configuration ──────────────────────────────────────────────
SERVICE_NAME = "me4-testsimulator"
VERSION = "0.1.0"
PORT = 5521
WORKFLOW_DIR = Path(__file__).parent / "workflows"
WORKFLOW_DIR.mkdir(exist_ok=True)

# ─── Macro Recorder ─────────────────────────────────────────────
class MacroRecorder:
    """Records mouse and keyboard events as a macro."""
    
    def __init__(self):
        self.events = []
        self.recording = False
        self.start_time = 0
        self._mouse_listener = None
        self._keyboard_listener = None
    
    def start(self, capture_mouse_move: bool = False):
        """Start recording."""
        self.events = []
        self.recording = True
        self.start_time = time.time()
        
        def on_click(x, y, button, pressed):
            if self.recording:
                self.events.append({
                    "type": "mouse_click",
                    "x": x, "y": y,
                    "button": str(button),
                    "pressed": pressed,
                    "time": time.time() - self.start_time
                })
        
        def on_move(x, y):
            if self.recording and capture_mouse_move:
                self.events.append({
                    "type": "mouse_move",
                    "x": x, "y": y,
                    "time": time.time() - self.start_time
                })
        
        def on_scroll(x, y, dx, dy):
            if self.recording:
                self.events.append({
                    "type": "mouse_scroll",
                    "x": x, "y": y, "dy": dy,
                    "time": time.time() - self.start_time
                })
        
        def on_press(key):
            if self.recording:
                try:
                    k = key.char
                except AttributeError:
                    k = str(key)
                self.events.append({
                    "type": "key_press",
                    "key": k,
                    "time": time.time() - self.start_time
                })
        
        self._mouse_listener = mouse.Listener(on_click=on_click, on_move=on_move, on_scroll=on_scroll)
        self._keyboard_listener = keyboard.Listener(on_press=on_press)
        self._mouse_listener.start()
        self._keyboard_listener.start()
        print(f"[MacroRecorder] Recording started (capture_mouse_move={capture_mouse_move})")
    
    def stop(self) -> dict:
        """Stop recording and return the macro data."""
        self.recording = False
        if self._mouse_listener:
            self._mouse_listener.stop()
        if self._keyboard_listener:
            self._keyboard_listener.stop()
        duration = time.time() - self.start_time
        print(f"[MacroRecorder] Recording stopped: {len(self.events)} events in {duration:.1f}s")
        return {
            "name": f"macro_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "created": datetime.now().isoformat(),
            "duration": round(duration, 2),
            "event_count": len(self.events),
            "events": self.events
        }


# ─── Macro Player ───────────────────────────────────────────────
class MacroPlayer:
    """Plays back recorded macros using PyAutoGUI."""
    
    def __init__(self):
        self.playing = False
        pg.FAILSAFE = True
        pg.PAUSE = 0.01
    
    def play(self, macro: dict, speed: float = 1.0) -> dict:
        """Play back a macro at given speed multiplier."""
        self.playing = True
        events = macro.get("events", [])
        last_time = 0
        count = 0
        
        for event in events:
            if not self.playing:
                break
            
            # Wait for correct timing
            delay = (event["time"] - last_time) / speed
            if delay > 0:
                time.sleep(min(delay, 0.5))  # Cap at 500ms
            last_time = event["time"]
            
            try:
                if event["type"] == "mouse_click":
                    if event.get("pressed", True):
                        pg.click(event["x"], event["y"], button=event.get("button", "left").replace("Button.", ""))
                
                elif event["type"] == "mouse_move":
                    pg.moveTo(event["x"], event["y"], duration=0.01)
                
                elif event["type"] == "mouse_scroll":
                    pg.scroll(event.get("dy", 0))
                
                elif event["type"] == "key_press":
                    k = event["key"]
                    if k.startswith("Key."):
                        k = k.replace("Key.", "").lower()
                        pg.press(k)
                    else:
                        pg.typewrite(k, interval=0.02)
                
                count += 1
            except Exception as e:
                print(f"[MacroPlayer] Error on event {count}: {e}")
        
        self.playing = False
        return {"played": count, "total": len(events)}
    
    def stop(self):
        """Stop playback."""
        self.playing = False


# ─── Workflow Manager ───────────────────────────────────────────
class WorkflowManager:
    """Manages saved macros and workflows."""
    
    def save(self, macro: dict) -> str:
        """Save a macro to disk."""
        name = macro["name"]
        path = WORKFLOW_DIR / f"{name}.json"
        with open(path, "w") as f:
            json.dump(macro, f, indent=2)
        return str(path)
    
    def load(self, name: str) -> Optional[dict]:
        """Load a macro by name."""
        path = WORKFLOW_DIR / f"{name}.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return None
    
    def list_all(self) -> list:
        """List all saved workflows."""
        workflows = []
        for f in sorted(WORKFLOW_DIR.glob("*.json")):
            with open(f) as fp:
                data = json.load(fp)
                workflows.append({
                    "name": f.stem,
                    "created": data.get("created", ""),
                    "duration": data.get("duration", 0),
                    "event_count": data.get("event_count", 0)
                })
        return workflows
    
    def delete(self, name: str) -> bool:
        """Delete a workflow."""
        path = WORKFLOW_DIR / f"{name}.json"
        if path.exists():
            path.unlink()
            return True
        return False


# ─── Global Instances ───────────────────────────────────────────
recorder = MacroRecorder()
player = MacroPlayer()
manager = WorkflowManager()
