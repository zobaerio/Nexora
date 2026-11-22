# NEXORA — GDD-15: Dialogue & Conversation Design

**Unit AL · Queue 7 · Version 1.0 · 2026-11-22**
**Parent documents:** `NEXORA-MIGRATION-PLAN.md` Part C #17 (rule/State-Tree dialogue first; LLM optional, later) · `docs/GDD-01-LIFE-AND-DATA-MODEL.md` §2.2 (goals), §2.3 (memory), §6.2 (relationship scores) · `docs/GDD-04-MISSIONS-AND-PROGRESSION.md` + `data/missions.json` (mission/goal data that drives dialogue) · `docs/GDD-05-UI-AND-PANELS.md` §3 (interaction prompt), §4 (profile card), §9 (inputs) · `docs/GDD-06-NPC-BEHAVIOUR.md` §2 (`Converse` state), §5 (tiers & promotion), §6 (conversation & memory hooks) · `data/npc-schedules.json` (11 profession templates + 3 life-stage templates)
**Status:** DESIGN ONLY. No dialogue tree asset, no `WBP_Dialogue` widget, no dialogue runtime exists yet; nothing here claims an NPC has ever spoken a line. This document is the contract Phase 6 implements against.

> **Design law:** dialogue is *authored branching on memory*, never generated text. Every line an NPC can say is written by a designer, gated by conditions on data that already exists (relationship scores, semantic flags, episodic memories, mission state), and every choice the player can make writes a real row or it does not ship. The plan's Part C #17 rule is honoured in full: rule/State-Tree dialogue first; an LLM layer for key NPCs is optional, later, and — if it ever arrives — it may only *rephrase* lines this system already authorises, never invent new facts, offers or prices. The world must work fully offline with authored lines, so it never depends on an API to feel alive.

---

## 1. Where Dialogue Lives in the Machine

Dialogue is not a separate system bolted onto the NPCs. It is the *player-facing surface* of three systems that already exist:

| System | What dialogue reads | Source |
|---|---|---|
| Relationship edges | Directed trust/affection/respect scores (−100..100) + semantic flags (`met_player`, `worked_with_player`, `employs_player`, `owes_player`) | GDD-01 §6.2, §2.3 |
| Memory | Episodic rows (Full tier only, cap 200, weight −100..100) involving the player; goal stack (life goal + up to 2 stage goals) | GDD-01 §2.2, §2.3 |
| Missions & goals | Mission state (`mission_progress`), the player's goal stack, side-mission generators | GDD-04, `data/missions.json` |

The behaviour layer already reserves the shape: GDD-06 §2 defines the `Converse` interrupt state — the NPC's schedule state is *suspended*, not advanced, and resumes if its block is still current when dialogue ends. This document fills in what happens *inside* `Converse`. Nothing here changes the state machine, the tick, or any schedule template.

## 2. Initiation — Who Can Talk, When, and How

**Entry (GDD-06 §6, unchanged):** the player uses `IA_Interact` on a Full or Scheduled NPC in an interruptible state (not `Sleep`, not a moving work sub-state — no conversation with a taxi driver mid-fare-loop, no waking a sleeper). The HUD prompt reads `[F] — Talk to <name>` (GDD-05 §3 rule: never a bare "F"; the verb comes from the target).

| Tier | Initiation rule |
|---|---|
| **Full** (~25 named NPCs/district, Unit AN cast) | Talk any time they are interruptible. Full dialogue trees, episodic-memory lines, mission offers. |
| **Scheduled** (district residents with homes/jobs) | Talk any time they are interruptible. Topic dialogue (§4) + mission offers; no episodic lines (they have no episodic memory — GDD-06 §6). |
| **Ambient** (Mass crowd) | No dialogue pre-promotion. The first talk attempt triggers promotion (GDD-06 §5): one beat of "the stallholder looks up", then dialogue with a Scheduled NPC at their next anchor transition. The promotion itself is the conversation's first line — it is never silent. |
| **Child stage** (`child_school_day` template) | Never `Converse` alone with strangers (GDD-06 §4.12). The interact prompt on a child routes to a parent/guardian NPC where one exists ("Ask their mother"), or is refused with a line ("I'm not supposed to talk to strangers") where none is present. |

**Interrupt priority (GDD-06 §2 rule 3, restated for dialogue):** life event > weather (`SeekCover`) > player (`Converse`). A conversing NPC does not seek cover until the dialogue ends — the player is standing in the rain too. A dialogue in progress is never cut by a schedule block boundary; it ends by player choice, by the NPC's exit line, or by a life-event interrupt, and the NPC then transitions to the now-current block.

**Cooldown:** after a conversation ends, the same NPC cannot be re-engaged for 30 in-game minutes (one schedule-block granularity) except through a mission-flagged topic. This stops dialogue farming for relationship drift and stops the player from re-rolling a greeting band by spamming `F`.

## 3. Greeting Bands — The First Line Is a Read, Not a Script

The NPC's opening line is selected from the greeting band computed from the *player's outgoing* relationship edge to that NPC (GDD-01 §6.2: behaviour reads the actor's outgoing scores; here the actor is the NPC, so the NPC's outgoing edge toward the player). The band uses the mean of trust and affection:

| Band | Mean trust+affection | Opening behaviour |
|---|---|---|
| `close` | ≥ 60 | Warm personal greeting, first-name, may open with an episodic memory ("You saved my stall in the storm — I still owe you"). Full tier only for the memory line; Scheduled tier uses the warm form without it. |
| `warm` | 20 to 59 | Friendly greeting, topic menu opens with personal topics available. |
| `neutral` | −19 to 19 | Polite neutral greeting. This is the band for `met_player` = false (first meeting): a stranger's greeting, plus the introduction exchange (§5). |
| `wary` | −59 to −20 | Short, guarded greeting; personal topics locked; mission offers from this NPC are refused until the band improves. |
| `hostile` | ≤ −60 | Refusal to talk, or a single hostile line and exit. Service refusal is the concrete form (GDD-06 §6): a harmed NPC may refuse services or raise prices within the economy's rules. The player can still apologise through the `apologise` topic (§4) if one exists for the offence. |

**Thresholds are this document's decision** (GDD-06 names the five bands but sets no numbers). They are data, not code: the band table lives with the dialogue data so tuning it is a data edit. Respect is *not* part of the greeting band — respect gates work topics (a respected professional is asked for work; a disrespected one is not), not the hello.

## 4. Topics — What You Can Talk About

A conversation is a **topic menu**, not a free-text box. Topics unlock from the NPC's state; locked topics are hidden, never shown greyed-out (a greyed-out topic advertises content the player cannot reach and invites save-scumming to unlock it).

| Topic | Unlock condition | What it does |
|---|---|---|
| `greet` / small talk | Always (band ≥ `wary`) | One authored small-talk line chosen from the NPC's profession + current season/weather; writes `met_player` on first use; small relationship drift (GDD-01 §4 step 4). |
| `introduce` | First meeting (`met_player` = false) | Name exchange; writes `met_player` + an episodic row (Full tier) or semantic flag (Scheduled). The NPC's profile card becomes inspectable (GDD-05 §4) after this. |
| `ask_about_work` | NPC employed; respect ≥ 0 | The NPC describes their current work sub-state (GDD-06 §4) in one or two lines; may unlock a `work_shift` side mission (GDD-04 §3). |
| `ask_about_goals` | Band ≥ `warm` | The NPC states their current life/stage goal (GDD-01 §2.2); may unlock a favour side mission tied to that goal. |
| `ask_about_family` | Band ≥ `warm`, NPC has household | Household news from real household rows (a birth, a child's school day); never invents a relative. |
| `ask_about_place` | Always | One line about the NPC's current anchor/zone (GDD-02 zone ids); the line is authored per zone, not per NPC. |
| `mission_offer` | NPC is the giver of an available mission | Offers the mission (GDD-04): shows objectives + reward verbatim from `missions.json`; accepting writes `mission_progress`. See §6. |
| `favour` (errand / lend / mediate) | Side-mission generator has one for this NPC | Side missions from GDD-04 §3 (errands, favours, work shifts, events, discovery). Reward pattern is the GDD's, never negotiated in dialogue. |
| `debt` | Semantic flag `owes_player` or `player_owes` set | Debt collection / repayment: a repayment writes a ledger row through the economy (GDD-01 §8); a refusal writes a memory + relationship drift. Dialogue never creates or erases a debt — it only settles one the ledger already holds. |
| `apologise` | Band ≤ `wary` and a harming episodic memory exists | One authored apology exchange; on acceptance, the harming memory's weight is reduced (not deleted — the NPC remembers, but forgives) and the band re-computes. One apology per offence. |
| `say_goodbye` | Always | Closes the conversation; writes the drift + any memory rows (§7). |

**Topic selection by the NPC (not just the player):** when the player opens a conversation, the NPC may *lead* with a topic instead of the menu — if a mission they offer is time-sensitive (an in-game deadline within 3 days), if they owe the player money, or if a top-weighted episodic memory involves the player (GDD-06 §6). The NPC leads at most once per conversation; after the led topic resolves, the menu opens.

## 5. Dialogue Trees — Authored, Data-Driven, Mission-Linked

A dialogue tree is **data**, not code: a set of nodes, each with a speaker, authored lines, conditions on the §1 state, player choices, and effects that write real rows. The runtime (Phase 6) walks the tree; it never authors a line.

**Node shape (the contract for the data file Phase 6 adds):**

| Field | Meaning |
|---|---|
| `node_id` | Stable id, e.g. `dlg_1_3_neighbour_help` |
| `speaker` | `player` or the NPC's cast id (Unit AN) / profession template |
| `lines` | 1–3 authored lines; the runtime picks by condition, never at random from unrelated lines |
| `condition` | A test on §1 state (band, flag, memory weight, mission state, goal) — absent = always |
| `choices` | Player options, each with its own condition and `next` node |
| `effects` | Rows written on reaching the node: relationship drift, memory write, mission flag, `mission_progress` row, ledger row (only through the economy's own functions — see §7) |
| `ends` | Whether the node closes the conversation |

**Trees are driven by mission/goal data (GDD-04), not written beside it.** Every main mission that involves a person gets at least one tree; the tree's `condition` fields reference the mission id from `data/missions.json`, so a mission rename is a data edit and the tree follows.

**Worked example — mission `1.3` "Know Your Neighbours" (GDD-04 §2, `data/missions.json`):**

```
NPC (neighbour, band neutral, met_player=false)
  → introduce → "I'm <name>. I live two doors down — the blue door."
  → player: "I just moved in." → NPC offers help topic
  → NPC: "The market's that way — but my roof leaks and I can't climb.
           Could you carry these tiles up for me?"   [mission_offer 1.3]
  → player accepts → mission_progress 1.3 opened; NPC: "Thank you. Come
           back when it's done — I'll have tea ready."
  → player completes the task (world action, not dialogue) → return to NPC
  → NPC (mission_progress 1.3 objective complete): "You did it! The tea's
           on — you're a good neighbour." → effects: +10 relationship
           (each), +5 reputation (district), episodic memory "helped <name>"
           weight +40 (Full tier) · mission 1.3 completes
  → player declines → NPC: "No trouble — the tiles will wait."
           effects: no drift, no memory; the offer stays open
```

**Second example — mission `2.4` "A Friend in the City" (friendship 40+):** the tree's entry condition is the relationship score itself — the NPC greets in the `warm` band and the `ask_about_goals` topic offers the friendship mission; there is no separate "quest-giver" NPC type. Any NPC whose scores qualify can carry the mission; the mission data names the *condition*, not a person.

**Authoring rules:**
1. No node may reference a fact the data does not hold (no invented relatives, jobs, or debts).
2. No choice may promise a reward the mission data does not carry — rewards are quoted verbatim from `missions.json` (`rewards`/`unlocks` fields).
3. Every tree ends in a state the data can represent: mission accepted/declined/completed, relationship drifted, memory written, or nothing changed (and a tree that changes nothing is cut — GDD-06 §6).
4. Trees are written per *situation* (mission, goal, debt, offence), not per NPC — the Unit AN cast reuses them, so 25 NPCs share a small library of honest trees instead of each carrying bespoke fiction.

## 6. Mission Offers Through People

Missions reach the player through dialogue, not through a quest board alone (GDD-04 §2: the game offers missions matching the player's life goal first; GDD-06 §6: the NPC's goal stack drives the mission offers the mission system routes through people):

- **Main missions** (GDD-04 §2, ids `1.1`–`8.4` in `data/missions.json`): each mission's giver is a *condition* (a neighbour for `1.3`, a friend for `2.4`, a partner for `5.1`, a civic contact for `6.2`), resolved at runtime to a real NPC who satisfies it. The mission data never names a person who does not exist.
- **Side missions** (GDD-04 §3): generated from the simulation — an NPC with a need, a business short-staffed, a weather event. The generating system writes the offer into the NPC's topic list; dialogue is the delivery mechanism, not the generator.
- **Acceptance is a data write:** accepting writes `mission_progress` (schema `mission_progress`); declining writes nothing and leaves the offer open; abandoning costs reputation per GDD-04 §1. Dialogue never completes a mission — completion is verified against world state the server (or the single-player authority) owns (TECH-MULTIPLAYER §4).
- **Level gating is mission data, not dialogue data:** a mission whose level is not yet reached is never offered, and its giver's topic list does not contain it. The dialogue system does not know about levels; it asks the mission system what is available.

## 7. What Dialogue Can Change — and What It Never Changes

| Dialogue may change | Mechanism (the row it writes) |
|---|---|
| Relationship scores | Small drift per GDD-01 §4 step 4 (big changes only from events). Drift amounts are data, per topic, capped per conversation. |
| Semantic flags | `met_player`, `worked_with_player`, employment flags — on the relationship/employment rows themselves (GDD-01 §2.3). |
| Episodic memory (Full tier) | Appends to `character_memories` (cap 200, oldest low-weight forgotten first). Includes the player's own memories of the conversation where the weight justifies it. |
| Mission state | `mission_progress` rows (accept/complete via the mission system). |
| Goals | A conversation may *propose* a stage goal (GDD-01 §2.2); the player accepts it into the goal stack or not. Dialogue never silently replaces a life goal. |
| Employment | A job offer accepted in dialogue writes an `employments` row through the labour system (Session 04 machinery in the sim; the UE equivalent validates the vacancy exists). |
| Money | Only as a *settlement* of an existing debt or a mission reward — through the ledger's own functions, with a reason code (`mission_reward`, `loan`, `repayment`). |

| Dialogue NEVER changes | Why |
|---|---|
| Currency balances directly | GDD-01 §8: only the server (Phase 9) / the single-player authority writes ledger rows. A dialogue line cannot mint, move or erase credits except through the ledger functions above. |
| Property ownership / tenancy | Server authority (GDD-01 §8, TECH-MULTIPLAYER §4). A conversation can *start* a purchase (the NPC agrees to sell) — the transaction itself is a server-validated ledger + property write, and it can still fail (insufficient funds, a faster buyer). |
| Reputation beyond the mission rules | Reputation changes only via the GDD-04 reward table or the event rules. A flattering line does not buy reputation. |
| Another character's memories or goals | Dialogue writes the *speaker's* and the *player's* rows. It never edits a third party's memory. |
| The world clock, weather, or season | Those are owned by the clock/weather/season systems; dialogue may *comment* on them (small talk reads the preset) but never sets them. |

**Audit rule:** any dialogue effect that is not in the left-hand table is a design bug, caught by the acceptance checks (§10) — the tree's `effects` list is reviewed against this section, node by node.

## 8. UI Hookup (GDD-05)

Dialogue renders through the profile-card family (GDD-05 §1 rule 4: one card, learned once):

| Element | Design |
|---|---|
| **Header** | The NPC's `WBP_CharacterCard` (GDD-05 §10): name, profession + tier, residence city, derived class. The greeting band is shown as a tone word ("Warm", "Wary"), never as a raw score — the UI does not leak simulation internals (GDD-05 §4 Memories rule, generalised). |
| **Body** | The current node's lines, speaker-labelled. NPC lines in the NPC's voice colour; player choices as buttons. Maximum 3 lines visible per node; longer exchanges are multiple nodes. |
| **Choices** | Buttons, gamepad-navigable (GDD-05 §1 rule 5), Esc = `say_goodbye` (one Esc = one step back — GDD-05 §9; in dialogue, Esc closes the conversation, it never opens Pause mid-node). |
| **Topic menu** | A list, not a wheel: topic labels are plain verbs ("Ask about work", "Ask about family"). Locked topics are hidden (§4). |
| **Mission offer display** | Objectives + rewards quoted verbatim from `missions.json` (GDD-05 §6 mission detail rule) — the dialogue offer and the Mission Log show the same numbers, because they read the same data. |
| **Pause behaviour** | Panels pause nothing by default (GDD-05 §1 rule 3): life continues while the player talks. The NPC's schedule state is suspended (GDD-06 §2 `Converse`), but the rest of the district keeps living — a second NPC may walk past mid-conversation, and that is correct. |
| **Widget** | New: `WBP_Dialogue` (panel), parent `NexoraPlayerController`, binding the §5 node data + the §3 band + the §4 topic list. It reads through the dialogue runtime only — no widget reads the ledger or the relationship tables directly (GDD-05 §10 rule). |

**Voice:** Full tier — full face animation + lip-sync for dialogue lines (Phase 2 sheet §6). Scheduled tier — preset expressions + lip-sync. Ambient — no dialogue, no voice. No voice *acting* is designed here: lines are text first; any future voice pass reads the same authored lines, so a voiced line and its text can never disagree.

## 9. The LLM Question — Answered Once, Here

The migration plan (Part C #17) makes LLM dialogue *optional, later*. This document fixes what "later" may and may not do, so no future unit has to re-litigate it:

- **Allowed, if ever built:** an LLM that *rephrases* an authored line within the same node (same facts, same offer, same price), for variety across repeated small-talk. It runs only on nodes flagged `rephrase_ok`, only for Full-tier NPCs, only offline-approved content, and only with the authored line as the fallback when the API is unavailable or the output fails validation.
- **Never allowed:** inventing a fact, offer, price, mission, debt, or relationship change; speaking for a Scheduled/Ambient NPC (they have no episodic memory for an LLM to be faithful to); replacing the topic menu with free text; any network call in the shipped single-player path. If the LLM is off, the game is identical — that is the test.
- **Cost & moderation:** an LLM layer carries API cost, an online requirement, and moderation weight (plan Part C #17). Those are owner decisions with money attached, deferred honestly — this document designs the game so they are never needed.

## 10. Acceptance Checks (for Phase 6 implementation)

1. **Initiation:** every tier behaves per §2 — Full/Scheduled talk when interruptible, Ambient promotes first, a child routes to a guardian, a sleeping NPC cannot be talked to.
2. **Greeting bands:** five test NPCs with engineered relationship scores greet in the correct band; the band boundaries in §3 are data, and changing the data changes the greeting.
3. **Topic gating:** a topic whose condition is unmet is absent from the menu (not greyed out); meeting the condition mid-game (e.g. a debt appears) adds the topic on the next conversation.
4. **Mission flow:** mission `1.3` plays end-to-end through the §5 tree: offer → accept (`mission_progress` row exists) → complete in the world → return → completion lines + the exact GDD-04 rewards (+10 relationship, +5 reputation, memory weight +40). Declining writes nothing.
5. **No forbidden writes:** a scripted pass over every shipped tree's `effects` lists finds no ledger write except `mission_reward`/`loan`/`repayment`, no property write, no third-party memory write (§7 right-hand table is empty in the shipped data).
6. **UI:** the dialogue header is the same `WBP_CharacterCard` as the profile screen; the offer's rewards match the Mission Log to the credit; Esc closes the conversation in one step; the whole flow is gamepad-operable.
7. **Cooldown & resume:** re-engaging the same NPC within 30 in-game minutes is refused except for a mission-flagged topic; after dialogue ends mid-block, the NPC resumes the suspended state if its block is still current, else transitions to the now-current block (GDD-06 §2).
8. **Offline:** with no network, every dialogue in the shipped game plays identically (no LLM dependency — §9).

## 11. What This Document Deliberately Does Not Decide

- **Exact authored lines for every tree** — the tree *structure* and the worked examples are here; the full line library is Phase 6 authoring work, written against the §5 contract.
- **Voice acting, casting, or a voice pipeline** — text first (§8); a voice pass reads the same lines.
- **Localisation** — all strings are English design text (GDD-05 §11: a Bangla UI is a separate owner decision).
- **Multiplayer dialogue** — Phase 9: dialogue in a shared world is server-validated like any other state change (TECH-MULTIPLAYER §4); two players talking to the same NPC is a Phase 9 design question, not answered here.
- **The LLM layer** — optional, later, bounded by §9; no API, provider, or cost is chosen here.

*End of GDD-15 v1.0 — Unit AL, Queue 7.*
