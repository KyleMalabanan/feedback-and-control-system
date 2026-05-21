"""
AI-Based Smart Speed Monitoring System
Python AI Agent — connects to Arduino via Serial and LM Studio via local API

Requirements (install with):
    pip install pyserial openai rich

LM Studio must be running with:
    - A model loaded (e.g. llama-3, mistral, phi-3, etc.)
    - Local server enabled at http://localhost:1234
"""

import serial
import serial.tools.list_ports
import time
import json
import threading
from datetime import datetime
from openai import OpenAI          # LM Studio uses OpenAI-compatible API
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# ─────────────────────────────────────────────
#  CONFIG — edit these as needed
# ─────────────────────────────────────────────
SERIAL_PORT   = "COM3"          # ← change to your Arduino's COM port
BAUD_RATE     = 9600
LM_STUDIO_URL = "http://localhost:1234/v1"
LM_MODEL      = "local-model"   # LM Studio uses this placeholder name

# Speed thresholds (must match Arduino values)
SPEED_WARN   = 2.00   # m/s
SPEED_DANGER = 3.00   # m/s

# How many readings to include in AI context
HISTORY_SIZE = 10

# ─────────────────────────────────────────────
#  GLOBALS
# ─────────────────────────────────────────────
console       = Console()
speed_history = []          # list of dicts: {time, speed, status}
alarm_active  = False
lock          = threading.Lock()


# ─────────────────────────────────────────────
#  LM STUDIO CLIENT
# ─────────────────────────────────────────────
lm_client = OpenAI(
    base_url=LM_STUDIO_URL,
    api_key="lm-studio"        # LM Studio doesn't need a real key
)


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def find_arduino_port() -> str | None:
    """Auto-detect Arduino serial port."""
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if "Arduino" in p.description or "CH340" in p.description or "USB Serial" in p.description:
            return p.device
    return None


def parse_serial_line(line: str) -> dict | None:
    """
    Parse Arduino output format:
        TIME=12345|SPEED=1.234|STATUS=SAFE
    Returns dict or None on parse failure.
    """
    try:
        parts = dict(item.split("=") for item in line.strip().split("|"))
        return {
            "time":   int(parts["TIME"]),
            "speed":  float(parts["SPEED"]),
            "status": parts["STATUS"],
            "ts":     datetime.now().strftime("%H:%M:%S"),
        }
    except Exception:
        return None


def build_ai_prompt(reading: dict, history: list) -> str:
    """Build the prompt sent to the LM Studio model."""
    history_text = "\n".join(
        f"  [{h['ts']}] Speed={h['speed']:.3f} m/s  Status={h['status']}"
        for h in history[-HISTORY_SIZE:]
    ) or "  (no previous readings)"

    return f"""You are an AI safety agent for a smart speed monitoring system.
Your job is to analyse speed readings from ultrasonic sensors and decide whether to trigger an alarm.

=== CURRENT READING ===
Timestamp : {reading['ts']}
Speed     : {reading['speed']:.3f} m/s
Status    : {reading['status']}

=== RECENT HISTORY (last {HISTORY_SIZE} readings) ===
{history_text}

=== THRESHOLDS ===
SAFE    : speed < {SPEED_WARN} m/s
WARNING : {SPEED_WARN} <= speed < {SPEED_DANGER} m/s
DANGER  : speed >= {SPEED_DANGER} m/s

=== YOUR TASK ===
1. Analyse the current reading and the trend in recent history.
2. Decide ONE of these actions:
   - TRIGGER_ALARM  → immediately alarming situation
   - IGNORE         → safe / false positive
   - MONITOR        → concerning but watch for now
3. Give a brief 1-2 sentence reason.

Respond ONLY in this exact JSON format (no markdown, no extra text):
{{"action": "TRIGGER_ALARM|IGNORE|MONITOR", "reason": "your reason here"}}
"""


# ─────────────────────────────────────────────
#  AI DECISION
# ─────────────────────────────────────────────
def ask_ai(reading: dict, history: list) -> dict:
    """Call LM Studio and return parsed JSON response."""
    prompt = build_ai_prompt(reading, history)
    try:
        response = lm_client.chat.completions.create(
            model=LM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200,
        )
        raw = response.choices[0].message.content.strip()

        # Strip markdown fences if model adds them
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)

    except json.JSONDecodeError as e:
        console.print(f"[yellow]AI returned invalid JSON: {e}[/yellow]")
        return {"action": "MONITOR", "reason": "AI response parse error — defaulting to MONITOR"}
    except Exception as e:
        console.print(f"[red]LM Studio error: {e}[/red]")
        return {"action": "MONITOR", "reason": f"LM Studio unreachable: {e}"}


# ─────────────────────────────────────────────
#  DISPLAY
# ─────────────────────────────────────────────
def print_dashboard(reading: dict, ai_result: dict):
    status_color = {"SAFE": "green", "WARNING": "yellow", "DANGER": "red"}.get(reading["status"], "white")
    action_color = {"TRIGGER_ALARM": "red", "IGNORE": "green", "MONITOR": "yellow"}.get(ai_result["action"], "white")

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Key",   style="bold cyan",  width=12)
    table.add_column("Value", style="white")

    table.add_row("Time",   reading["ts"])
    table.add_row("Speed",  f"{reading['speed']:.3f} m/s")
    table.add_row("Status", f"[{status_color}]{reading['status']}[/{status_color}]")
    table.add_row("AI Act", f"[{action_color}]{ai_result['action']}[/{action_color}]")
    table.add_row("Reason", ai_result["reason"])

    console.print(Panel(table, title="[bold]Speed Monitor[/bold]", border_style="blue"))


# ─────────────────────────────────────────────
#  MAIN LOOP
# ─────────────────────────────────────────────
def main():
    global alarm_active

    # ── Serial port detection ──
    port = SERIAL_PORT
    if port == "AUTO":
        port = find_arduino_port()
        if not port:
            console.print("[red]Could not auto-detect Arduino. Set SERIAL_PORT manually.[/red]")
            return

    console.print(Panel(
        f"Connecting to Arduino on [cyan]{port}[/cyan] @ {BAUD_RATE} baud\n"
        f"LM Studio  → [cyan]{LM_STUDIO_URL}[/cyan]\n"
        "Press Ctrl+C to quit.",
        title="[bold green]AI Speed Monitor Starting[/bold green]"
    ))

    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=2)
        time.sleep(2)   # wait for Arduino to reset after serial connect
        console.print("[green]✓ Arduino connected[/green]")
    except serial.SerialException as e:
        console.print(f"[red]Serial error: {e}[/red]")
        return

    # Send PING to verify Arduino is alive
    ser.write(b"PING\n")
    time.sleep(0.5)
    pong = ser.readline().decode(errors="ignore").strip()
    if pong == "PONG":
        console.print("[green]✓ Arduino heartbeat OK[/green]")
    else:
        console.print("[yellow]⚠ No PONG from Arduino (continuing anyway)[/yellow]")

    # ── Main read loop ──
    while True:
        try:
            raw = ser.readline().decode(errors="ignore").strip()
            if not raw or raw == "PONG":
                continue

            reading = parse_serial_line(raw)
            if reading is None:
                console.print(f"[dim]Unrecognised line: {raw}[/dim]")
                continue

            # Skip error readings
            if reading["status"] == "ERROR":
                console.print("[yellow]Sensor measurement error — skipping AI call[/yellow]")
                continue

            with lock:
                speed_history.append(reading)
                if len(speed_history) > HISTORY_SIZE * 2:
                    speed_history.pop(0)

            # ── Ask the AI ──
            console.print(f"\n[dim]Querying LM Studio for reading: {reading}[/dim]")
            ai_result = ask_ai(reading, speed_history)

            print_dashboard(reading, ai_result)

            # ── Send command back to Arduino ──
            action = ai_result.get("action", "MONITOR")

            if action == "TRIGGER_ALARM" and not alarm_active:
                ser.write(b"TRIGGER_ALARM\n")
                alarm_active = True
                console.print("[bold red]→ ALARM sent to Arduino[/bold red]")

            elif action in ("IGNORE", "MONITOR") and alarm_active:
                ser.write(b"CLEAR_ALARM\n")
                alarm_active = False
                console.print("[bold green]→ CLEAR_ALARM sent to Arduino[/bold green]")

            elif action == "IGNORE":
                ser.write(b"IGNORE\n")

        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down...[/yellow]")
            if alarm_active:
                ser.write(b"CLEAR_ALARM\n")
            ser.close()
            break
        except serial.SerialException as e:
            console.print(f"[red]Serial disconnected: {e}[/red]")
            break


if __name__ == "__main__":
    main()