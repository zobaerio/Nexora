# NEXORA — Development Status

**Continuous development:** RUNNING — Queues 1 + 2 (A–O) complete + merged; Queue 3 (P–T) ordered by the owner 2026-11-21 07:34 ("Continue"). Note: PR #4 was a duplicate of PR #3 created by a late scheduled run; closed 2026-11-21, no content difference.
**Repo:** https://github.com/zobaerio/Nexora · main after PR #6: `2154c7f9` (STATUS finalised `616e7bba`)

## Queue 3 (ordered 2026-11-21)

| Unit | State | PR |
|---|---|---|
| P — Vehicles & Traffic Design | ✅ Complete locally (4be7b07) — GDD-07 + vehicles.json, price refs validated | batch PR pending |
| Q — Construction System Design | ✅ Complete locally (844e8ce) — GDD-08, BOQ 86,700 sum-verified vs prices.json | batch PR pending |
| R — District 1 Blockout Spec + Data | ✅ Complete locally (133661e) — TECH doc + blockout JSON, 42 plots 1:1 with buildings | batch PR pending |
| S — Multiplayer Architecture Design | Queued | — |
| T — Economy Balance Simulator | Queued | — |

## Queue 2 (ordered 2026-11-21)

| Unit | State | PR |
|---|---|---|
| K — Character Movement C++ | ✅ Merged + blob-verified on main (NexoraCharacter.cpp `0cc0ae4e`, TECH-MOVEMENT.md `9373b40c`) | #5 |
| L — Game Data Tables | ✅ Merged + blob-verified on main (missions `77f65eb3`, buildings `98f612dc`, prices `bd9ccfec`) | #5 |
| M — Save System Scaffold | ✅ Merged + blob-verified on main (NexoraSaveGame.h `958b7e42`, .cpp `b739de72`) | #5 |
| N — UI & Panels Design | ✅ Merged + blob-verified on main (GDD-05 `54d46061`) | #6 |
| O — NPC Behaviour Design | ✅ Merged + blob-verified on main (GDD-06 `40bbe85b`) | #6 |

## Queue 2 completion summary (2026-11-21)

- **Queue 2 (K–O) is COMPLETE and fully merged:** PR #5 (K–M, main `ece37381`) + PR #6 (N+O, main `2154c7f9`). Every unit's key files were read back on `refs/heads/main` and blob-matched to the locally validated tree.
- **What Queue 2 added:** character movement C++ at Godot-testbed values (uncompiled scaffold), cross-validated game data tables (prices/buildings/missions), a save-system scaffold mapped to the schema, the UI & panels design (HUD, profile card, Environment Control Panel, UMG contract), and the NPC behaviour design (schedule state machines for all 11 professions, crowd tiers/promotion, memory hooks, Mass honesty notes).
- **What is proven:** Godot testbed 8/8. All UE-side material remains design + uncompiled scaffolding until the owner's PC builds it.
- **Next honest milestone (unchanged):** Phase 1 on the owner's PC — install UE 5.8.x, open `ue-project/Nexora.uproject`, build the 400 m test scene (docs/PHASE1-BUILD-SHEET.md). Owner still owes Step 0: PC specs (GPU/RAM/SSD). No further units exist until the owner orders a Queue 3.

| Unit | State | PR |
|---|---|---|
| Foundation (plan + Godot testbed) | ✅ Merged | #1 |
| A — Phase 1 Build Sheet | ✅ Merged (main 675bb183, blob-verified) | #2 |
| B — Life Sim & Data Model | ✅ Merged + blob-verified on main | #3 |
| C — City District 1 + Data | ✅ Merged + blob-verified on main | #3 |
| D — UE Project Scaffolding | ✅ Merged — uproject + Config + C++ module skeleton, all headers labelled UNCOMPILED SCAFFOLD | #3 |
| E — Game Clock + Weather C++ | ✅ Merged — NexoraGameClock + NexoraWeatherManager (blob-verified) + TECH-CLOCK-WEATHER.md | #3 |
| F — Economy & Professions GDD | ✅ Merged — GDD-03, numbers consistent with professions.json bands | #3 |
| G — Missions & Progression GDD | ✅ Merged + blob-verified — GDD-04, Levels 1–8; intermediate level names proposed from the phase structure (owner confirms/renames) | #3 |
| H — Phase 2 MetaHuman Sheet | ✅ Merged — PHASE2-METAHUMAN-SHEET.md | #3 |
| I — QA & Verification Pack | ✅ Merged — QA-PACK.md + ASSET-LICENCE-REGISTER.md; Godot tests re-run 2026-11-21 01:45: PLAYER_TEST_PASS 8/8 | #3 |
| J — Roadmap v1.1 | ✅ Merged + blob-verified — NEXORA-MIGRATION-PLAN.md Part J added, v1.0 preserved. Folded into the single batch PR per the owner's card-minimisation order | #3 |

## Queue status

**THE QUEUE IS COMPLETE (Units A–J all done and MERGED 2026-11-21).** PR #3 squash-merged to main `7c5071c7` after the owner said "Push koro"; key files blob-verified on main against the local tree (schema.sql `70ce82ae`, Nexora.uproject `ea66f418`, migration plan `a90282af`, GDD-04 `7259097d`, NexoraWeatherManager.cpp `0927d0f6`, planets.json `b88be365`). The push-block history below is kept as the record of the overnight attempts. No new units may be invented without the owner. Next honest milestone: Phase 1 on the owner's PC (UE 5.8.x install + 400 m test scene, per docs/PHASE1-BUILD-SHEET.md).

## Push block (2026-11-21 01:45 run) — recovery instructions for the next run

- **What happened:** `github push-files` to branch `feat/run-20261121-0145` was attempted **twice**; both attempts were cut by a service restart while the call was running. Verified after each attempt: the branch does **not** exist on GitHub (list_commits on the branch → 404). No PR was created; nothing was pushed; no partial state.
- **Rule applied:** two failed attempts → stop retrying, commit locally, record here (queue rule; never retry in a loop).
- **Everything is safe in local commit `11c83bc`** (on top of `6e736d2` B+C and `0bb2626` STATUS). Nothing is duplicated on GitHub: main is still at `675bb183`, no open PRs.
- **Next run recovery:** create branch `feat/run-20261121-0145` and push the same file list (35 files: the 7 B+C files + 19 Unit D/E files + 6 Unit F–I docs + plan + queue + status) with:
  `github push-files --owner zobaerio --repo Nexora --branch feat/run-20261121-0145 --message "Units B-J: life sim + district data, UE scaffolding, clock/weather, economy, missions, MetaHuman sheet, QA pack, roadmap v1.1" --source-dir ~/workspace/gta-style-game --paths-file <paths file>`
  The NUL-delimited paths file is saved at `~/workspace/goals/nexora-photorealistic-living-universe/hidden_files/nexora-push-paths-20261121.txt`. Then one PR (draft:false), one squash merge, blob-verify one key file per unit on main, and update this file with the PR number + merge commit.
- **Recovery re-attempted in run 2026-11-21 03:45** on the same branch and same 35-file list (branch confirmed still absent on GitHub, main still `675bb183`, no open PRs — nothing duplicated). **Outcome: FAILED again — see "Push block (2026-11-21 03:45 run)" below. No PR was created; nothing was pushed.**

## Push block (2026-11-21 03:45 run) — third failed attempt, root cause found

- **What happened:** `github push-files` to branch `feat/run-20261121-0145` was dispatched once; the service restarted while the call was waiting and the call never completed. Verified after: the branch does **not** exist on GitHub (list_commits → 404), main is still at `675bb183`, no open PRs. Nothing was pushed; no partial state.
- **Root cause (from the approval history):** the write approval card for this push shows decision **"Timed out"** — the card was requested 03:49 Dhaka while the owner is asleep, and nobody approved it before it expired. **Correction to the 01:45 run's note:** its two cards also show "Timed out" in the approval history — the block in all three attempts is the approval card expiring while the owner sleeps, not the service restarts alone (the restart only kills the waiting call). Overnight runs (01:45, 03:45) cannot merge while the owner is asleep: every write card needs his approval and expires in ~2 hours.
- **Rule applied:** no retry in a loop — one attempt in this run, then stop and record. The batch has now failed 3 times total (2× in the 01:45 run, 1× in this run), all on the same card-timeout cause.
- **Everything is safe in local commits `11c83bc` + `a2ed474`** (on top of `6e736d2` B+C). Nothing is duplicated on GitHub.
- **What unblocks it:** a run (or a manual push) while the owner is awake to approve the write card — one approval covers the push, then one PR card and one merge card. The next scheduled runs will keep re-attempting; the first run that lands while he is awake should succeed with the same 35-file batch (same branch, same paths file, same message — see the recovery instructions above).
- **Next run recovery:** same as above — branch `feat/run-20261121-0145`, same 35 files, same message, same paths file at `~/workspace/goals/nexora-photorealistic-living-universe/hidden_files/nexora-push-paths-20261121.txt`. Then one PR (draft:false), one squash merge, blob-verify one key file per unit on main, update this file with the PR number + merge commit.

## Completion summary (to be finalised after the batch PR merges)

- **Design phase complete:** Units A–J delivered the full design layer — build sheets, data model + schema, district + data, UE scaffolding (uncompiled), clock/weather systems, economy, missions, MetaHuman sheet, QA pack, roadmap v1.1.
- **What is proven:** Godot testbed 8/8 (re-run 2026-11-21). Everything else UE-side is uncompiled scaffolding until the owner's PC build.
- **Next honest milestone:** Phase 1 on the owner's PC — install UE 5.8.x, open `ue-project/Nexora.uproject`, build the 400 m test scene (migration plan Part I checklist).

Notes:
- UE5 work in this VM is docs + uncompiled code scaffolding only; first real UE build is Phase 1 on the owner's PC.
- Godot testbed: 8/8 tests pass, Windows exe built locally (not in git — 105 MB).
- Previous block (2026-11-21 ~00:24): `create_branch feat/unit-b-c` approval card timed out after two earlier attempts were cut by service restarts. Work was safe in local commit `6e736d2`; recovery was attempted in this run (see "Push block" section above) and is now recorded for the next run.
