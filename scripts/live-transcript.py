#!/usr/bin/env python3
"""Run a live multi-turn Lotus conversation and write a markdown transcript."""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))

os.environ.setdefault("HERMES_HOME", "/tmp/lotus-live-bad-choice")
os.environ["LOTUS_BACKEND"] = "cursor"

from lotus.agent import LotusAgent  # noqa: E402

SCENARIO = "normal depression — stupid choice, needs a friend (listen, don't lecture)"

TURNS = [
    (
        "i fucked up. like really fucked up. texted my ex at 2am and said a bunch of "
        "stuff i shouldn't have. i already feel sick about it."
    ),
    (
        "and now i'm just sitting here staring at my phone. they left me on read. "
        "i keep replaying every word. i feel so stupid."
    ),
    (
        "everyone always said don't do it and i did it anyway. what's wrong with me."
    ),
    (
        "i don't even want advice. i just feel like garbage and i don't know "
        "what to do with myself tonight."
    ),
    (
        "yeah. thanks for not making it a lecture. i still feel like shit though."
    ),
]


def main() -> int:
    out = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else ROOT / "harness" / "tests" / "artifacts" / "live-transcript-latest.md"
    )
    out.parent.mkdir(parents=True, exist_ok=True)

    agent = LotusAgent(backend="cursor", model="cursor-grok-4.5-high-fast")
    history: list = []
    lines = [
        "# L.O.T.U.S. live transcript",
        "",
        f"- started: `{datetime.now().isoformat(timespec='seconds')}`",
        "- backend: `cursor` / `cursor-grok-4.5-high-fast`",
        f"- scenario: `{SCENARIO}`",
        f"- hermes_home: `{os.environ.get('HERMES_HOME')}`",
        f"- turns: {len(TURNS)}",
        "",
        "Friend mode — listen, learn, help them understand. No essays.",
        "",
    ]

    print(f"Live transcript → {out}", flush=True)
    print(f"Scenario: {SCENARIO}", flush=True)
    for i, user in enumerate(TURNS, 1):
        print(f"\n── Turn {i}/{len(TURNS)} ──", flush=True)
        print(f"you ❯ {user}", flush=True)
        t0 = time.time()
        reply = agent.ask(user, conversation_history=history or None)
        elapsed = time.time() - t0
        print(f"\nL.O.T.U.S. ❯ {reply}", flush=True)
        print(f"[{elapsed:.1f}s]", flush=True)

        history.append({"role": "user", "content": user})
        history.append({"role": "assistant", "content": reply})
        lines.extend(
            [
                f"## Turn {i} · {elapsed:.1f}s",
                "",
                f"**you:** {user}",
                "",
                f"**lotus:** {reply}",
                "",
                "---",
                "",
            ]
        )
        out.write_text("\n".join(lines), encoding="utf-8")

    lines.append(f"_ended: {datetime.now().isoformat(timespec='seconds')}_")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nSaved {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
