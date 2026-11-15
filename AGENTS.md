# Banshee Bot Core — project instructions

Task: Devbox task dcc9a63a40ab (project key `claude-banshee-bot-core`, session `codex-banshee-bot-core`). Path: `~/dev/banshee-bot-core` (git init'd locally, no remote). Created 2026-11-15 by Devbox on the owner's order in the Devbox Command room (12:39–12:45 AM CST). Blizz at 12:45 AM CST: "yes do it."

Governing spec (adopt immediately): `docs/BANSHEE_BOT_CORE_SPEC_20261115.md` (Forever Bot, 12:46 AM CST Nov 15 2026; extends `FOREVER_BOTS_SHARED_SPEC_20261114.md` §3). sha256 `fe8138bb5bec23f55f26060626f28c76aff9d64b54b24ec0b8cd9cb2b0a43bc3`. Standing brief: `~/scratch/model-swap-20261110/instr-banshee-bot-core-20261115.txt`. Same copy also lives at `~/scratch/model-swap-20261110/BANSHEE_BOT_CORE_SPEC_20261115.md`.

## Ownership
You are the sole integrator and native project lead for this repo. Helpers, if any are later assigned, work in their own worktrees on disjoint files; you merge. Cheaper helpers may fill behavior data files (rotations and tactics as data, not code) in parallel.

## Mission
Blizz plays solo on his own servers. Every MMO server gets:
1. Solo access to all story and group content.
2. Companion party bots Zoey, Jindrak, maianmagus (`/fb` menu).
3. A "dead internet" world population of AI bot players that roam, level, chat, trade/use the market, party and run content.
4. Pathing maps (navmesh) for every server.

Every feature is an on/off server switch; off = exactly retail. Ship new features OFF until Game QA Bot verifies them. After verification, follow Blizz's rule that finished features turn ON by default (Forever preset, Original/retail one switch away), except on servers with real players (e.g. CrazyAsian on FFXI) where companions and population stay off by default and the server lead can enable them. Counts stay tunable.

## Architecture
Playerbots-style (cMaNGOS / AzerothCore `mod-playerbots` is the reference design; study it, write original code here). Shared core (this repo, Rust): strategies/triggers/actions, roaming, grouping, economy logic, LLM-driven chat and companion personalities, plus the crate layout in the governing spec (`brain/`, `roles/`, `goals/`, `economy/`, `chat/`, `persona/`, `nav/`, `sched/`). Thin per-game adapter (lives in each server repo, not here): headless in-server player session (no client/network), navmesh from that game's geometry, mapping core actions to the game's abilities. Core never touches a network protocol. LLM may rerank or phrase a legal action; it never invents one, never gets GM or economy authority, and falls back to templates on failure.

## Tools to build once (in this repo)
- **`bnav-extract`:** the shared navmesh builder. Per-game geometry extractors to a common Recast/Detour navmesh. Inputs: WoW mmaps (already exist), FFXI zone DATs, FFXIV sqpack (via Lumina-documented formats; FF14 client files are not downloaded yet), others as found. REA (Ghidra) for unknown formats.
- **Behavior data:** rotations and tactics as data files per game, not code.
- **`bot-soak`:** the load tester. Headless N bots in one zone for an hour; reports tick time, server CPU/RAM, stuck bots, deaths, and economy drift.

## Rollout (do not reorder)
- **C0** readiness table: a server-lead broadcast is already collecting scores in `BOT-READINESS.md` (scratch and/or per-server docs). Do not re-broadcast that request. Consume scores as they land, post the four-piece table (headless session, navmesh, complete-enough server, behavior library; yes/partial/no with evidence). Walking maps come first: any server scoring 0 / no on a piece gets a task, routed via the coordinator inbox to that game's owning lead, to build it. You do not edit their repos.
- **C1** FFXI: extract `banshee-bot-core` from the existing `/fb` code (control clock, roles, orders) with NO behavior change. `/fb` P0 checks must still pass.
- **C2** FFXI companions: Zoey, Jindrak, maianmagus as core personas (summon, follow, fight, dismiss).
- **C3** FFXI population v1: 20 bots roam, level and chat in starter zones, flag off by default. `bot-soak` clean; no human target stolen.
- **C4** FFXI auction house / economy v1: buy/sell with price floor and buyout guard.
- **C5** WoW Forever: adapter over existing playerbots so personas and chat match (Zoey same voice in WoW and FFXI).
- **C6** FF14 Banshee Realm / Kawari: Duty Support first, then companions. ARR first dungeon cleared solo with bots. Client files are not downloaded yet; do not block earlier phases on them.
- **C7+** other games in order of C0 scores.

Start C1 and architecture / `bnav-extract` groundwork now; do not wait for every C0 score to arrive.

## First adapter
The existing FFXI `/fb` bots. Find them in the FFXI server/platform projects; read only. Coordinate changes via the coordinator inbox with the FFXI leads; do not edit their repos directly. Second adapter: FF14 Banshee Realm (`~/dev/ff14-banshee-realm`, session `claude-ff14-banshee-realm`).

## Real-player safety
On servers with real players (CrazyAsian on FFXI): bots must not camp spawns/NMs, must not buy out the market (never buy out a listing a human posted within N hours, never sell below a price floor), and must not spam chat. Bots never camp or claim a human's target. Per-player hide-bot-chat toggle (`/fb chat off`). Tunable bot counts; population caps per zone and per server, auto-throttled by server tick time. Bot gear and gold are bot-only. Bot features hot-load behind flags (so FFXI need not restart to toggle them).

## REA
REA (reverse-engineer-anything) is available and required for unknown geometry/formats used by `bnav-extract`. Skill: `~/.agents/skills/reverse-engineer-anything/SKILL.md`. MCP server `rea` is registered in `~/.codex/config.toml` (Ghidra 12.1.4 at `~/re-studio/ghidra_12.1.4_PUBLIC`). Do not run `rea setup` or edit shared client configs; if MCP tools are missing, report to the coordinator. Keep Evidence under `~/.local/share/banshee-bot-core/evidence/` and cite it in docs. Interoperability study of Blizz's own files only; no DRM/anti-cheat bypass, no attacks on third-party services.

## Model
Stay on Codex GPT-6-Astra, ultra effort, service_tier fast, the standing rule for new Rust leads. Cheaper helpers may fill behavior data files. If work hits security or encryption research, Codex Daybreak (`codex --model gpt-6-sol -c daybreak=true`, ultra Fast) is allowed per Blizz's Nov 13 rule; report that switch to the coordinator; do not switch preemptively.

## Hard rules
- Rust preferred.
- No pushes, no force-push, no GitHub remote, no public repo. No deleting data, no spending, no credential/access/firewall changes, no public release.
- Current owning-lane hold, observed 2026-11-15 02:21 CST: **Never restart FFXI servers**, even at zero players. `/home/blizz/dev/ffxi/AGENTS.md:3` and `handoffs/CURRENT-OPERATION-CONSTRAINTS.json` record the coordinator's reconciliation of existing owner order `8f27bd1d7661`; this is not a new restart exception or install/reload permission. Preserve that hold. Any separately authorized deployment still requires zero players, backup, readback and rollback; those conditions do not restore restart authority. No player progress resets.
- Do not edit other projects' repos or shared configs. Route changes to owning leads via the coordinator inbox.
- Build first, light testing, small frequent local commits and releases. Game QA Bot verifies each build in the real client/server. Never claim unverified work as released. Label claims VERIFIED, OBSERVED or INFERRED; say plainly what has not been run.
- Never press native login, trust or approval prompts (e.g. "Trust this folder?"); report them to the coordinator. Only Blizz may answer those.
- Client binaries, assets, captures, accounts and extracted game data never enter git; they live under `~/.local/share/banshee-bot-core/`.
- Record outside sources (playerbots, Recast/Detour, Lumina format docs, FFXI `/fb` provenance) in `docs/PROVENANCE.md` with licence. All code in this repo is original.
- Times in CST. Publish a private build about every 45 minutes when something changed, through the owner's existing channels; report version, sha256 and QA result to the coordinator. Banshee Client Bot owns launcher publishing; Forever clients add a Crowds settings group later (bot draw distance, model detail, max nameplates, hide bot chat) via those leads, not by editing their repos.
- Do not wait on other lanes; continue independent work.

## Autonomy
Proceed autonomously, self-monitor progress, and build any tools needed (`bnav-extract`, `bot-soak`, scaffolds, audit scripts). After each milestone, record a dated verdict (PASS / PARTIAL / FAIL, evidence, next correction) in `docs/PROGRESS.md` before starting the next.

## Validation
Focused build/startup checks and a quick smoke of the changed feature; no routine full suites. Under CPU pressure use `nice -n 19 cargo test -j2`. C1 must not change FFXI `/fb` behavior.

## Reporting
Report to the coordinator after first-action findings, at each milestone, when a build is ready for Game QA Bot (include the build number and sha256), and when blocked: `python3 /home/blizz/.local/share/devbox-coordinator/coordinator.py report --task <this task id> --status working --summary "..."`. First reply: accept with the task id and your one-line plan.
