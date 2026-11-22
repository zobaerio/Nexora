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

- **Exact authored lines for every tree** — the tree *structure* and the worked examples are here; the full line library is Phase 6 authoring work, written against the §5 contract. That library now exists as authored data (Unit AO, 2026-11-22): `data/dialogue-lines.json` carries full line sets for the mission `1.3` neighbour-help tree, the mission `2.4` friendship tree, the debt tree, and the apology tree, plus the §4 topic set and small-talk lines for all 11 professions and all 10 zones. Every node and line carries its `condition` and `effects` per the §5 contract, and every reward quoted is verbatim from `data/missions.json`. It is authored data, not generated text — the runtime walks it, it never authors a line.
- **Voice acting, casting, or a voice pipeline** — text first (§8); a voice pass reads the same lines.
- **Localisation** — all strings are English design text (GDD-05 §11: a Bangla UI is a separate owner decision).
- **Multiplayer dialogue** — Phase 9: dialogue in a shared world is server-validated like any other state change (TECH-MULTIPLAYER §4); two players talking to the same NPC is a Phase 9 design question, not answered here.
- **The LLM layer** — optional, later, bounded by §9; no API, provider, or cost is chosen here.

*End of GDD-15 v1.0 — Unit AL, Queue 7.*

---

## 12. Dialogue Runtime Binding

**Unit AV · Queue 9 · Version 1.0 · 2026-11-22**
**Status:** DESIGN ONLY. This section binds the authored data in `data/dialogue-lines.json` (Unit AO) to live state at conversation time. It adds no new state, no new fields, and no sim code changes; Phase 6 implements against it. Where a binding needs an input no source supplies, the gap is named in §12.8 — it is not papered over.

### 12.1 The conversation-time snapshot

When a conversation opens (GDD-06 §2 `Converse`; GDD-15 §2), the runtime takes one snapshot of the §1 state for this NPC–player pair. Every condition in the conversation is evaluated against that snapshot, plus the effects the conversation itself has already applied — so a later node sees an earlier node's writes (for example, `dlg_1_3_intro` sets `met_player`, and the topic menu then drops `introduce`). Nothing outside the conversation mutates the snapshot while it runs: the NPC's schedule state is suspended (GDD-06 §2), and the rest of the district keeps living without touching this pair's rows.

| Input the runtime needs | Where it lives | How it is read |
|---|---|---|
| Greeting band | `relationships` (NPC→player edge), `trust`/`affection` | Mean of trust and affection, banded by GDD-15 §3 / `dialogue-lines.json` `greeting_bands` |
| Semantic flags | `relationships.flags` JSONB | `met_player`, `worked_with_player`, `employs_player`, `owes_player`, `player_owes`, `apologised_for_offence` (GDD-01 §2.3; GDD-15 §1) |
| Respect | `relationships.respect` on the same edge | Compared against `respect_min` (GDD-01 §6.2) |
| Episodic memories | `character_memories` rows for the NPC about the player | `tools/sim/memory.py` `memories_about()` — strongest first (GDD-01 §2.3; GDD-06 §6) |
| Goal stack | `character_goals` (1 life + up to 2 stage goals) | The NPC's life goal fills `<life_goal>` (GDD-01 §2.2) |
| Mission state | `mission_progress` row for (player, mission id) | See §12.3 and gap G1 — the dialogue states do not all exist in the schema |
| Employment | `employments` row with `ended_at_game_minutes IS NULL` | `profession_id` matches `data/professions.json` ids (GDD-01 §1) |
| Household | `household_members` row with `left_at_game_minutes IS NULL` | `has_household` (GDD-01 §5) |
| Current zone | The NPC's current anchor zone | One of the 10 zone ids (GDD-06 §3); see gap G8 |
| Tier / life stage | `characters.sim_tier`; stage derived from age | `full` / `scheduled` / `ambient` (GDD-01 §2, §3); child stage per GDD-06 §4.12 |
| Favour availability | Side-mission generator (GDD-04 §3) | See gap G2 — no sim module supplies it |
| Conversation cooldown | `relationships.last_interaction_at_game_minutes` | 30 in-game minutes (GDD-15 §2); mission-flagged topics bypass it |

### 12.2 The walk — how a line is selected

1. **Entry gate (GDD-15 §2).** The NPC must be Full or Scheduled tier and in an interruptible state (not `Sleep`, not a moving work sub-state). Ambient NPCs promote first (GDD-06 §5). A child routes to a guardian or refuses (GDD-06 §4.12, `dlg_topic_introduce_child`). The 30-minute cooldown applies unless the topic is mission-flagged.
2. **Greeting (GDD-15 §3).** The opening line is the band-matching line of the greeting nodes: `dlg_topic_greet` (bands `close`, `warm`, `neutral`), `dlg_topic_greet_wary` (`wary`), `dlg_topic_greet_hostile` (`hostile`). Full tier, `close` band, may open with the top episodic memory instead — the first row of `memories_about()` for this NPC about the player.
3. **NPC lead (GDD-15 §4), at most once.** Checked in this order: `owes_player` set → the debt tree opens at `dlg_debt_npc_owes`; a top-weighted episodic memory involving the player exists → the NPC opens with it; a time-sensitive mission (deadline within 3 days) → the mission offer opens. The third trigger cannot fire today — see gap G10. After the led topic resolves, the menu opens.
4. **Topic menu (GDD-15 §4).** Only topics whose unlock condition holds on the snapshot are listed; locked topics are hidden, never greyed out.
5. **Node entry.** A node is entered only if its `condition` holds (§12.3). Entering a node applies its effects (§12.4) before its lines render.
6. **Lines.** Every line in the node whose `condition` holds is shown, in file order, up to the 3-line maximum (GDD-15 §8). There is no random pick and no re-roll: the same snapshot always shows the same lines. Placeholders fill from existing data only — `<name>` from the speaking NPC's cast name, `<life_goal>` from the NPC's goal stack, `<current_work>` from the NPC's current work sub-state (GDD-06 §4), `<zone_name>` from the display name of the NPC's current zone (GDD-02 §2).
7. **Choices.** Only choices whose `condition` holds are shown. Following a choice jumps to its `next` node id and re-enters step 5. A node with no choices and `ends: false` returns to the topic menu; a node with `ends: true` closes the conversation.
8. **Close.** `say_goodbye` (`dlg_topic_goodbye`) writes the drift and any memory rows (§12.4); the cooldown starts from the drift write, which updates `last_interaction_at_game_minutes`.

**Worked trace — mission `1.3` "Know Your Neighbours" (GDD-04 §2, `data/missions.json`).** Neighbour, band `neutral`, `met_player` = false. Opening line: the `neutral` line of `dlg_topic_greet`. Inside the mission `1.3` tree, `dlg_1_3_intro` offers two choices: "I just moved in." → `dlg_1_3_offer`; "Nice to meet you." → `dlg_1_3_hello`, which greets and drifts slightly without offering the mission. The player picks `introduce` → `dlg_topic_introduce` sets `met_player`. The `mission_offer` topic lists mission `1.3` → `dlg_topic_mission_offer` → choice "Tell me about 'Know Your Neighbours'." → `dlg_1_3_offer` (condition: mission `1.3` state `available`; both lines show — the offer, then the reward quoted verbatim: no credits, +10 reputation with each neighbour met, +5 district reputation, unlocks the Neighbour favour system). Accept → `dlg_1_3_accept` (mission `1.3` state `offered` — see G1). Decline → `dlg_1_3_decline`; nothing is written and the offer stays open. While the mission is accepted, re-engaging the NPC enters `dlg_1_3_reminder` (and `dlg_1_3_reminder_exit`). On return with the objective complete → `dlg_1_3_return`: +10 trust / +10 affection drift, episodic memory "helped `<name>`" weight +40 (Full tier), mission `1.3` completes with the exact `missions.json` rewards.

**Worked trace — mission `2.4` "A Friend in the City" (GDD-04 §2).** Entry is the score itself: `dlg_2_4_entry` requires `relationship_mean_min` 40, matching the mission objective "Raise one friendship to 40+ (trust/affection)". Then `dlg_2_4_offer` (mission `2.4` state `available`) quotes the reward verbatim — no credits, +10 district reputation, a memory event, unlocks Friend favour missions. Accept → `dlg_2_4_accept`; progress → `dlg_2_4_progress`; return → `dlg_2_4_return` (memory event, mission complete). Decline → `dlg_2_4_decline`; defer → `dlg_2_4_later`. No separate quest-giver NPC type exists: any NPC whose scores qualify carries the mission (GDD-15 §5).

### 12.3 Condition evaluation

A `condition` object holds only if **every** key in it holds (AND). An absent `condition` means always true. The vocabulary is the one declared in `data/dialogue-lines.json` `condition_vocabulary`; each key maps to live state as follows.

| Condition key | Reads | True when |
|---|---|---|
| `always` | Nothing | Always |
| `band` | NPC→player edge, mean of trust and affection, banded per §3 | The computed band equals the named band |
| `band_min` | Same | The band is at least this warm, in the order `close` > `warm` > `neutral` > `wary` > `hostile` (inclusive) |
| `band_max` | Same | The band is at most this warm (inclusive) |
| `flag` | `relationships.flags` on the NPC→player edge | The named flag equals the stated value (`met_player`, `owes_player`, `player_owes`, `worked_with_player`, `employs_player`, `apologised_for_offence`) |
| `mission` | `mission_progress` row for (player, mission id) | The mission is in the named state — **see G1**: only `available` and `completed` exist in both vocabularies; `not_started`, `offered`, `accepted`, `objective_complete` have no defined evaluation against `data/schema.sql` as written |
| `relationship_mean_min` | Same edge, mean of trust and affection | Mean ≥ the number (e.g. 40 for `dlg_2_4_entry`, matching mission `2.4`) |
| `respect_min` | `relationships.respect` on the same edge | Respect ≥ the number |
| `employed` | `employments` | A current row exists (`ended_at_game_minutes IS NULL`) |
| `has_household` | `household_members` | A current row exists (`left_at_game_minutes IS NULL`) |
| `zone` | NPC's current anchor zone | Equals the named zone id (see G8) |
| `profession` | NPC's `profession_id` | Equals the named profession id |
| `memory` (`harming_episodic_memory`, `exists: true`) | `memories_about()` for the NPC about the player | At least one row has negative emotional weight (GDD-01 §2.3: weight −100..100; negative = harming) |
| `tier` | `characters.sim_tier` / derived life stage | Equals the named tier or stage (`full`, `child`) |
| `favour_available` | Side-mission generator (GDD-04 §3) | **See G2** — no sim module supplies this value |

**Band arithmetic.** The band uses the arithmetic mean of trust and affection on the NPC's outgoing edge toward the player (GDD-01 §6.2: behaviour reads the actor's outgoing scores). Thresholds are GDD-15 §3, stored as data in `dialogue-lines.json` `greeting_bands`: `close` ≥ 60, `warm` 20 to 59, `neutral` −19 to 19, `wary` −59 to −20, `hostile` ≤ −60. Respect is not part of the band — it gates work topics only (§3). A pair with no edge at all (first meeting, `met_player` = false) reads as `neutral` (§3).

**Zones and professions in the data.** The `ask_about_place` topic has one node per zone — `dlg_topic_place_market` (`d1_market`), `dlg_topic_place_oldtown` (`d1_oldtown`), `dlg_topic_place_riverfront` (`d1_riverfront`), `dlg_topic_place_midtown` (`d1_midtown`), `dlg_topic_place_civic` (`d1_civic`), `dlg_topic_place_education` (`d1_education`), `dlg_topic_place_industry` (`d1_industry`), `dlg_topic_place_park` (`d1_park`), `dlg_topic_place_transport` (`d1_transport`), `dlg_topic_place_uptown` (`d1_uptown`) — and small-talk lines exist for all 11 professions: `construction_worker`, `civil_engineer`, `doctor`, `teacher`, `police_officer`, `taxi_driver`, `chef`, `software_developer`, `shop_owner`, `business_owner`, `pilot`. Zone lines use only the contents GDD-02 §2 lists for that zone; profession lines use only the workplace and gameplay summary `data/professions.json` carries for that profession.

**Debt and apology trees.** The debt tree is entered through `dlg_topic_debt` and branches on the flags: `dlg_debt_npc_owes` → `dlg_debt_repay_now` (settles), `dlg_debt_npc_refuses` (cannot pay yet), `dlg_debt_wait` (player waits); `dlg_debt_player_owes` → `dlg_debt_player_pays`, `dlg_debt_player_wait`. The apology tree is entered through `dlg_topic_apologise`: `dlg_apology_open` requires band at most `wary` and a harming memory; `dlg_apology_accepted` reduces that memory's weight (see G6) and sets `apologised_for_offence`; `dlg_apology_refused` ends the attempt with drift; `dlg_apology_repeat` answers a second apology for the same offence; `dlg_apology_hostile` is the single hostile line and exit. Work topics live at `dlg_topic_work` / `dlg_topic_work_how`, goals at `dlg_topic_goals` / `dlg_topic_goals_help`, family at `dlg_topic_family` / `dlg_topic_family_meet`, favours at `dlg_topic_favour` / `dlg_topic_favour_none` (see G2).

### 12.4 Effect application

Effects are applied on node entry, in the order listed, as one transaction per node: if any effect cannot be written (for example the ledger rejects a settlement), the whole node's effects roll back and the node is treated as failed — the conversation returns to the topic menu with no partial write. Effects write only the speaker's and the player's rows, never a third party's (GDD-15 §7).

| Effect type | Engine call | Row written |
|---|---|---|
| `relationship_drift` | `tools/sim/relationships.py` `adjust_scores()` | Trust/affection/respect on the NPC→player edge, clamped to −100..100; symmetric relation types mirror to the return edge; `last_interaction_at_game_minutes` updates (this is what the §2 cooldown reads) |
| `set_flag` | `tools/sim/relationships.py` `set_flag()` | One key in `relationships.flags` JSONB on the NPC→player edge |
| `memory_write` | `tools/sim/memory.py` `record_memory()` | Appends to `character_memories` (Full tier only — `record_memory()` returns `None` for Scheduled/Ambient, so the effect is a no-op there and the rest of the node's effects still apply); cap 200, oldest low-weight forgotten first (`prune()`). Weight is carried only where a source gives one (+40 for `dlg_1_3_return`, GDD-15 §5) — see G5 |
| `memory_weight_reduce` | None exists | See G6 — `memory.py` can append and prune but cannot change a stored weight |
| `mission_progress` / `mission_complete` | The mission system's own functions (not dialogue code) | `mission_progress` rows; `mission_complete` pays the rewards verbatim from `data/missions.json` — mission `1.3`: credits `null`, +10 reputation `relationship_each_met`, +5 `district`; mission `2.4`: credits `null`, "Memory event", +10 `district`. A `null` credit reward means no credit reward — never invent one |
| `ledger_settlement` | The ledger's own functions only, reason `repayment` | Settles an existing debt; the amount is read from the ledger (`amount_ref` `ledger_debt_amount`) and is never stated in a line. Dialogue never creates or erases a debt (GDD-15 §4) |
| `propose_goal` | None exists | See G7 — a conversation may propose a stage goal; the player accepts it or not, never silently applied (GDD-15 §7) |
| `none` | Nothing | Explicitly no write (a decline, a refusal, a waiting answer) |

**Node effects vs line effects — the precedence rule.** `data/dialogue-lines.json` duplicates effects at node level and at line level (for example `dlg_1_3_return` and `dlg_debt_repay_now` carry identical lists in both places), so the runtime must not apply both. The rule is: **apply the effects of the lines actually shown; if none of the shown lines carries any effect, apply the node's effects. Never apply both.** This is consistent across the shipped data: `dlg_1_3_accept`, `dlg_1_3_return`, `dlg_debt_player_pays`, `dlg_topic_work`, `dlg_topic_goals_help` and `dlg_apology_accepted` all resolve to exactly one application; `dlg_1_3_intro` and `dlg_topic_greet` resolve through the node fallback (their shown lines carry no effects, or carry the per-band drift respectively); `dlg_topic_goodbye` applies the `close`-band line's +1 affection only when that line shows. A `memory_write` effect names no owner in the data (see G5); the binding writes it to the speaking NPC's `character_memories`.

**Drift discipline.** Drift amounts are data, per topic, small per GDD-01 §4 step 4 — big changes come only from events. The per-conversation drift cap GDD-15 §7 requires has no number in any source (see G9); until one is set, the shipped drift values (+1/+2 per line, +10/+10 only on mission `1.3` completion) are the cap in practice, because they are the only numbers the data carries.

### 12.5 What the Session 01/02 sim supplies

The headless sim is the reference implementation of the read and write functions this binding calls. The UE runtime reads the same tables (`data/schema.sql`); the sim's functions are the contract for *how*. Two tables the sim uses — `life_events` and `relationship_history` — have no `CREATE TABLE` in `data/schema.sql`; they exist only in the sim store, and the binding reaches them only through the sim functions below, never as schema tables.

**`tools/sim/memory.py` (Unit 03) — episodic memory, GDD-01 §2.3:**
- `record_memory()` — appends one `character_memories` row (Full tier only, otherwise `None`), clamps `emotional_weight` to −100..100, then enforces the cap.
- `memories_about()` — what a character episodically remembers about another person, strongest first (`ABS(emotional_weight)` descending, then most recent), default limit 5. This is the read behind the NPC-lead check (§12.2 step 3), the `close`-band memory greeting (§3), and the `memory` condition (§12.3).
- `recent_memories()` — top-weighted recent memories, default limit 10.
- `prune()` / `MEMORY_CAP` (200) — retention priority is |weight| aged by recency (halves roughly every 90 days); the least important rows are forgotten first.
- `log_life_event()` — the world's event log (`life_events`); memory is what an individual retains of it. Dialogue reads `character_memories`, never `life_events` directly.

**`tools/sim/relationships.py` (Unit 07; Session 02 Unit 01 history) — edges and semantic memory, GDD-01 §6:**
- `get_edge()` — one directed `relationships` row by (from, to, `relation_type`); scores trust/affection/respect −100..100, `flags` JSONB, `last_interaction_at_game_minutes`.
- `adjust_scores()` — the only drift writer; clamps, stamps the interaction time, mirrors symmetric types.
- `set_flag()` / `get_flag()` — semantic memory on the edge itself (GDD-01 §2.3).
- `history_of()` — the recorded history of a pair from `relationship_history` (formation, status changes).
- `add_edge()` / `weekly_drift()` — formation and slow settling between interactions; dialogue never calls them (formation is a life event, drift between conversations is the weekly tick, not a dialogue write).

**Read-only at selection time.** Steps 1–7 of §12.2 only read: `get_edge()`, `get_flag()`, `memories_about()`, and table reads for `mission_progress`, `character_goals`, `employments`, `household_members`, `characters`. Writes happen only through the §12.4 effect functions. The sim supplies **no** function that writes `mission_progress`, generates a side-mission favour, proposes a goal, reduces a memory weight, or derives a debt flag from the ledger — those are the gaps in §12.8, and the sim must not be credited with them.

### 12.6 Fallback — when no line's condition matches

Deterministic, in order:

1. **No line in the node matches.** The node contributes no line and applies no effects. Control returns to the topic menu. If the node had `ends: true`, the conversation closes through `dlg_topic_goodbye` instead — a conversation never ends mid-node on silence.
2. **No choice matches.** The node's matching lines show, then control returns to the topic menu. A choice list that is empty after filtering is the same as no choices.
3. **No topic is available.** `say_goodbye` (`dlg_topic_goodbye`) is always available, so the menu always has at least one entry.
4. **The greeting cannot fail.** A pair with no edge reads as band `neutral` (§12.3), and all five bands have a greeting node (`dlg_topic_greet`, `dlg_topic_greet_wary`, `dlg_topic_greet_hostile`). A first meeting always has a line.
5. **No `mission_progress` row exists.** Every `mission` condition that requires a row state is false. (`not_started` is the exception in name only — its evaluation is part of G1 and is undefined until the mapping exists.)
6. **No randomness anywhere.** The same snapshot and the same data always produce the same lines, in the same order. If a line is missing, that is a data bug to fix in `dialogue-lines.json`, not a case for the runtime to improvise — the runtime never authors a line (GDD-15 §5).

### 12.7 What dialogue can never change — and the LLM position

Restated from GDD-15 §7 and §9, because the binding must enforce it, not just quote it:

| Dialogue can never change | Authority |
|---|---|
| Currency balances directly | GDD-01 §8: only the server (Phase 9) / the single-player authority writes ledger rows. A dialogue line cannot mint, move or erase credits except through the ledger functions in §12.4 (`mission_reward`, `loan`, `repayment` reason codes) |
| Property ownership / tenancy | GDD-01 §8. A conversation can start a purchase; the transaction is a server-validated ledger + property write and can still fail |
| Reputation beyond the mission rules | Only via the GDD-04 reward table or the event rules |
| Another character's memories or goals | Dialogue writes the speaker's and the player's rows only |
| The world clock, weather, or season | Owned by the clock/weather/season systems; dialogue may comment on them, never set them |

**LLM (GDD-15 §9, restated).** An LLM, if ever built, may only *rephrase* an authored line within the same node (same facts, same offer, same price), only on nodes flagged `rephrase_ok`, only for Full-tier NPCs, only with the authored line as the fallback when the API is unavailable or the output fails validation. It may never invent a fact, offer, price, mission, debt, or relationship change; never speak for a Scheduled/Ambient NPC; never replace the topic menu with free text; never make a network call in the shipped single-player path. If the LLM is off, the game is identical — that is the test. **Honest note: no node in `data/dialogue-lines.json` v1.0 carries a `rephrase_ok` flag, so today zero nodes are eligible for rephrasing.** No API, provider, or cost is chosen here; those are owner decisions with money attached, deferred honestly.

### 12.8 Honest gaps

These are inputs the binding needs that no source supplies. They are recorded here so Phase 6 does not invent them silently. None of them blocks this design; each blocks the nodes that depend on it until it is resolved by data or by an owner decision.

- **G1 — Mission-state mapping.** `data/dialogue-lines.json` conditions use six mission states (`available`, `not_started`, `offered`, `accepted`, `objective_complete`, `completed`); `data/schema.sql` `mission_progress.status` allows four (`available`, `active`, `completed`, `failed`). No source maps one vocabulary onto the other, and no source defines the `progress` JSONB keys the sub-states would need. Until the mapping is defined, the nodes that depend on `offered` (`dlg_1_3_accept`, `dlg_1_3_decline`, `dlg_2_4_accept`, `dlg_2_4_decline`), `accepted` (`dlg_1_3_reminder`, `dlg_1_3_reminder_exit`, `dlg_2_4_progress`) and `objective_complete` (`dlg_1_3_return`, `dlg_2_4_return`) cannot be evaluated against the schema as written.
- **G2 — Favour availability.** `favour_available` is a condition in `data/dialogue-lines.json` (`dlg_topic_favour`, `dlg_topic_favour_none`) and GDD-04 §3 describes side-mission generation, but no `tools/sim` module generates side missions or reports whether one exists for an NPC. The favour topic cannot be evaluated from sim state.
- **G3 — Debt flags.** The flags `owes_player` and `player_owes` are dialogue vocabulary (GDD-15 §1, §4) and `set_flag()` can store them, but no sim function derives them from `economy_ledger` loan rows and no sim code ever sets them. Whether the runtime derives them from the ledger or the economy maintains them is undefined.
- **G4 — Which edge supplies the band.** `get_edge()` requires a `relation_type`, and GDD-01 §6.1 allows several directed edges between one pair (for example `spouse` and `colleague`). No source names which edge supplies the greeting band, `relationship_mean_min`, or `respect_min` when more than one exists.
- **G5 — `memory_write` is underspecified three ways.** `record_memory()` requires an `event_type` string and a `details` JSON object, but no source names the `event_type` for a conversation memory ("helped `<name>`", "met `<name>`"); no source gives the rule by which the runtime assigns a weight to a `memory_write` that carries none (only +40 for `dlg_1_3_return` is sourced); and no `memory_write` effect names whose memory it is — §12.4 assigns it to the speaking NPC, but the data carries no owner field.
- **G6 — No weight reduction.** `memory_weight_reduce` (`dlg_apology_accepted`, `amount_ref` `runtime_rule`) has no number in any source and no sim function: `tools/sim/memory.py` can append, read, and prune, but cannot change a stored `emotional_weight`. The reduction step and its size are both undefined.
- **G7 — Goal proposal has no accept path.** `propose_goal` (`dlg_topic_goals_help`) may propose a stage goal, and `character_goals` supports `goal_kind` `stage` with status `active`, but no sim function proposes a goal or records the player's acceptance of one. The accept step is UE-side and undefined.
- **G8 — Current zone has no sim accessor.** GDD-06 §3 resolves location tokens to anchors from the live schedule instantiation, but no source read for this unit names a sim function returning an NPC's current zone at a given game time. The binding reads the zone from live schedule state; the headless sim exposes no single call for it.
- **G9 — Per-conversation drift cap.** GDD-15 §7 requires drift to be capped per conversation, but no source gives the cap's number. The shipped drift values are the only numbers the data carries (§12.4).
- **G10 — No mission deadlines.** GDD-15 §4 lets an NPC lead with a time-sensitive mission (deadline within 3 days), but no mission in `data/missions.json` carries a deadline field. That lead trigger cannot be evaluated from mission data today.

*End of GDD-15 v1.0 + Unit AV §12 (Queue 9).*
