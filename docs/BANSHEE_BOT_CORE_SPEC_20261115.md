# Banshee Bot Core: one bot brain, every MMO server (2026-11-15 12:46 AM CST)

Owner: Forever Bot (spec). Routed by Devbox. Blizz said "yes do it" at 12:45 AM CST.
Builds on `FOREVER_BOTS_SHARED_SPEC_20261114.md` §3 (game-neutral brain). This spec widens it from party companions to every server and adds world population ("dead internet").

## Goal
Every Banshee MMO server can be played solo with bots and feels full of players:
- **Companions:** Zoey, Jindrak, maianmagus (shared personas from banshee-accounts `identity.py`), plus `/fb` party bots.
- **Population:** AI bot players that roam, quest, level, chat, trade, group, run dungeons and keep the economy moving.
Both are separate on/off switches, off by default on servers with real players, and with both off the game plays like retail.

## Why WoW was easy (the four pieces every game needs)
1. **Headless player session:** a bot is a real player session inside the server with no network client, so it uses the server's own code for casting, loot, quests and trade.
2. **Navmesh:** walkable maps built from the game's own geometry.
3. **Complete server:** combat, quests, loot, market and duties actually work.
4. **Behavior library:** per class/job rotations, role tactics and per-dungeon scripts.
A game gets population bots only when it has all four. Companions can start once 1, 2 and basic combat exist.

## Architecture
```
banshee-bot-core (Rust crate, game-neutral)
  brain/      decision loop: safety > owner order > role policy > goal planner > optional LLM advice
  roles/      tank, healer, dd, support (game maps jobs/classes onto these)
  goals/      population planner: level, quest, gather/craft, sell/buy, socialize, group, log off/on
  economy/    budgets, price memory, market caps (see guardrails)
  chat/       templates first, alias table, optional rate-limited LLM, persona cards
  persona/    Zoey/Jindrak/maianmagus + generated population personas (name, schedule, playstyle)
  nav/        navmesh query trait, formation follow, grounded fallback
  sched/      tick budget, per-zone bot caps, day/night online schedules
per-game adapter (thin, in each server repo)
  Session     spawn/despawn a headless bot as a player session
  Actions     map core intents to that game's abilities, items, menus, NPC dialogs
  World       read-only facts: entities, threat, AoE, quest state, market
  Nav         that game's navmesh (built offline from client files by `bnav-extract`)
```
- Core never touches the network protocol. Adapters call the server's own in-process player APIs.
- LLM may rerank or phrase a legal action. It never invents one, never gets GM or economy authority, and its failure falls back to templates.

## Tools to build once
- **`bnav-extract`:** per-game geometry reader to a common navmesh (Recast/Detour format). Inputs: WoW mmaps (already exist), FFXI zone DATs, FFXIV sqpack (via Lumina-documented formats), SWTOR/others as found. REA (Ghidra) for unknown formats.
- **Behavior data:** rotations and tactics as data files per game, not code, so helpers can fill them in parallel.
- **`bot-soak`:** headless load test, N bots in one zone for an hour, reports tick time, server CPU/RAM, stuck bots, deaths, and economy drift.

## Guardrails (hard)
- Never restart FFXI while a human is online (CrazyAsian). Bot features hot-load behind flags.
- No player progress resets. Bot gear and gold are bot-only.
- Real players come first: bots never camp or claim a human's target, never buy out a market listing a human posted within N hours, never sell below a price floor, never flood chat. Per-player toggle hides bot chat (`/fb chat off`).
- Population caps per zone and per server, auto-throttled by server tick time.
- Private servers stay private (FF14, SWTOR). No public lists.

## Client side (Forever clients)
Each Forever client adds a **Crowds** group in Settings: bot draw distance, bot model detail, max nameplates, hide bot chat. Default is on with the Forever graphics look, and Original keeps retail-like limits.

## Rollout (small, verifiable builds)
| Step | Game | Scope | QA gate |
|---|---|---|---|
| C0 | all | Each server lead scores its game on the four pieces (yes/partial/no with evidence) | Devbox posts the table |
| C1 | FFXI | Extract `banshee-bot-core` from the existing `/fb` code (control clock, roles, orders) with no behavior change | `/fb` P0 checks still pass |
| C2 | FFXI | Zoey/Jindrak/maianmagus as core personas | Summon each, follow, fight, dismiss |
| C3 | FFXI | Population v1: 20 bots roam, level and chat in starter zones, flag off by default | `bot-soak` clean; no human target stolen |
| C4 | FFXI | Economy v1: AH buy/sell with price floor and buyout guard | AH prices stay inside band over 24h |
| C5 | WoW Forever | Adapter over existing playerbots so personas and chat match | Zoey same voice in WoW and FFXI |
| C6 | FF14 | Adapter on Kawari, Duty Support first, then companions | ARR first dungeon cleared solo with bots |
| C7+ | others | In order of C0 scores | per-game |

Every build reports build number, sha256 and QA result in Devbox Command, in CST. Nothing is called released before Game QA Bot passes it.
