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

- **G1 — Mission-state mapping.** `data/dialogue-lines.json` conditions use six mission states (`available`, `not_started`, `offered`, `accepted`, `objective_complete`, `completed`); `data/schema.sql` `mission_progress.status` allows four (`available`, `active`, `completed`, `failed`). No source maps one vocabulary onto the other, and no source defines the `progress` JSONB keys the sub-states would need. Until the mapping is defined, the nodes that depend on `offered` (`dlg_1_3_accept`, `dlg_1_3_decline`, `dlg_2_4_accept`, `dlg_2_4_decline`), `accepted` (`dlg_1_3_reminder`, `dlg_1_3_reminder_exit`, `dlg_2_4_progress`) and `objective_complete` (`dlg_1_3_return`, `dlg_2_4_return`) cannot be evaluated against the schema as written. **Resolved by Queue 10, Unit BA (GDD-15 §13):** the mapping table, the four `progress` keys, and the 12 evaluable nodes are defined there. `offered` is snapshot-local by design; abandon stays a recommendation (§13.5).
- **G2 — Favour availability.** `favour_available` is a condition in `data/dialogue-lines.json` (`dlg_topic_favour`, `dlg_topic_favour_none`) and GDD-04 §3 describes side-mission generation, but no `tools/sim` module generates side missions or reports whether one exists for an NPC. The favour topic cannot be evaluated from sim state. **Resolved by Queue 10, Unit BC (GDD-04 §3.1 + GDD-15 §15):** the generation contract and the `favour_available` evaluation rule are defined there. The favour offer/accept/complete nodes remain Phase 6 authoring work; find-a-lost-item and discovery favours are ungeneratable until their records are designed.
- **G3 — Debt flags.** The flags `owes_player` and `player_owes` are dialogue vocabulary (GDD-15 §1, §4) and `set_flag()` can store them, but no sim function derives them from `economy_ledger` loan rows and no sim code ever sets them. Whether the runtime derives them from the ledger or the economy maintains them is undefined. **Resolved by Queue 10, Unit BB (GDD-15 §14):** the read-only derivation rule (schema reason codes `loan_disburse` / `loan_repay`, character↔character rows only, system accounts excluded), derive-at-conversation-time, and the clearing rule (repayment only) are defined there. The sim/server reason-code drift (§14.4) still needs a Phase 9 alignment, and no character↔character loan exists yet to derive from (§14.5).
- **G4 — Which edge supplies the band.** `get_edge()` requires a `relation_type`, and GDD-01 §6.1 allows several directed edges between one pair (for example `spouse` and `colleague`). No source names which edge supplies the greeting band, `relationship_mean_min`, or `respect_min` when more than one exists.
- **G5 — `memory_write` is underspecified three ways.** `record_memory()` requires an `event_type` string and a `details` JSON object, but no source names the `event_type` for a conversation memory ("helped `<name>`", "met `<name>`"); no source gives the rule by which the runtime assigns a weight to a `memory_write` that carries none (only +40 for `dlg_1_3_return` is sourced); and no `memory_write` effect names whose memory it is — §12.4 assigns it to the speaking NPC, but the data carries no owner field. **Resolved by Queue 10, Unit BE (GDD-15 §16.3–§16.5):** the event-type table (2 sourced, 3 decided-here), the weight rule (weightless → 0, the schema default), and the `owner` field (`speaker` / `player`, default `speaker`) are specified there for the Phase 6 authoring pass.
- **G6 — No weight reduction.** `memory_weight_reduce` (`dlg_apology_accepted`, `amount_ref` `runtime_rule`) has no number in any source and no sim function: `tools/sim/memory.py` can append, read, and prune, but cannot change a stored `emotional_weight`. The reduction step and its size are both undefined. **Resolved by Queue 10, Unit BE (GDD-15 §16.1):** the step rule (toward zero, never across zero, never delete) and the target (strongest negative memory about the player) are defined there; the amount stays a runtime-rule parameter by design — no number is decided.
- **G7 — Goal proposal has no accept path.** `propose_goal` (`dlg_topic_goals_help`) may propose a stage goal, and `character_goals` supports `goal_kind` `stage` with status `active`, but no sim function proposes a goal or records the player's acceptance of one. The accept step is UE-side and undefined. **Resolved by Queue 10, Unit BE (GDD-15 §16.2):** the accept path (player-only choice, `character_goals` row write, stack-cap rule), the decline record (no row — effect `none`), and the required node restructure (the shipped node fires on entry with no choice) are defined there.
- **G8 — Current zone has no sim accessor.** GDD-06 §3 resolves location tokens to anchors from the live schedule instantiation, but no source read for this unit names a sim function returning an NPC's current zone at a given game time. The binding reads the zone from live schedule state; the headless sim exposes no single call for it.
- **G9 — Per-conversation drift cap.** GDD-15 §7 requires drift to be capped per conversation, but no source gives the cap's number. The shipped drift values are the only numbers the data carries (§12.4).
- **G10 — No mission deadlines.** GDD-15 §4 lets an NPC lead with a time-sensitive mission (deadline within 3 days), but no mission in `data/missions.json` carries a deadline field. That lead trigger cannot be evaluated from mission data today.

---

## 13. Mission-State Mapping (AV gap G1 — resolved)

**Unit BA · Queue 10 · Version 1.0 · 2026-11-22**
**Status:** DESIGN ONLY. This section defines the mapping gap G1 named: the six mission states `data/dialogue-lines.json` conditions use against the four `data/schema.sql` `mission_progress.status` allows. It adds no new state, no new table, and no schema change — the mapping is the deliverable. The mission system (Phase 6) implements against it; dialogue reads through it.

### 13.1 The two vocabularies

| Vocabulary | States | Source |
|---|---|---|
| Dialogue (`condition_vocabulary`, `mission`) | `available`, `not_started`, `offered`, `accepted`, `objective_complete`, `completed` | `data/dialogue-lines.json` `condition_vocabulary.mission` |
| Schema (`mission_progress.status`) | `available`, `active`, `completed`, `failed` | `data/schema.sql`, `CHECK (status IN ('available','active','completed','failed'))` |

The shipped data uses four of the six dialogue states (`available`, `offered`, `accepted`, `objective_complete` — 12 mission-condition nodes across the `1.3` and `2.4` trees). No shipped node conditions on `not_started` or `completed`; the mapping defines them anyway, so future trees can use the full vocabulary without re-opening this gap.

### 13.2 The mapping table

A dialogue state is evaluated from the `mission_progress` row for (player, mission id) — exactly the row §12.3 reads — plus the conversation snapshot (§12.1) for the one transient state. `progress` is the row's `JSONB` column (`data/schema.sql`, default `'{}'`).

| Dialogue state | Row state | Evaluation rule |
|---|---|---|
| `not_started` | **No row** | No `mission_progress` row exists for (player, mission). This defines §12.6 rule 5's exception: "no row" is a real state with a name, not an undefined case. A mission whose level is not yet reached has no row (GDD-15 §6: level gating is mission data), so it reads `not_started`. |
| `available` | `status = 'available'` | The row exists and its status is `available`. The mission may be offered. |
| `offered` | `status = 'available'` **+ snapshot-local `offered` flag** | The offer was shown in this conversation. `offered` is **not a stored key** — it lives only in the §12.1 snapshot. It becomes true when the offer node is entered (`dlg_1_3_offer`, `dlg_2_4_offer`) and is false again when the conversation closes. The accept/decline nodes are reachable only through the offer node's choices in the same conversation, so the snapshot flag is always set when their conditions are tested. Nothing persists the offer: the offer node's effects are `none` (`dialogue-lines.json`), and no stored flag may be invented for it. |
| `accepted` | `status = 'active'` **+** `progress.accepted_at_game_minutes` set **+** `progress.objectives_complete` is not `true` | The accept effect wrote the row to `active` (see §13.3). The mission is in progress and its objectives are not yet verified complete. |
| `objective_complete` | `status = 'active'` **+** `progress.objectives_complete = true` | The mission system verified the objectives against world state it owns (TECH-MULTIPLAYER §4) and set the flag. Dialogue never sets it: no shipped dialogue effect writes `objectives_complete`, and a dialogue line may not claim an objective is done. |
| `completed` | `status = 'completed'` | The `mission_complete` effect wrote the row to `completed` (§13.3). |
| *(no dialogue state)* | `status = 'failed'` | Failed missions have **no dialogue state**: every `mission` condition on a failed mission is false, and no node offers, reminds, or completes it. Retry returns the row to `available` through the mission system (GDD-04 §1: a failed mission can be retried after 7 in-game days); dialogue plays no part in the retry. |

### 13.3 The `progress` JSONB keys the sub-states need

Exactly four keys. No other `progress` key is defined by this mapping, and none may be added by improvisation — a key the mission system needs for another purpose is that system's own design, recorded where it is defined.

| Key | Type | Written by | When |
|---|---|---|---|
| `accepted_at_game_minutes` | integer | The mission system, on the accept effect | The player accepts (`mission_progress` effect, state `accepted` — see below). Absent means the mission was never accepted. |
| `objectives_complete` | boolean | The mission system, on objective verification | Set `true` when the mission system verifies the objectives against world state. Absent means `false`. Dialogue reads it, never writes it. |
| `completed_at_game_minutes` | integer | The mission system, on the `mission_complete` effect | The mission completes. Absent means the mission never completed. |
| `abandoned` | boolean | The mission system, on abandon — **recommendation only** (see §13.5) | Set `true` only if the abandon recommendation is adopted. Absent means `false`. |

There is deliberately **no `offered` key** (snapshot-local, §13.2) and **no per-objective array**: objectives are verified against world state (TECH-MULTIPLAYER §4), and a per-objective list in `progress` would be a second copy of world state that can disagree with it. The mission system may keep its own verification record elsewhere; it is not part of this mapping.

### 13.4 Effect mapping — what the dialogue effects write

The data's `mission_progress` effects use dialogue states as targets (`effect_vocabulary`: `state:<accepted|objective_complete>`). Each maps to a row write:

| Effect in the data | Row write |
|---|---|
| `mission_progress`, state `accepted` (shipped: `dlg_1_3_accept`, `dlg_2_4_accept`) | `status` → `'active'`; `progress.accepted_at_game_minutes` → current `game_minutes`. This is the only dialogue write that changes `status`. |
| `mission_progress`, state `objective_complete` (no shipped effect uses this target today) | `progress.objectives_complete` → `true`; `status` stays `'active'`. Defined here so future data can target it; the objective check itself stays the mission system's (TECH-MULTIPLAYER §4). |
| `mission_complete` (shipped: `dlg_1_3_return`, `dlg_2_4_return`) | `status` → `'completed'`; `progress.completed_at_game_minutes` → current `game_minutes`; rewards paid verbatim from `data/missions.json` (§12.4). A `null` credit reward means no credit reward — never invent one. |
| Decline (shipped: `dlg_1_3_decline`, `dlg_2_4_decline`, effects `none`) | **No row write.** `status` stays `'available'`; the offer stays open (GDD-15 §5 worked example). |

Dialogue never writes `status = 'failed'` and never writes `status = 'available'`: failure and availability are the mission system's, not the conversation's.

### 13.5 Abandon — a recommendation, not a sourced rule

GDD-04 §1 says a mission can be abandoned for a reputation cost, but no source gives abandon a status: the schema has no `abandoned` status and dialogue has no abandon state. This section **recommends** (it does not claim a source for) the handling the mission system should adopt: abandon sets `status = 'failed'` with `progress.abandoned = true`, the reputation cost is applied by the mission system per GDD-04 §1, and retry after 7 in-game days returns the row to `'available'`. Until the mission system adopts it, abandon is undefined behaviour and no dialogue node may offer it.

### 13.6 Which nodes become evaluable

With this mapping, all 12 mission-condition nodes in the shipped data evaluate against the schema as written (node → dialogue state → row state):

| Node | Mission | State | Row state |
|---|---|---|---|
| `dlg_1_3_offer` | `1.3` | `available` | `status = 'available'` |
| `dlg_1_3_accept` | `1.3` | `offered` | `status = 'available'` + snapshot `offered` |
| `dlg_1_3_decline` | `1.3` | `offered` | `status = 'available'` + snapshot `offered` |
| `dlg_1_3_reminder`, `dlg_1_3_reminder_exit` | `1.3` | `accepted` | `status = 'active'`, `objectives_complete` not `true` |
| `dlg_1_3_return` | `1.3` | `objective_complete` | `status = 'active'`, `objectives_complete = true` |
| `dlg_2_4_offer` | `2.4` | `available` | `status = 'available'` |
| `dlg_2_4_accept` | `2.4` | `offered` | `status = 'available'` + snapshot `offered` |
| `dlg_2_4_decline` | `2.4` | `offered` | `status = 'available'` + snapshot `offered` |
| `dlg_2_4_progress` | `2.4` | `accepted` | `status = 'active'`, `objectives_complete` not `true` |
| `dlg_2_4_return` | `2.4` | `objective_complete` | `status = 'active'`, `objectives_complete = true` |

Missions `1.3` ("Know Your Neighbours") and `2.4` ("A Friend in the City") both exist in `data/missions.json` with the objectives, rewards and unlocks the §12.2 worked traces quote. **Gap G1 is resolved by this section** — §12.8 G1 now reads as defined, not undefined — with two deliberate limits kept: the `offered` state is snapshot-local by design (it is never persisted), and abandon stays a recommendation (§13.5) until the mission system adopts it.

*End of GDD-15 §13 — Unit BA, Queue 10.*

---

## 14. Debt-Flag Derivation (AV gap G3 — resolved)

**Unit BB · Queue 10 · Version 1.0 · 2026-11-22**
**Status:** DESIGN ONLY. This section defines the derivation gap G3 named: how the dialogue flags `owes_player` / `player_owes` are derived from `economy_ledger` loan rows, and whether the runtime derives them or the economy maintains them. It adds no table, no column, and no sim code change — the derivation rule is the deliverable. The runtime (Phase 6) implements against it.

### 14.1 What the flags mean

The flags live on the NPC→player relationship edge (`relationships.flags`, GDD-01 §2.3; read at snapshot time per §12.1). They are **semantic memory of a debt between two people** — nothing else:

| Flag | Meaning |
|---|---|
| `owes_player` | The NPC owes the player money: the player lent to the NPC and the loan is not fully repaid. |
| `player_owes` | The player owes the NPC money: the NPC lent to the player and the loan is not fully repaid. |

A debt is a loan between two characters. It is **not** a bank loan, not household arrears, and not a missed rent: those are debts to system accounts or to a household pool, and no NPC's flag may ever be set by them (§14.3).

### 14.2 The derivation rule (read-only, over the ledger)

For a pair (NPC `X`, player `P`), evaluated over `economy_ledger` rows whose **both endpoints are characters** (`from_character_id` / `to_character_id` set, `from_business_id` / `to_business_id` NULL) and whose reason code is a loan code:

- `owes_player(X)` is true iff `SUM(loan_disburse, P → X) − SUM(loan_repay, X → P) > 0`
- `player_owes(X)` is true iff `SUM(loan_disburse, X → P) − SUM(loan_repay, P → X) > 0`

where `SUM(loan_disburse, A → B)` is the sum of `amount` over rows with `reason_code = 'loan_disburse'`, `from_character_id = A`, `to_character_id = B`, and `SUM(loan_repay, A → B)` is the same over `reason_code = 'loan_repay'`. Both sums are over **all** such rows ever written: the ledger is append-only (GDD-01 §8), so history is never rewritten and the sums are the outstanding balance by construction. The reason codes are the `data/schema.sql` codes (`loan_disburse`, `loan_repay`) — the server vocabulary, not the sim's (§14.4).

**When a flag clears:** when the outstanding sum reaches 0 — the loan is fully repaid. A partial repayment leaves the flag set: the flag is boolean and the amount is never shown (dialogue never states amounts — `dialogue-lines.json` notes; the settlement effect reads `amount_ref: ledger_debt_amount`). **No other clearing rule exists in any source:** there is no write-off, no expiry, and no forgiveness mechanic. A debt never clears except by repayment. That absence is recorded here as an open point for the mission/economy design, not filled in by this section.

### 14.3 What never sets the flags

| Ledger rows | Why they never set a flag |
|---|---|
| Bank loans (`SYS-BANK` ↔ character, kinds `bank_loan` / `mortgage` — `tools/sim/banking.py` `disburse_loan`, `monthly_repayments`) | The other party is the bank, a system account — not an NPC. A player who owes the bank does not owe any NPC, and an NPC who owes the bank does not owe the player. The derivation excludes every row with a system-account endpoint (`SYS-BANK`, `SYS-CITY`, `SYS-MARKET`, `SYS-EXTERNAL` and any later system account). |
| Household arrears repayments (e.g. `tools/sim/family_economy.py`, reason `debt_repayment`, head → `SYS-MARKET`) | The debt is a household's arrears to the market/city pool, not a loan between two people. The reason code is not a loan code, so the rule does not count it. |
| Business-endpoint rows (any row with `from_business_id` / `to_business_id` set) | A business's books are not a person's debt. The rule counts character↔character rows only. |
| Any other reason code (`wage`, `rent`, `purchase`, `tax`, `mission_reward`, …) | Only `loan_disburse` / `loan_repay` rows are loans. A rent row is rent, however overdue; it is not a loan and it sets no flag. |

### 14.4 Found discrepancy — the reason-code vocabulary drifts across stores

The derivation is written against the schema codes, but three wordings for the same acts exist today, and the server cannot ingest sim rows verbatim until they are aligned:

| Act | `data/schema.sql` (server) | Headless sim (`tools/sim/`) | `docs/GDD-03-ECONOMY-AND-PROFESSIONS.md` §8 |
|---|---|---|---|
| Loan disbursement | `loan_disburse` | `loan_disbursement` (`banking.py` `disburse_loan`); `mortgage_disbursement` (`decisions.py` mortgage path) | `loan` |
| Loan repayment | `loan_repay` | `loan_repayment` (`banking.py` `monthly_repayments`); `debt_repayment` (`family_economy.py`, arrears — not a loan) | `loan_repayment` |
| Debt settlement from dialogue | `loan_repay` (this section's ruling) | — (no dialogue settlement exists in the sim) | — |

The dialogue settlement effect names its reason `repayment` (GDD-15 §12.4; `dialogue-lines.json` `ledger_settlement`, `reason: "repayment"`). `repayment` is **not** a `schema.sql` reason code. This section rules: a settlement row written by the dialogue settlement effect carries `reason_code = 'loan_repay'` — the schema code for the act. The effect vocabulary's `repayment` is the effect's name for the settlement, not the ledger code. Likewise the sim's SQLite `economy_ledger` carries **no `CHECK` on `reason_code`** (`tools/sim/persistence.py` SCHEMA: `reason_code TEXT NOT NULL`, no list), which is how the drift arose: nothing in the sim enforces the schema list, and the sim today writes ~39 reason strings the schema `CHECK` would reject. Aligning the sim's loan strings to the schema codes is a Phase 9 data-alignment item for the server ingest; it is **not** decided here and no sim code is changed by this unit.

### 14.5 Where the loans come from — today, none

No sim module creates a character↔character loan row. The only loans the sim creates are bank loans (`banking.py`: `SYS-BANK` ↔ character, recorded in the sim-only `loans` table — `data/schema.sql` has **no `loans` table**, so on the server the ledger rows *are* the loan record and outstanding is derived by aggregation per §14.2, never by reading a loan balance). The only designed source of an NPC↔player loan is the GDD-04 §3 favour "lend money (ledger loan, GDD-03 §4.3)" — unimplemented; see GDD-15 §15 / GDD-04 §3.1. **Consequence, stated plainly: today both flags derive `false` for every NPC–player pair in the sim, and the debt tree (`dlg_topic_debt` and its 7 nodes) is reachable only once a favour loan — or a future mechanic — writes a character↔character loan row.** The tree is not broken; it is waiting on its input, like the favour topic (§15).

### 14.6 Derive at conversation time — the decision, and the rejected alternative

**Decision: derive at conversation time (read-only).** When a conversation opens, the runtime evaluates §14.2 once per NPC–player pair, from the ledger, and stores the result in the §12.1 snapshot. That derived value governs the whole conversation — the `debt` topic, the NPC-lead check (§12.2 step 3: `owes_player` set → the debt tree opens at `dlg_debt_npc_owes`), and every `flag` condition on these two flags. Nothing is written to `relationships.flags` by the derivation, and the derivation never creates or erases a debt (GDD-15 §4).

**Why not economy-maintained:** the alternative is for the economy to call `set_flag()` on the edge whenever a loan or repayment row lands. It is rejected for three reasons. (1) **One truth:** the ledger is the truth (GDD-01 §8); a stored flag is a second copy, and every second copy can drift — a missed maintainer path (bank, justice, favour, settlement) would leave a flag saying a debt exists after it was repaid, or absent while it is owed. (2) **No maintainer exists:** no sim module sets these flags today, and the loan paths are spread across banking, justice, decisions, family economy and the future favour generator — maintaining a flag from all of them is five integration points where derivation is one read. (3) **Cost is trivial:** one indexed aggregate per conversation open, over the `economy_ledger` indexes `schema.sql` already defines (`idx_ledger_from_char`, `idx_ledger_to_char`).

**Consequences for the shipped data (no data change needed):** the debt tree's `set_flag` effects (`dlg_debt_repay_now` sets `owes_player` `false`; `dlg_debt_player_pays` sets `player_owes` `false`) become no-ops under derivation — harmless, because the next derivation recomputes the same `false` from the settled ledger. The runtime **ignores stored debt flags** and derives; a stored `owes_player`/`player_owes` value left by an older write is never read. §12.1's snapshot table ("Semantic flags … from `relationships.flags`") is amended for these two flags only: they are derived from the ledger at snapshot time; every other flag still reads from the edge.

**Gap G3 is resolved by this section** — §12.8 G3 now reads as defined, not undefined — with the limits kept: the reason-code drift (§14.4) still needs a Phase 9 alignment, and no character↔character loan exists yet to derive from (§14.5).

*End of GDD-15 §14 — Unit BB, Queue 10.*

---

## 15. Favour Topic Note (AV gap G2 — resolved by contract)

**Unit BC · Queue 10 · Version 1.0 · 2026-11-22**
**Status:** DESIGN ONLY. This section is the dialogue-side note for the favour generation contract; the contract itself lives in `docs/GDD-04-MISSIONS-AND-PROGRESSION.md` §3.1 (Unit BC), which is the authoritative text. Nothing here duplicates it.

**How the topic evaluates.** `favour_available` (§12.3) is evaluated at conversation open, from the §12.1 snapshot, by the contract's rule (GDD-04 §3.1): the runtime runs the per-type eligibility checks in §3 table order (errands, work shifts, favours, events, discovery) and the flag is true iff at least one type is eligible for this NPC. The two shipped nodes follow it exactly: `dlg_topic_favour` (condition `favour_available: true`) and `dlg_topic_favour_none` (condition `favour_available: false`). No band, flag, or score condition is added to either node — the data conditions only on the flag, and the contract does not invent a second gate.

**What the topic does today — and what it does not.** The shipped favour topic is a stub in the honest sense: its lines and effects carry only a +1/0 relationship drift (`dlg_topic_favour`) or nothing (`dlg_topic_favour_none`). There is no favour offer / accept / complete node in `data/dialogue-lines.json`, so a favour offered through this topic today has nowhere to go after the line is shown. The accept flow — accept writes `mission_progress` under the instance key `side:<type>:<giver>:<generated_at_game_minutes>`, completion is verified against world state (TECH-MULTIPLAYER §4) — is a Phase 6 data addition built on the GDD-04 §3.1 contract. Two of the five types are ungeneratable until a record is designed (find-a-lost-item: no lost-item record; discovery: no discovery-progress record — GDD-04 §3.1); the generator must never offer them in the meantime. **Gap G2 is resolved by this note together with GDD-04 §3.1** — the evaluation rule now exists — while the favour flow remains Phase 6 authoring work.

*End of GDD-15 §15 — Unit BC, Queue 10.*

---

## 16. Dialogue Effect Functions (AV gaps G6 + G7 — resolved; G5 fixed)

**Unit BE · Queue 10 · Version 1.0 · 2026-11-22**
**Status:** DESIGN ONLY. This section defines the two effect functions no sim module supplies (§12.4: `memory_weight_reduce`, `propose_goal`) and records the three G5 underspecification fixes the data needs (`event_type` names, the weight rule for weightless `memory_write`, the memory owner field). It adds no sim code and does not rewrite `data/dialogue-lines.json` — the function contracts and the data fixes are the deliverable, specified here for the Phase 6 implementation and authoring pass. Where a number would be needed and no source gives one, the amount stays a parameter: this section does not decide it.

### 16.1 `memory_weight_reduce` — the step rule (gap G6)

**The function.** A new function in `tools/sim/memory.py` (the module that owns episodic memory — GDD-01 §2.3; §12.5), specified here for the Phase 6 implementation. Its contract:

- **Target selection.** The target is the harming memory: the strongest negative-weight episodic memory the speaking NPC holds about the player — `memories_about(NPC, player)` (§12.5: strongest first, `ABS(emotional_weight)` descending, then most recent), filtered to `emotional_weight < 0`, first row. The data names the target `harming_episodic_memory` (`dlg_apology_accepted`, `amount_ref: runtime_rule`). If no such memory exists, the effect is a no-op — but the apology accept node requires the `memory: harming_episodic_memory, exists: true` condition, so reaching the effect without a target means the condition was mis-evaluated, and the node's effects roll back per §12.4 rather than silently succeeding.
- **Step rule.** The weight moves toward zero by the amount, and never across zero: `new_weight = sign(weight) × max(0, |weight| − amount)`. A weight of −40 reduced by an amount of 15 becomes −25; reduced by an amount of 40 or more becomes 0. The row is **never deleted** (GDD-15 §4: the NPC remembers, but forgives) and the weight is never made positive by an apology: forgiveness reduces the harm, it does not manufacture fondness.
- **The amount stays a parameter.** The amount is supplied by the Phase 6 runtime rule (`amount_ref: runtime_rule` in the data). **No number is decided here** — no source gives one, and this unit does not invent one. The function takes `amount` as an argument; the data carries `amount_ref: runtime_rule`; the value the runtime passes is an owner-tunable rule for Phase 6 playtesting, not a fact this document fixes. Any future number must be recorded where it is set, with its source.
- **What a zero weight means.** A weight that reaches 0 stays stored as a forgiven memory with weight 0. It is not deleted by the reduction — but `prune()` (`memory.py`, retention priority `|weight|` aged by recency) will forget it first when the 200-row cap binds, because |0| has the lowest priority. That is the correct fate for a forgiven offence under GDD-01 §2.3 ("minor events are never stored indefinitely"): the NPC remembers it only until the cap needs the space.
- **Whose memory.** The reduction applies to the **speaking NPC's** memory only (see §16.4, the owner fix). The player's own memory of the same event — a separate row owned by the player, if one exists — is untouched: dialogue writes the speaker's and the player's rows, never a third party's (§7), and an apology does not rewrite the player's memory of what happened.
- **Transaction.** The apology accept node applies `memory_weight_reduce` + `set_flag(apologised_for_offence)` + drift +5/+5 as one transaction (§12.4): if any effect cannot be written, the whole node's effects roll back. One apology per offence: the flag gates repeats, and a second apology for the same offence is answered by `dlg_apology_repeat`, not by a second reduction.

**Gap G6 is resolved by this section** as a function question — the step rule, the target, and the parameter status now exist — while the amount itself remains a runtime-rule parameter by design.

### 16.2 `propose_goal` — the accept path (gap G7)

**The proposal.** `dlg_topic_goals_help` proposes the NPC's life goal as a **stage** goal for the player (`goal_ref: npc_life_goal` — the NPC's `character_goals` row with `goal_kind = 'life'`, GDD-01 §2.2). A proposed goal is always kind `stage`, never `life`: dialogue never silently replaces a life goal (GDD-15 §7).

**The accept path (designed here).** The player — and only the player — accepts, through a dialogue choice on the propose node:

1. **Accept choice.** On accept, the runtime inserts a `character_goals` row for the player: `character_id` = player, `goal_kind = 'stage'`, `goal_type` = the NPC life goal's `goal_type`, `target` = the NPC life goal's `target` plus `proposed_by` (the NPC's character id) and `proposed_at_game_minutes` (current game minutes), `status = 'active'`, `created_at_game_minutes` = current game minutes. The `goal_type` vocabulary is the NPC's own (`own_company | own_house | save_amount | reach_skill | marry | …` — `data/schema.sql` `character_goals` comment): no new goal type is invented for a proposal.
2. **The stack cap is enforced.** The player's goal stack holds at most 3 active goals — 1 life + up to 2 stage (GDD-01 §2.2). If the player already has 2 active stage goals, the accept choice is **not offered** — hidden, not greyed out, by the same rule that hides locked topics (GDD-15 §4). The proposal can still be heard; it cannot be accepted into a full stack.
3. **Completion is ordinary goal machinery.** An accepted proposed goal completes like any stage goal (GDD-01 §2.2: completing one pays out in reputation + a trait nudge and proposes the next) — through the goal system, not through dialogue. Dialogue proposes; it never completes a goal.
4. **Who accepts.** The player only, via the choice. The NPC never accepts a goal for the player, and no other character's goals are touched (§7: dialogue writes the speaker's and the player's rows only).

**What is recorded on decline.** On decline, **no `character_goals` row is written** — that is the point of "never silently applied". The decline itself is recorded as nothing: no flag, no memory row, no goal row. The effect on the decline choice is `none` (the data's explicit no-write vocabulary, §12.4). The NPC's life goal is unchanged, the topic stays available while the band stays `warm`, and the player may be proposed the goal again — bounded only by the 30-minute re-engagement cooldown (GDD-15 §2). The absence of a decline record is deliberate, not an oversight: a proposal the player refused leaves no trace in the goal stack, and the only thing that could stop a re-proposal is the cooldown.

**Required data fix (Phase 6 authoring pass — specified here, not applied to the file by this unit).** The shipped node fires the proposal on entry with no player choice: `dlg_topic_goals_help` has `choices: []` and carries the `propose_goal` effect on both its line and its node, so entering the node proposes the goal immediately — which contradicts GDD-15 §7 ("the player accepts it into the goal stack or not"). The node must be restructured before the accept path can run: (a) the `propose_goal` effect moves off node entry and onto an **accept choice**; (b) a **decline choice** is added with effect `none`, returning to the topic menu; (c) the node's line becomes the proposal itself (the NPC stating the goal and asking), with no effect. The choice labels are authoring for the Phase 6 pass (they must be written, not generated — GDD-15 §5); this section fixes only their structure and their effects, not their words. Until the restructure lands, the accept path in this section has no node to run on — recorded here as the data's current state, not papered over.

**Gap G7 is resolved by this section** as an accept-path question — the row write, the cap rule, the accepter, and the decline record now exist — with the node restructure outstanding as specified Phase 6 authoring work.

### 16.3 G5 fix 1 — `event_type` names for conversation memories

`record_memory()` (`tools/sim/memory.py`) requires an `event_type` string, but no source named the event type for a conversation memory. This fix gives every shipped `memory_write` effect its event type. Two names are **sourced**; three are **decided here** (labelled as this unit's data decision, following the snake_case vocabulary of the schema comment and the sim's event strings — `new_friend`, `partnership`, `marriage`, `conflict_resolved`).

| Memory text (shipped `memory_write`) | `event_type` | Provenance |
|---|---|---|
| `helped <name>` (weight +40, `dlg_1_3_return`) | `helped_by_player` | **Sourced** — `data/schema.sql` `character_memories` comment lists `helped_by_player` verbatim among its examples. |
| `Memory event: friendship with <name>` (`dlg_2_4_return`) | `new_friend` | **Sourced** — the sim's `record_memory()` callers use `new_friend` for a friendship memory (`tools/sim/`). |
| `<name> could not repay a debt yet` (`dlg_debt_npc_refuses`) | `debt_unpaid` | **Decided here** — no source names a debt event type. Follows the schema/sim snake_case pattern. |
| `player asked for more time to repay a debt` (`dlg_debt_player_wait`) | `debt_deferred` | **Decided here** — no source names one. Same pattern. |
| `met <name>` (`dlg_topic_introduce` line — see note below) | `first_meeting` | **Decided here** — no source names one. (`met_player` is a *flag*, GDD-01 §2.3, not an event type, so the event needs its own name.) |

**Note on `met <name>`.** The shipped `dlg_topic_introduce` node carries a `memory_write` with text `met <name>` in the data as read for this unit — if the Phase 6 authoring pass finds the introduce memory recorded under a different text, the `first_meeting` name follows the memory, not the text: the table maps the *occasion* (first meeting), and the text is the authored line. **Rule from here on:** every `memory_write` effect must carry an `event_type` from this table (extended by future units the same way — sourced first, decided-here labelled when no source exists). A `memory_write` without an `event_type` is a data bug, caught by the authoring check — the runtime must never invent one. The `details` JSONB on the row carries the filled memory text (`details.text`, placeholders filled from live data) and the originating node (`details.node_id`).

### 16.4 G5 fix 2 — the weight rule for weightless `memory_write`

Eight of the ten shipped `memory_write` effects carry no `weight` (the four texts in §16.3 other than `helped <name>` — each appearing at node and line level). The rule, grounded in the schema rather than invented: **a `memory_write` with no weight stores `emotional_weight = 0`** — the `data/schema.sql` default (`emotional_weight SMALLINT NOT NULL DEFAULT 0`, and the sim's `character_memories` table likewise defaults to 0). The runtime passes `0` to `record_memory()`; it does not guess a weight and it does not reject the write. Consequence, stated plainly: weight-0 memories have the lowest retention priority under `memory.py` `_priority` (|0| aged by recency) and are forgotten first when the 200-row cap binds — a first meeting is remembered only until the cap needs the space, which matches GDD-01 §2.3 ("minor events are never stored indefinitely"). The only sourced weight in the shipped data remains **+40** (`dlg_1_3_return`, GDD-15 §5). No other number is introduced by this rule.

### 16.5 G5 fix 3 — the memory owner field

No shipped `memory_write` effect names whose memory it is; §12.4 assigns it to the speaking NPC, but the data carries no owner field. The fix: **the `memory_write` effect gains an explicit `owner` field** with two values — `"speaker"` (the speaking NPC — the §12.4 assignment, now explicit in the data) or `"player"` (the player's own memory of the conversation, where the data calls for it). Until the Phase 6 authoring pass adds the field, the runtime default is `"speaker"`, preserving §12.4 for the shipped data. The owner is always one of the two conversation parties — a `memory_write` naming a third party is a data bug (§7: dialogue writes the speaker's and the player's rows only).

**Gap G5 is resolved by this section** — the three underspecifications now have fixes (event-type table §16.3, weight rule §16.4, owner field §16.5) — specified here for the Phase 6 authoring pass, which applies them to `data/dialogue-lines.json`. This unit does not rewrite the data file: the fixes are design decisions recorded in this document, and the verification script checks the document states them and the data contains the effects they apply to.

*End of GDD-15 §16 — Unit BE, Queue 10.*

*End of GDD-15 v1.0 + Unit AV §12 (Queue 9) + Queue 10 §§13–16.*
