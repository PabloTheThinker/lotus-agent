"""CLI entrypoint for the L.O.T.U.S. harness."""

from __future__ import annotations

import argparse
import os
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lotus-harness",
        description="L.O.T.U.S. — specialized Hermes mental-health companion harness",
    )
    parser.add_argument(
        "--hermes-home",
        default=os.environ.get("HERMES_HOME", ""),
        help="Hermes profile home (default: $HERMES_HOME or ~/.hermes/profiles/lotus)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    ask_p = sub.add_parser("ask", help="One-shot message")
    ask_p.add_argument("message", help="User message")
    ask_p.add_argument(
        "--backend",
        default="",
        help="Model backend: hermes (default) or cursor (Cursor CLI / Grok)",
    )
    ask_p.add_argument(
        "--model",
        default="",
        help="Model id (Hermes model, or Cursor id e.g. cursor-grok-4.5-high-fast)",
    )

    chat_p = sub.add_parser("chat", help="Simple interactive loop")
    chat_p.add_argument("--model", default="", help="Model override")
    chat_p.add_argument(
        "--backend",
        default="",
        help="Model backend: hermes (default) or cursor",
    )
    chat_p.add_argument(
        "--transcript",
        default="",
        help="Append a live markdown transcript to this path (created if missing)",
    )

    class_p = sub.add_parser("classify", help="Classify a message into a mission protocol")
    class_p.add_argument("message", help="User message")

    sub.add_parser("core-status", help="Show realtime living-model status")

    tick_p = sub.add_parser("core-tick", help="Run realtime core on a message (no LLM)")
    tick_p.add_argument("message", help="User message")

    sub.add_parser("continuity-status", help="Show continuity resume card / open threads")

    cont_p = sub.add_parser("continuity-tick", help="Run continuity engine on a message (no LLM)")
    cont_p.add_argument("message", help="User message")
    cont_p.add_argument("--first", action="store_true", help="Simulate first turn of session")

    doc_p = sub.add_parser("doctor", help="Check profile, keys, harness, gateway readiness")
    doc_p.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    prefs_p = sub.add_parser("prefs", help="Show or set locale / crisis-region prefs")
    prefs_sub = prefs_p.add_subparsers(dest="prefs_cmd", required=True)
    prefs_sub.add_parser("show", help="Print current prefs")
    prefs_set = prefs_sub.add_parser("set", help="Update prefs")
    prefs_set.add_argument("--lang", default="", help="Preferred language (en,es,fr,pt,de)")
    prefs_set.add_argument(
        "--regions",
        default="",
        help="Comma-separated crisis regions (US,CA,GB,AU,NZ,IE,IN,INTL)",
    )

    sub.add_parser("moments-status", help="Show moments connection graph summary")

    related_p = sub.add_parser("moments-related", help="Find moments related to a message")
    related_p.add_argument("message", help="User message to match against the graph")

    tick_m = sub.add_parser("moments-tick", help="Run moments engine on a message (no LLM)")
    tick_m.add_argument("message", help="User message")
    tick_m.add_argument("--session", default="cli-demo", help="Session id")

    sub.add_parser("compound-status", help="Show compounding mission + journey meter")

    tick_c = sub.add_parser("compound-tick", help="Run compound engine on a message (no LLM)")
    tick_c.add_argument("message", help="User message")

    sub.add_parser("profile-status", help="Show internal user profile + Lotus notes summary")

    tick_p = sub.add_parser("profile-tick", help="Update internal profile from a message (no LLM)")
    tick_p.add_argument("message", help="User message")

    sub.add_parser("research-status", help="Show research queue + approaches + recent log")
    seed_p = sub.add_parser(
        "research-seed",
        help="Seed offline baseline approaches when library is empty",
    )
    seed_p.add_argument(
        "--force",
        action="store_true",
        help="Seed even if approaches already exist (appends only when empty)",
    )

    priv_p = sub.add_parser(
        "privacy",
        help="Export or wipe lotus-core companion state (sensitive)",
    )
    priv_sub = priv_p.add_subparsers(dest="privacy_cmd", required=True)
    priv_sub.add_parser("status", help="Summarize lotus-core files on disk")
    priv_export = priv_sub.add_parser("export", help="Zip lotus-core to a portable archive")
    priv_export.add_argument(
        "--out",
        default="",
        help="Destination zip path or directory (default: under HERMES_HOME)",
    )
    priv_export.add_argument(
        "--keep-prefs",
        action="store_true",
        help="Omit prefs.json from the export",
    )
    priv_wipe = priv_sub.add_parser(
        "wipe",
        help="Delete lotus-core personal state (requires --yes)",
    )
    priv_wipe.add_argument(
        "--yes",
        action="store_true",
        help="Confirm irreversible wipe",
    )
    priv_wipe.add_argument(
        "--keep-prefs",
        action="store_true",
        help="Preserve locale / crisis region prefs",
    )
    priv_wipe.add_argument(
        "--keep-approaches",
        action="store_true",
        help="Preserve APPROACHES.md + research_log.jsonl",
    )

    args = parser.parse_args(argv)

    hermes_home = args.hermes_home or str(
        os.path.expanduser("~/.hermes/profiles/lotus")
    )

    if args.cmd == "classify":
        from .protocols import classify_all

        for p in classify_all(args.message):
            print(p.value)
        return 0

    if args.cmd == "core-status":
        os.environ["HERMES_HOME"] = hermes_home
        from .realtime.core import reset_core

        m = reset_core().model
        print(m.prompt_block())
        print(f"\npaths: HERMES_HOME={hermes_home}")
        return 0

    if args.cmd == "core-tick":
        os.environ["HERMES_HOME"] = hermes_home
        from .realtime.core import reset_core

        core = reset_core()
        print(core.before_turn(args.message))
        core.after_turn(args.message, "(dry-run assistant reply)")
        print("\n--- saved living model ---")
        print(core.model.prompt_block())
        return 0

    if args.cmd == "continuity-status":
        os.environ["HERMES_HOME"] = hermes_home
        from .continuity.engine import reset_continuity
        from .continuity.paths import resume_card_path

        st = reset_continuity().state
        print(f"sessions={st.session_count} affect={st.last_affect} protocol={st.last_protocol}")
        print(f"resume: {st.resume_summary or '(empty)'}")
        print("open_threads:", "; ".join(st.open_threads) or "(none)")
        print("checkins:", "; ".join(st.pending_checkins) or "(none)")
        print(f"\n{resume_card_path()}")
        return 0

    if args.cmd == "continuity-tick":
        os.environ["HERMES_HOME"] = hermes_home
        from .continuity.engine import reset_continuity

        eng = reset_continuity()
        eng.on_session_start(session_id="cli-demo", platform="cli")
        print(eng.before_turn(args.message, is_first_turn=bool(args.first)))
        eng.after_turn(args.message, "I'm here with you — we can come back to this whenever you're ready.")
        eng.on_session_end()
        print("\n--- resume ---")
        print(eng.state.resume_summary)
        print("threads:", eng.state.open_threads)
        return 0

    if args.cmd == "doctor":
        os.environ["HERMES_HOME"] = hermes_home
        from .doctor import run_doctor

        report = run_doctor(hermes_home)
        if getattr(args, "json", False):
            import json

            print(json.dumps(report.to_dict(), indent=2))
        else:
            print(report.render())
        return 0 if report.ok and not report.errors else 1

    if args.cmd == "prefs":
        os.environ["HERMES_HOME"] = hermes_home
        from .prefs import get_prefs, reset_prefs, update_prefs

        reset_prefs()
        if args.prefs_cmd == "show":
            p = get_prefs()
            print(f"preferred_lang={p.preferred_lang}")
            print(f"lang_locked={p.lang_locked}")
            print(f"crisis_regions={','.join(p.crisis_regions)}")
            print(f"updated_at={p.updated_at or '—'}")
            return 0
        if args.prefs_cmd == "set":
            kwargs = {}
            if args.lang:
                kwargs["preferred_lang"] = args.lang
            if args.regions:
                kwargs["crisis_regions"] = [
                    r.strip() for r in args.regions.split(",") if r.strip()
                ]
            if not kwargs:
                print("Nothing to set — pass --lang and/or --regions")
                return 2
            p = update_prefs(**kwargs)
            print(f"preferred_lang={p.preferred_lang}")
            print(f"crisis_regions={','.join(p.crisis_regions)}")
            return 0

    if args.cmd == "moments-status":
        os.environ["HERMES_HOME"] = hermes_home
        from .moments import reset_moments
        from .moments.paths import moments_json_path, moments_md_path

        g = reset_moments().graph
        open_n = sum(1 for m in g.moments if m.status in {"open", "active"})
        print(f"moments={len(g.moments)} open/active={open_n} links={len(g.links)}")
        for m in g.moments[-8:]:
            print(f"  [{m.status}] {m.kind}: {m.title}")
        print(f"\n{moments_json_path()}")
        print(moments_md_path())
        return 0

    if args.cmd == "moments-related":
        os.environ["HERMES_HOME"] = hermes_home
        from .moments import reset_moments

        hits = reset_moments().find_related(args.message, limit=8)
        if not hits:
            print("(no related moments)")
            return 0
        for m, score in hits:
            print(f"{score:.2f}  [{m.kind}/{m.status}] {m.title} — {m.summary[:100]}")
        return 0

    if args.cmd == "moments-tick":
        os.environ["HERMES_HOME"] = hermes_home
        from .moments import reset_moments

        eng = reset_moments()
        print(eng.before_turn(args.message, is_first_turn=True, session_id=args.session))
        eng.after_turn(args.message, "I'm here with you — we can come back to this whenever you're ready.", session_id=args.session)
        print("\n--- graph ---")
        print(f"moments={len(eng.graph.moments)} links={len(eng.graph.links)}")
        for m in eng.graph.moments[-5:]:
            print(f"  {m.id} [{m.kind}] {m.title}")
        return 0

    if args.cmd == "compound-status":
        os.environ["HERMES_HOME"] = hermes_home
        from .compound import reset_compound
        from .compound.paths import compound_json_path, compound_md_path

        st = reset_compound().state
        mission = st.active()
        if not mission:
            print("(no active mission)")
        else:
            m = mission.meter
            print(f"mission: {mission.statement}")
            print(f"status={mission.status} rung={mission.current_ladder_rung} consent={mission.consent}")
            print(
                f"meter: {m.checkpoints_met}/{m.checkpoints_total} "
                f"score={m.compound_score:.2f} horizon={m.estimated_horizon} "
                f"center_met={m.center_met} guidance={m.guidance_unlocked}"
            )
            for cp in mission.checkpoints:
                mark = "◆" if cp.is_center else "•"
                print(f"  {mark} [{cp.status}] {cp.ladder_rung}: {cp.title}")
        print(f"\n{compound_json_path()}")
        print(compound_md_path())
        return 0

    if args.cmd == "compound-tick":
        os.environ["HERMES_HOME"] = hermes_home
        from .compound import reset_compound

        eng = reset_compound()
        print(eng.before_turn(args.message, is_first_turn=True))
        eng.after_turn(args.message, "I'm here with you — one secure step at a time.")
        print("\n--- after ---")
        print(eng.before_turn(args.message))
        return 0

    if args.cmd == "profile-status":
        os.environ["HERMES_HOME"] = hermes_home
        from .profile import reset_profile
        from .profile.paths import lotus_notes_path, profile_json_path, profile_md_path

        p = reset_profile().profile
        print(f"confidence={p.confidence} turns={p.turn_count}")
        print(f"name={p.preferred_name or '—'}")
        print(f"affect={p.current_affect} protocols={', '.join(p.active_protocols) or '—'}")
        print(f"mission={p.active_mission or '—'}")
        print(f"formulation: {p.formulation or '(forming)'}")
        print(f"notes={len(p.lotus_notes)} concerns={len(p.presenting_concerns)}")
        print(f"\n{profile_json_path()}")
        print(profile_md_path())
        print(lotus_notes_path())
        return 0

    if args.cmd == "profile-tick":
        os.environ["HERMES_HOME"] = hermes_home
        from .profile import reset_profile
        from .realtime.model import LivingUserModel

        eng = reset_profile()
        eng.after_turn(
            args.message,
            "I'm here with you.",
            living_model=LivingUserModel.load(),
        )
        print(eng.before_turn())
        return 0

    if args.cmd == "research-status":
        os.environ["HERMES_HOME"] = hermes_home
        from .realtime.core import reset_core

        core = reset_core()
        st = core.research.pulse_status(core.model)
        print(f"queued={st['queued']} done={st['done']} approaches={st['approaches']}")
        for t in st.get("pending_topics") or []:
            print(f"  • {t}")
        if st.get("log_tail"):
            print("\nrecent log:")
            for line in st["log_tail"]:
                print(f"  {line[:160]}")
        return 0

    if args.cmd == "research-seed":
        os.environ["HERMES_HOME"] = hermes_home
        from .realtime.core import reset_core

        core = reset_core()
        if core.model.help_approaches and not args.force:
            print(f"approaches already present ({len(core.model.help_approaches)}) — use --force to no-op")
            print("(seed only fills an empty library)")
            return 0
        n = core.research.seed_offline_approaches(core.model)
        core.model.save()
        print(f"seeded={n} approaches={len(core.model.help_approaches)}")
        return 0

    if args.cmd == "privacy":
        os.environ["HERMES_HOME"] = hermes_home
        from pathlib import Path

        from .privacy import export_core, summarize_core, wipe_core

        if args.privacy_cmd == "status":
            st = summarize_core()
            print(f"core_dir={st['core_dir']}")
            print(f"files={st['file_count']} bytes={st['bytes']}")
            for name in st["files"]:
                print(f"  {name}")
            return 0
        if args.privacy_cmd == "export":
            out = Path(args.out) if args.out else None
            path = export_core(out, keep_prefs=bool(args.keep_prefs))
            print(f"exported={path}")
            return 0
        if args.privacy_cmd == "wipe":
            if not args.yes:
                print("Refusing wipe without --yes (irreversible).")
                print("Example: lotus-harness privacy wipe --yes --keep-prefs")
                return 2
            n, names = wipe_core(
                keep_prefs=bool(args.keep_prefs),
                keep_approaches=bool(args.keep_approaches),
            )
            print(f"removed={n}")
            for name in names:
                print(f"  {name}")
            return 0

    from .agent import LotusAgent
    from .backends.cursor_cli import resolve_backend

    backend = resolve_backend(getattr(args, "backend", "") or "")
    agent = LotusAgent(
        hermes_home=hermes_home,
        model=getattr(args, "model", "") or "",
        backend=backend,
    )

    if args.cmd == "ask":
        if backend == "cursor":
            print(f"[backend=cursor model={agent._model or 'cursor-grok-4.5-high-fast'}]", file=sys.stderr)
        print(agent.ask(args.message))
        return 0

    if args.cmd == "chat":
        print("L.O.T.U.S. harness — type 'exit' to quit.")
        if backend == "cursor":
            print(f"Backend: Cursor CLI ({agent._model or 'cursor-grok-4.5-high-fast'})")
        print(
            "Companion only. If you are in crisis, contact local emergency services or 988 (US)."
        )
        transcript_path = Path(args.transcript).expanduser() if getattr(args, "transcript", "") else None
        if transcript_path:
            transcript_path.parent.mkdir(parents=True, exist_ok=True)
            if not transcript_path.exists():
                transcript_path.write_text(
                    "# L.O.T.U.S. live transcript\n\n"
                    f"- backend: `{backend}`\n"
                    f"- started: {__import__('datetime').datetime.now().isoformat(timespec='seconds')}\n\n",
                    encoding="utf-8",
                )
            print(f"Transcript → {transcript_path}")
        history: list = []
        turn_n = 0
        while True:
            try:
                user = input("\nyou ❯ ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
            if not user:
                continue
            if user.lower() in {"exit", "quit", ":q"}:
                return 0
            reply = agent.ask(user, conversation_history=history or None)
            print(f"\nL.O.T.U.S. ❯ {reply}")
            history.append({"role": "user", "content": user})
            history.append({"role": "assistant", "content": reply})
            if transcript_path:
                turn_n += 1
                stamp = __import__("datetime").datetime.now().strftime("%H:%M:%S")
                with transcript_path.open("a", encoding="utf-8") as tf:
                    tf.write(f"## Turn {turn_n} · {stamp}\n\n")
                    tf.write(f"**you:** {user}\n\n")
                    tf.write(f"**lotus:** {reply}\n\n")
                    tf.write("---\n\n")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
