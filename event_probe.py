"""Captura de eventos do kernel ACP com timestamps durante prompt longo (grafo).

Prova: o kernel STREAMS eventos durante o turno (que o cliente atual bufferiza
e só devolve no final) ou só emite a resposta completa? Se streamar, dá pra
expor ao usuário sem tmux; se não, tmux só mostraria chrome do TUI do CLI.

Uso: venv/bin/python scripts/event_probe.py [modelo]
"""
import json
import queue
import subprocess
import sys
import time

KERNEL = "/Users/gemanuel/Library/Application Support/Zed/external_agents/registry/antigravity-acp/v_1.0.0_92521fc3cbd964bd_5cbd321ab34fa538/agy_acp_server.par"
CWD = "/Users/gemanuel"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "gemini-3.8-flash-low"
PROMPT = ("Use o MCP codegraph-uniplus para mapear o fluxo de reconciliation "
          "do backend de /Users/gemanuel/dev/sub/backend/uniplus-api e liste "
          "as funcoes principais. Nao edite nada, so responda com o mapa.")

q = queue.Queue()
proc = subprocess.Popen(
    [KERNEL],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    cwd=CWD, bufsize=0,
)
stop = [False]

def pump():
    while not stop[0]:
        line = proc.stdout.readline()
        if not line:
            break
        try:
            q.put(json.loads(line))
        except Exception:
            print(f"[pump] non-json: {line[:120]!r}", flush=True)

import threading
threading.Thread(target=pump, daemon=True).start()

def err_pump():
    while not stop[0]:
        line = proc.stderr.readline()
        if not line:
            break
        print(f"[stderr] {line.decode(errors='replace')[:200]}", flush=True)

threading.Thread(target=err_pump, daemon=True).start()

def rpc(method, params, rid):
    proc.stdin.write((json.dumps({"jsonrpc": "2.0", "id": rid, "method": method, "params": params}) + "\n").encode())

def recv(rid, timeout=240):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        try:
            m = q.get(timeout=1)
        except queue.Empty:
            continue
        if m.get("id") == rid:
            return m
        if m.get("method") == "session/update" and m.get("params", {}).get("update", {}).get("sessionUpdate") == "agent_message_chunk":
            chunk = m['params']['update']['content'].get('text', '')
            print(f"[{time.monotonic() - t0:6.2f}s] STREAM text ({len(chunk)} chars): {chunk[:60]!r}", flush=True)
    raise TimeoutError(f"no response {rid} in {timeout}s")

t0 = time.monotonic()
print(f"[{0:6.2f}s] initialize…", flush=True)
rpc("initialize", {"protocolVersion": 1, "clientCapabilities": {}, "clientInfo": {"name": "event-probe", "version": "0"}}, 1)
recv(1, 120)
print(f"[{time.monotonic() - t0:6.2f}s] boot ok; session/new (model={MODEL})…", flush=True)
rpc("session/new", {"cwd": CWD, "mcpServers": []}, 2)
sn = recv(2, 120)
if "error" in sn:
    print("ERRO session/new:", sn["error"])
    sys.exit(1)
sid = sn["result"]["sessionId"]
print(f"[{time.monotonic() - t0:6.2f}s] session {sid}; set model={MODEL} + mode yolo…", flush=True)
rpc("session/set_config_option", {"configId": "model", "value": MODEL}, 4)
recv(4, 30)
rpc("session/set_config_option", {"configId": "mode", "value": "yolo"}, 5)
recv(5, 30)
print(f"[{time.monotonic() - t0:6.2f}s] prompt (grafo, deve demorar)...", flush=True)

# divisor: eventos que chegam ANTES da resposta final
seen = {"stream_text": 0, "other_updates": 0}
r0 = time.monotonic()
rpc("session/prompt", {"sessionId": sid, "prompt": [{"type": "text", "text": PROMPT}]}, 3)
fr = recv(3, 300)
dur = time.monotonic() - r0
print(f"[{time.monotonic() - t0:6.2f}s] FINAL em {dur:.1f}s", flush=True)
stop[0] = True
proc.terminate()
try:
    proc.wait(timeout=5)
except Exception:
    proc.kill()