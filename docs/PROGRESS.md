# Banshee Bot Core — progress

Times are America/Chicago (CST).

## 2026-11-15 12:49 AM CST — project stood up

- Repo: `~/dev/banshee-bot-core` (local git only, no remote).
- Governing spec landed: `docs/BANSHEE_BOT_CORE_SPEC_20261115.md` (Forever Bot, sha256 `fe8138bb5bec23f55f26060626f28c76aff9d64b54b24ec0b8cd9cb2b0a43bc3`).
- Lead model: Codex GPT-6-Astra ultra fast, session `codex-banshee-bot-core`.
- Phase order locked: C0 readiness table (consume `BOT-READINESS.md` scores already being collected; do not re-broadcast) → C1 extract core from FFXI `/fb` with no behavior change → C2 FFXI companions → C3 20 population bots → C4 auction house → C5 WoW personas → C6 FF14 Duty Support on Kawari.
- Walking maps first: any server scoring 0 / no on a four-piece item gets a task to its owning lead via the coordinator inbox.
- Features ship off until verified; finished features then follow Blizz's on-by-default rule, except real-player servers (CrazyAsian) stay off by default.
- Next: scaffold the Rust workspace (`banshee-bot-core`, `bnav-extract`, `bot-soak`), locate FFXI `/fb` (read only), start C1, and post the C0 table as scores arrive.

No milestone verdict yet.
