# Security Policy — L.O.T.U.S.

Lotus is a specialized companion built on [Hermes Agent](https://github.com/NousResearch/hermes-agent). Hermes’s trust model still applies for the runtime: see [Hermes SECURITY.md](https://github.com/NousResearch/hermes-agent/blob/main/SECURITY.md).

## Reporting a vulnerability

Please report privately. Prefer GitHub Security Advisories on this repo, or contact the maintainers via a private channel listed on the GitHub profile — **do not** open a public issue for exploitable security bugs.

A useful report includes:

- Description and severity
- Affected file path / component
- Steps to reproduce on latest `master`
- Whether Hermes core or Lotus-only code is involved

Lotus does not operate a bug bounty.

## What Lotus treats as security-critical

1. **Crisis / self-harm pathways** — bypasses that suppress safety context, leak method detail, or disable refusal when danger language is present.
2. **Credential exposure** — API keys, `API_SERVER_KEY`, gateway tokens, or profile `.env` ending up in logs, the web UI, or the public repo.
3. **Web UI / API proxy** — auth bypass on the frontend proxy, SSRF through the gateway proxy, or leaking session tokens.
4. **Prompt / plugin surfaces that invent biography or medical authority** in a way that could enable social-engineering harm (report as product security if reproducible).

## Out of scope (as security advisories)

These are still welcome as regular issues/PRs:

- Companion voice quality (“sounds AI”, soft loops) — product bugs, not vulns
- Model hallucinations that invent scene details — tracked as product/context-lock bugs
- Hermes-core isolation / shell sandbox issues — report upstream to Nous Research
- “The AI gave imperfect emotional advice” without a safety bypass

## Deployment notes

- Never commit `.env`, `auth.json`, or `memories/`.
- Keep the Lotus web UI behind a strong `API_SERVER_KEY`; do not expose to the public internet without auth.
- Lotus is **not** a licensed clinician or emergency service. Operators should keep crisis redirects (e.g. 988 / local emergency) intact.
- Review third-party Hermes skills/plugins before enabling them in a Lotus profile — they run with agent privileges.

## Disclosure

Coordinated disclosure: 90 days from report, or until a fix ships, whichever comes first. Credit in release notes unless you ask for anonymity.
