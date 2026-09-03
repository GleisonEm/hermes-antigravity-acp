#!/usr/bin/env python3
"""Prova do keep-alive do provider antigravity-acp no Hermes.

Roda 2 prompts seguidos no MESMO processo contra o kernel ACP e mede:
  - prompt 1: boot do kernel (session/new + quota) — ~8-10s
  - prompt 2: reuso da sessão viva           — ~1.5s  (5-6x mais rapido)

Se os DOIS tempos forem iguais (~8-10s), o keep-alive esta DESLIGADO
(model.acp_keep_alive=false) ou o kernel morreu entre requests.

Uso:
  python3 test_keepalive.py [modelo] [num_prompts]
  python3 test_keepalive.py gemini-3.8-flash-high 3

Nao deixa kernel orfao: o registro keep-alive vive no processo Python,
entao o kernel filho morre junto com o script.
"""
import os
import sys
import time

KEEP_ALIVE = os.getenv("HERMES_ANTIGRAVITY_ACP_KEEP_ALIVE", "1")
LEAN = os.getenv("HERMES_ANTIGRAVITY_ACP_LEAN_PROMPT", "1")
os.environ["HERMES_ANTIGRAVITY_ACP_KEEP_ALIVE"] = KEEP_ALIVE
os.environ["HERMES_ANTIGRAVITY_ACP_LEAN_PROMPT"] = LEAN

REPO = os.path.expanduser("~/.hermes/hermes-agent")
sys.path.insert(0, REPO)

from hermes_cli.auth import get_external_process_provider_status  # noqa: E402
from agent.copilot_acp_client import CopilotACPClient  # noqa: E402

MODEL = sys.argv[1] if len(sys.argv) > 1 else "gemini-3.8-flash-high"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 2

status = get_external_process_provider_status("antigravity-acp")
cmd, args = status["command"], status["args"]
print(f"kernel : {cmd} args={args} configured={status['configured']}")
print(f"model  : {MODEL}  prompts={N}  keep_alive={KEEP_ALIVE} lean={LEAN}")

client = CopilotACPClient(
    api_key="test",
    base_url="acp://antigravity",
    acp_command=cmd,
    acp_args=args,
    acp_cwd=REPO,
)

times: list[float] = []
for i in range(1, N + 1):
    t0 = time.time()
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": f"Reply with exactly: PONG_KEEPALIVE_{i}"}],
            timeout=180,
        )
        dt = time.time() - t0
        times.append(dt)
        try:
            text = resp.choices[0].message.content
        except Exception:
            text = str(resp)[:120]
        print(f"prompt {i}: {dt:5.1f}s -> {str(text)[:60]!r}")
    except Exception as e:
        print(f"prompt {i}: FAILED after {time.time()-t0:.1f}s -> {type(e).__name__}: {e}")

client.close()

if len(times) >= 2:
    ratio = times[0] / max(times[1], 0.01)
    verdict = "KEEP-ALIVE ATIVO (reuso de sessao)" if ratio >= 1.8 else (
        "keep-alive aparentemente INATIVO (tempos parecidos)"
    )
    print(f"\nveredito: {verdict} — p1={times[0]:.1f}s p2={times[1]:.1f}s ({ratio:.1f}x)")