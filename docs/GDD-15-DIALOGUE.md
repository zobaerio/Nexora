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

- **Exact authored lines for every tree** — the tree *structure* and the worked examples are here; the full line library is Phase 6 authoring work, written against the §5 contract. That library now exists as authored data (Unit AO, 2026-11-22): `data/dialogue-lines.json` carries full line sets for the mission `1.3` neighbour-help tree, the mission `2.4` friendship tree, the debt tree, and the apology tree, plus the §4 topic set and small-talk lines for all 11 professions and all 10 zones. Every node and line carries its `condition` and `effects` per the §5 contract, and every reward quoted is verbatim from `data/missions.json`. It is authored data, not generated text — the runtime walks it, it never authors a line. *(Update, Unit DM · Queue 17: the mission `1.4` river-at-dusk tree is authored too. Update, Unit DO · Queue 18: the mission `2.1` learn-the-trade tree is authored too.)*
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
| Semantic flags | `relationship_pair_flags` on the pair (GDD-15 §17.7 — pair-level store; the edge's `relationships.flags` holds edge-specific flags only, of which none is defined today) | `met_player`, `worked_with_player`, `employs_player`, `owes_player`, `player_owes`, `apologised_for_offence` (GDD-01 §2.3; GDD-15 §1) — the debt flags are derived from the ledger at snapshot time per §14, not read from any store |
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
| `flag` | `relationship_pair_flags` on the pair (GDD-15 §17.7) — the debt flags `owes_player` / `player_owes` are derived from the ledger at snapshot time per §14, not read from any store | The named flag equals the stated value (`met_player`, `owes_player`, `player_owes`, `worked_with_player`, `employs_player`, `apologised_for_offence`) |
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

**Debt and apology trees.** The debt tree is entered through `dlg_topic_debt` and branches on the flags: `dlg_debt_npc_owes` → `dlg_debt_repay_now` (settles), `dlg_debt_npc_refuses` (cannot pay yet), `dlg_debt_wait` (player waits); `dlg_debt_player_owes` → `dlg_debt_player_pays`, `dlg_debt_player_wait`. The apology tree is entered through `dlg_topic_apologise`: `dlg_apology_open` requires band at most `wary` and a harming memory; `dlg_apology_accepted` reduces that memory's weight (see G6) and sets `apologised_for_offence`; `dlg_apology_refused` ends the attempt with drift; `dlg_apology_repeat` answers a second apology for the same offence; `dlg_apology_hostile` is the single hostile line and exit. Work topics live at `dlg_topic_work` / `dlg_topic_work_how`, goals at `dlg_topic_goals` / `dlg_topic_goals_help`, family at `dlg_topic_family` / `dlg_topic_family_meet`, favours at `dlg_topic_favour` / `dlg_topic_favour_none` (see G2; the offer/accept/complete flow is §15.1).

### 12.4 Effect application

Effects are applied on node entry, in the order listed, as one transaction per node: if any effect cannot be written (for example the ledger rejects a settlement), the whole node's effects roll back and the node is treated as failed — the conversation returns to the topic menu with no partial write. Effects write only the speaker's and the player's rows, never a third party's (GDD-15 §7).

| Effect type | Engine call | Row written |
|---|---|---|
| `relationship_drift` | `tools/sim/relationships.py` `adjust_scores()` | Trust/affection/respect on the NPC→player edge, clamped to −100..100; symmetric relation types mirror to the return edge; `last_interaction_at_game_minutes` updates (this is what the §2 cooldown reads) |
| `set_flag` | `tools/sim/relationships.py` `set_pair_flag()` (GDD-15 §17.7 — pair-level store; the edge-level `set_flag()` stays for edge-specific flags only) | One key in `relationship_pair_flags.flags` on the pair |
| `memory_write` | `tools/sim/memory.py` `record_memory()` | Appends to `character_memories` (Full tier only — `record_memory()` returns `None` for Scheduled/Ambient, so the effect is a no-op there and the rest of the node's effects still apply); cap 200, oldest low-weight forgotten first (`prune()`). Weight is carried only where a source gives one (+40 for `dlg_1_3_return`, GDD-15 §5) — see G5 |
| `memory_weight_reduce` | None exists | See G6 — `memory.py` can append and prune but cannot change a stored weight |
| `mission_progress` / `mission_complete` | The mission system's own functions (not dialogue code) | `mission_progress` rows; `mission_complete` pays the rewards verbatim from `data/missions.json` — mission `1.3`: credits `null`, +10 reputation `relationship_each_met`, +5 `district`; mission `2.4`: credits `null`, "Memory event", +10 `district`. A `null` credit reward means no credit reward — never invent one |
| `ledger_settlement` | The ledger's own functions only, reason `repayment` | Settles an existing debt; the amount is read from the ledger (`amount_ref` `ledger_debt_amount`) and is never stated in a line. Dialogue never creates or erases a debt (GDD-15 §4) |
| `propose_goal` | No sim function yet — the data side is applied: the accept node `dlg_topic_goals_accepted` carries the effect (Unit BP); the runtime write is Phase 6 | See G7 — a conversation may propose a stage goal; the player accepts it or not, never silently applied (GDD-15 §7) |
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
- `set_flag()` / `get_flag()` — semantic memory on the edge itself (GDD-01 §2.3). Pair flags now go through the pair-level twins `set_pair_flag()` / `get_pair_flag()` (GDD-15 §17.7); the edge-level pair is kept for edge-specific flags only, of which none is defined today.
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
- **G2 — Favour availability.** `favour_available` is a condition in `data/dialogue-lines.json` (`dlg_topic_favour`, `dlg_topic_favour_none`) and GDD-04 §3 describes side-mission generation, but no `tools/sim` module generates side missions or reports whether one exists for an NPC. The favour topic cannot be evaluated from sim state. **Resolved by Queue 10, Unit BC (GDD-04 §3.1 + GDD-15 §15):** the generation contract and the `favour_available` evaluation rule are defined there. The favour offer/accept/complete nodes for the generatable types are authored in GDD-15 §15.1 (Queue 12, Unit BO); the lost-item and discovery nodes are authored in GDD-15 §15.2 (Queue 13, Unit BR) on the BL/BM records — all seven types now have nodes. The generator must still never offer a type whose eligibility input does not exist (§3.1).
- **G3 — Debt flags.** The flags `owes_player` and `player_owes` are dialogue vocabulary (GDD-15 §1, §4) and `set_flag()` can store them, but no sim function derives them from `economy_ledger` loan rows and no sim code ever sets them. Whether the runtime derives them from the ledger or the economy maintains them is undefined. **Resolved by Queue 10, Unit BB (GDD-15 §14):** the read-only derivation rule (schema reason codes `loan_disburse` / `loan_repay`, character↔character rows only, system accounts excluded), derive-at-conversation-time, and the clearing rule (repayment only) are defined there. The sim/server reason-code drift (§14.4) still needs a Phase 9 alignment, and no character↔character loan exists yet to derive from (§14.5).
- **G4 — Which edge supplies the band.** `get_edge()` requires a `relation_type`, and GDD-01 §6.1 allows several directed edges between one pair (for example `spouse` and `colleague`). No source names which edge supplies the greeting band, `relationship_mean_min`, or `respect_min` when more than one exists. **Resolved by Queue 11, Unit BF (GDD-15 §17):** the priority table over all 13 types (spouse first, `ex_partner` last), the selected edge supplies band/mean/respect/drift target/flags, and the priority order is this unit's labelled decision. The flag-visibility limit (§17.3) is resolved by design in §17.7 (Queue 13, Unit BV): flags move to a pair-level store, so a flag written on any edge is seen whichever edge is selected next — implementation is Phase 6 work.
- **G5 — `memory_write` is underspecified three ways.** `record_memory()` requires an `event_type` string and a `details` JSON object, but no source names the `event_type` for a conversation memory ("helped `<name>`", "met `<name>`"); no source gives the rule by which the runtime assigns a weight to a `memory_write` that carries none (only +40 for `dlg_1_3_return` is sourced); and no `memory_write` effect names whose memory it is — §12.4 assigns it to the speaking NPC, but the data carries no owner field. **Resolved by Queue 10, Unit BE (GDD-15 §16.3–§16.5):** the event-type table (2 sourced, 3 decided-here), the weight rule (weightless → 0, the schema default), and the `owner` field (`speaker` / `player`, default `speaker`) are specified there for the Phase 6 authoring pass.
- **G6 — No weight reduction.** `memory_weight_reduce` (`dlg_apology_accepted`, `amount_ref` `runtime_rule`) has no number in any source and no sim function: `tools/sim/memory.py` can append, read, and prune, but cannot change a stored `emotional_weight`. The reduction step and its size are both undefined. **Resolved by Queue 10, Unit BE (GDD-15 §16.1):** the step rule (toward zero, never across zero, never delete) and the target (strongest negative memory about the player) are defined there; the amount stays a runtime-rule parameter by design — no number is decided.
- **G7 — Goal proposal has no accept path.** `propose_goal` (`dlg_topic_goals_help`) may propose a stage goal, and `character_goals` supports `goal_kind` `stage` with status `active`, but no sim function proposes a goal or records the player's acceptance of one. The accept step is UE-side and undefined. **Resolved by Queue 10, Unit BE (GDD-15 §16.2):** the accept path (player-only choice, `character_goals` row write, stack-cap rule), the decline record (no row — effect `none`), and the required node restructure (the shipped node fires on entry with no choice) are defined there. **Restructure applied by Queue 12, Unit BP:** the node now carries the proposal as a line with no effect, the accept choice (hidden when the goal stack is full) targets `dlg_topic_goals_accepted`, and the decline choice targets `dlg_topic_goals_declined` — the sim function itself remains Phase 6, unimplemented.
- **G8 — Current zone has no sim accessor.** GDD-06 §3 resolves location tokens to anchors from the live schedule instantiation, but no source read for this unit names a sim function returning an NPC's current zone at a given game time. The binding reads the zone from live schedule state; the headless sim exposes no single call for it. **Resolved by Queue 11, Unit BG (GDD-15 §18):** the `current_zone_at()` contract reading the stored `instantiated_schedules` day, with the commute/`mobile` answers and the `tea_stall` store difference recorded. No sim function is added; the UE implements the same contract against live instantiation. The `tea_stall` store difference is now decided by Queue 12, Unit BQ (GDD-15 §21): the nearest stall's zone, with the scheduler change specified in §21.2 — and **implemented by Queue 13, Unit BS**: `scheduler.instantiate()` resolves the anchor at schedule time and stores it on the block (§21.2, §18.5).
- **G9 — Per-conversation drift cap.** GDD-15 §7 requires drift to be capped per conversation, but no source gives the cap's number. The shipped drift values are the only numbers the data carries (§12.4).
- **G10 — No mission deadlines.** GDD-15 §4 lets an NPC lead with a time-sensitive mission (deadline within 3 days), but no mission in `data/missions.json` carries a deadline field. That lead trigger cannot be evaluated from mission data today. **Resolved by Queue 11, Unit BH (GDD-04 §3.2 + GDD-15 §19):** the `deadline_days` field, the availability-based clock (`available_at_game_minutes`), the 3-day lead window, and the expiry-to-`failed` rule are defined there. Per-mission deadline values are now set by Queue 13, Unit BW (GDD-04 §3.2: 4.2 → 30 days, 6.2 → 45, 7.4 → 60; the other 29 missions carry none, each with a stated reason).

---

## 13. Mission-State Mapping (AV gap G1 — resolved)

**Unit BA · Queue 10 · Version 1.0 · 2026-11-22**
**Status:** DESIGN ONLY. This section defines the mapping gap G1 named: the six mission states `data/dialogue-lines.json` conditions use against the four `data/schema.sql` `mission_progress.status` allows. It adds no new state, no new table, and no schema change — the mapping is the deliverable. The mission system (Phase 6) implements against it; dialogue reads through it.

### 13.1 The two vocabularies

| Vocabulary | States | Source |
|---|---|---|
| Dialogue (`condition_vocabulary`, `mission`) | `available`, `not_started`, `offered`, `accepted`, `objective_complete`, `completed` | `data/dialogue-lines.json` `condition_vocabulary.mission` |
| Schema (`mission_progress.status`) | `available`, `active`, `completed`, `failed` | `data/schema.sql`, `CHECK (status IN ('available','active','completed','failed'))` |

The shipped data uses four of the six dialogue states (`available`, `offered`, `accepted`, `objective_complete` — 35 mission-condition nodes across the `1.3`, `1.4`, `2.1`, `2.2`, `2.3` and `2.4` trees). No shipped node conditions on `not_started` or `completed`; the mapping defines them anyway, so future trees can use the full vocabulary without re-opening this gap.

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
| `mission_progress`, state `accepted` (shipped: `dlg_1_3_accept`, `dlg_1_4_accept`, `dlg_2_1_accept`, `dlg_2_4_accept`) | `status` → `'active'`; `progress.accepted_at_game_minutes` → current `game_minutes`. This is the only dialogue write that changes `status`. |
| `mission_progress`, state `objective_complete` (no shipped effect uses this target today) | `progress.objectives_complete` → `true`; `status` stays `'active'`. Defined here so future data can target it; the objective check itself stays the mission system's (TECH-MULTIPLAYER §4). |
| `mission_complete` (shipped: `dlg_1_3_return`, `dlg_1_4_return`, `dlg_2_1_return`, `dlg_2_4_return`) | `status` → `'completed'`; `progress.completed_at_game_minutes` → current `game_minutes`; rewards paid verbatim from `data/missions.json` (§12.4). A `null` credit reward means no credit reward — never invent one. |
| Decline (shipped: `dlg_1_3_decline`, `dlg_1_4_decline`, `dlg_2_1_decline`, `dlg_2_4_decline`, effects `none`) | **No row write.** `status` stays `'available'`; the offer stays open (GDD-15 §5 worked example). |

Dialogue never writes `status = 'failed'` and never writes `status = 'available'`: failure and availability are the mission system's, not the conversation's.

### 13.5 Abandon — a recommendation, not a sourced rule

GDD-04 §1 says a mission can be abandoned for a reputation cost, but no source gives abandon a status: the schema has no `abandoned` status and dialogue has no abandon state. This section **recommends** (it does not claim a source for) the handling the mission system should adopt: abandon sets `status = 'failed'` with `progress.abandoned = true`, the reputation cost is applied by the mission system per GDD-04 §1, and retry after 7 in-game days returns the row to `'available'`. Until the mission system adopts it, abandon is undefined behaviour and no dialogue node may offer it.

### 13.6 Which nodes become evaluable

With this mapping, all 35 mission-condition nodes in the shipped data evaluate against the schema as written (node → dialogue state → row state): *(Correction, Unit DO · Queue 18: the section as written by Unit BA said 12 — that count was already wrong for its own trees (1.3 has 6 mission-condition nodes and 2.4 has 5, which is 11, not 12), and Unit DM never updated it when the 1.4 tree shipped. The count is now read from the data: 6 × 1.3, 6 × 1.4, 5 × 2.4, 6 × 2.1 = 23. Update, Unit EC · Queue 19: the 2.2 tree adds 6 more — 6 × 2.2 — for 29. Update, Unit EO · Queue 21: the 2.3 tree adds 6 more — 6 × 2.3 — for 35.)*

| Node | Mission | State | Row state |
|---|---|---|---|
| `dlg_1_3_offer` | `1.3` | `available` | `status = 'available'` |
| `dlg_1_3_accept` | `1.3` | `offered` | `status = 'available'` + snapshot `offered` |
| `dlg_1_3_decline` | `1.3` | `offered` | `status = 'available'` + snapshot `offered` |
| `dlg_1_3_reminder`, `dlg_1_3_reminder_exit` | `1.3` | `accepted` | `status = 'active'`, `objectives_complete` not `true` |
| `dlg_1_3_return` | `1.3` | `objective_complete` | `status = 'active'`, `objectives_complete = true` |
| `dlg_1_4_offer` | `1.4` | `available` | `status = 'available'` |
| `dlg_1_4_accept` | `1.4` | `offered` | `status = 'available'` + snapshot `offered` |
| `dlg_1_4_decline` | `1.4` | `offered` | `status = 'available'` + snapshot `offered` |
| `dlg_1_4_reminder`, `dlg_1_4_reminder_exit` | `1.4` | `accepted` | `status = 'active'`, `objectives_complete` not `true` |
| `dlg_1_4_return` | `1.4` | `objective_complete` | `status = 'active'`, `objectives_complete = true` |
| `dlg_2_1_offer` | `2.1` | `available` | `status = 'available'` |
| `dlg_2_1_accept` | `2.1` | `offered` | `status = 'available'` + snapshot `offered` |
| `dlg_2_1_decline` | `2.1` | `offered` | `status = 'available'` + snapshot `offered` |
| `dlg_2_1_reminder`, `dlg_2_1_reminder_exit` | `2.1` | `accepted` | `status = 'active'`, `objectives_complete` not `true` |
| `dlg_2_1_return` | `2.1` | `objective_complete` | `status = 'active'`, `objectives_complete = true` |
| `dlg_2_2_offer` | `2.2` | `available` | `status = 'available'` |
| `dlg_2_2_accept` | `2.2` | `offered` | `status = 'available'` + snapshot `offered` |
| `dlg_2_2_decline` | `2.2` | `offered` | `status = 'available'` + snapshot `offered` |
| `dlg_2_2_reminder`, `dlg_2_2_reminder_exit` | `2.2` | `accepted` | `status = 'active'`, `objectives_complete` not `true` |
| `dlg_2_2_return` | `2.2` | `objective_complete` | `status = 'active'`, `objectives_complete = true` |
| `dlg_2_3_offer` | `2.3` | `available` | `status = 'available'` |
| `dlg_2_3_accept` | `2.3` | `offered` | `status = 'available'` + snapshot `offered` |
| `dlg_2_3_decline` | `2.3` | `offered` | `status = 'available'` + snapshot `offered` |
| `dlg_2_3_reminder`, `dlg_2_3_reminder_exit` | `2.3` | `accepted` | `status = 'active'`, `objectives_complete` not `true` |
| `dlg_2_3_return` | `2.3` | `objective_complete` | `status = 'active'`, `objectives_complete = true` |
| `dlg_2_4_offer` | `2.4` | `available` | `status = 'available'` |
| `dlg_2_4_accept` | `2.4` | `offered` | `status = 'available'` + snapshot `offered` |
| `dlg_2_4_decline` | `2.4` | `offered` | `status = 'available'` + snapshot `offered` |
| `dlg_2_4_progress` | `2.4` | `accepted` | `status = 'active'`, `objectives_complete` not `true` |
| `dlg_2_4_return` | `2.4` | `objective_complete` | `status = 'active'`, `objectives_complete = true` |

Missions `1.3` ("Know Your Neighbours"), `1.4` ("The River at Dusk"), `2.1` ("Learn the Trade"), `2.2` ("Rainy Day Fund"), `2.3` ("The Market Run") and `2.4` ("A Friend in the City") all exist in `data/missions.json` with the objectives, rewards and unlocks the §12.2 worked traces quote. **Gap G1 is resolved by this section** — §12.8 G1 now reads as defined, not undefined — with two deliberate limits kept: the `offered` state is snapshot-local by design (it is never persisted), and abandon stays a recommendation (§13.5) until the mission system adopts it. *(Update, Unit DO · Queue 18: the 1.4 and 2.1 rows are added here — Unit DM authored the 1.4 tree without updating this table, and this unit corrects that as well as adding its own. The giver for 2.1 is a condition, not a person: a colleague in the player's profession — an NPC with an open `employments` row in the player's `profession_id`, with the `worked_with_player` pair flag set (GDD-15 §17.7) — resolved at runtime to a real NPC who satisfies it, per the §13.6 rule above. For 1.4 the giver is the riverfront tea-stall neighbour of the tree's fiction, likewise a condition, not a named person. Update, Unit EC · Queue 19: the 2.2 rows are added here, and the count is 29. The giver for 2.2 is a condition, not a person: a neighbour — an NPC joined to the player by a `neighbour` edge (the 1.3 fiction carries over) — resolved at runtime likewise. Update, Unit EO · Queue 21: the 2.3 rows are added here, and the count is 35. The giver for 2.3 is a condition, not a person: a neighbour — an NPC joined to the player by a `neighbour` edge (the 1.3 fiction carries over) — resolved at runtime likewise.)*

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

No sim module creates a character↔character loan row. The only loans the sim creates are bank loans (`banking.py`: `SYS-BANK` ↔ character, recorded in the sim-only `loans` table — `data/schema.sql` has **no `loans` table**, so on the server the ledger rows *are* the loan record and outstanding is derived by aggregation per §14.2, never by reading a loan balance). The only designed source of an NPC↔player loan is the GDD-04 §3 favour "lend money (ledger loan, GDD-03 §4.3)" — its loan instance is now defined in GDD-15 §20 (Unit BN, Queue 12): accepting the favour writes the `loan_disburse` row keyed to the favour instance, and repayment writes `loan_repay` rows against the same key. **Consequence, stated plainly: today both flags derive `false` for every NPC–player pair in the sim, and the debt tree (`dlg_topic_debt` and its 7 nodes) is reachable only once a favour loan — or a future mechanic — writes a character↔character loan row.** The tree is not broken; it is waiting on its input, like the favour topic (§15).

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

**What the topic does today — and what it does not.** The shipped favour topic was a stub in the honest sense: its lines and effects carried only a +1/0 relationship drift (`dlg_topic_favour`) or nothing (`dlg_topic_favour_none`), with no favour offer / accept / complete node — a favour offered through the topic had nowhere to go after the line was shown. The flow for the types the GDD-04 §3.1 contract makes generatable is now authored in §15.1 below (Unit BO, Queue 12) and extended to the two remaining types in §15.2 (Unit BR, Queue 13): all seven favour types now have offer / accept / complete nodes. **Gap G2 is resolved by this note together with GDD-04 §3.1** — the evaluation rule now exists — and the flow for every generatable type is authored in §15.1–§15.2. The generator must still never offer a type whose eligibility input does not exist (§3.1): the nodes do not make a favour generatable, the record does.

### 15.1 The favour flow — offer / accept / complete nodes (Unit BO · Queue 12 · 2026-11-22)

**Status:** DATA + DESIGN. The nodes live in `data/dialogue-lines.json` (favour topic); this section is their contract. It covers the types generatable under GDD-04 §3.1 as it stood before BL/BM — errands, work shifts, lend-money and mediate favours, events — and explicitly not find-a-lost-item or discovery, whose nodes follow on the BL/BM records.

**Two new condition keys** (`condition_vocabulary`, `data/dialogue-lines.json`; guarded by `tools/validate_data.py`):

| Key | Values | Reads |
|---|---|---|
| `favour_type` | `errands` \| `work_shifts` \| `favours_lend` \| `favours_mediate` \| `events` | The type of the favour the generator offered this conversation. The two `favours` sub-kinds share the §3.1 `favours` row and its reward pattern; they split here because their offer lines and their completion checks differ |
| `favour_state` | `none` \| `accepted` \| `objective_complete` \| `completed` | The state of this NPC's most recent favour instance with the player (by `generated_at_game_minutes`, latest wins), read through the instance's `mission_progress` row under the §13 mapping. `none` means no favour instance exists for this pair |

**The nodes** (favour topic, `data/dialogue-lines.json`; node order is the entry order — see the precedence rule below):

| Nodes | Condition | What happens |
|---|---|---|
| `dlg_favour_complete_<type>` (5) | `favour_type: <type>`, `favour_state: objective_complete` | The NPC confirms completion. Effect: `mission_complete` with `mission_id_ref: favour_instance` + `rewards_ref: favour_instance` — the reward paid is the one recorded on the favour instance (GDD-04 §3.1), never a number in the line |
| `dlg_favour_progress` | `favour_state: accepted` | A reminder that the favour is outstanding. No new offer is made while one is open (see precedence) |
| `dlg_topic_favour` (existing stub) | `favour_available: true` | Now carries one choice per type, each conditioned on `favour_type`, leading to that type's offer node. Only the matching choice shows (§12.2 step 7) |
| `dlg_favour_offer_<type>` (5) | `favour_available: true`, `favour_type: <type>` | The NPC offers the favour, quoting the §3 reward pattern verbatim for the type (errands "200-2,000 NCr + relationship", work shifts "Wage + reputation", lend/mediate "Relationship + small credits", events "Reputation + memory events"). Choices: accept → the accept node; "Not now" → `dlg_favour_decline` |
| `dlg_favour_accept_<type>` (5) | `favour_type: <type>` | Effect: `mission_progress` with `mission_id_ref: favour_instance`, state `accepted` — the runtime substitutes the §3.1 instance key (`side:<type>:<giver>:<generated_at_game_minutes>`) for the id. The row is created `active` with `accepted_at_game_minutes` (§13.3) |
| `dlg_favour_decline` (shared) | `favour_available: true` | Effect `none`. Reached only by choice from an offer node, never by topic entry (it sits after the offer stub in node order) |
| `dlg_topic_favour_none` (existing) | `favour_available: false` | Unchanged |

**Precedence — decided here (labelled as this unit's decision).** Topic entry evaluates nodes in file order and enters the first whose condition holds (the same "in file order" rule §12.2 step 6 states for lines): completion first, then the reminder, then a new offer, then none. So a favour that is ready to complete is completed before any new favour is offered, and no second favour is offered while one is outstanding — at most one non-completed favour instance per NPC–player pair. That makes `favour_state` unambiguous in practice (one instance to read), and it is the reason the decline node can sit safely after the offer stub: the stub always matches first on entry.

**The lend-money accept and the loan.** The lend accept node carries only the `mission_progress` effect — no ledger effect exists on it. The `loan_disburse` row is written by the mission system as the accept's ledger consequence (GDD-15 §20.1): lender = player, borrower = the NPC, amount = the favour's recorded amount, `transfer_key`/`event_ref` = the favour instance key. The funds check runs at accept time (GDD-04 §3.1): if the player cannot cover the principal, the accept node's effects roll back as one transaction (§12.4) — no `mission_progress` row and no loan row. The favour completes when the loan is fully repaid: the mission system sets `progress.objectives_complete` when the §14.2 outstanding reaches 0, and the complete node pays the recorded reward.

**What the lines never do.** No offer or complete line states an NCr amount — the errand pattern is quoted verbatim (one of the two NCr figures any line may carry, guarded by `validate_data.py`'s no-invented-amount check), and every other pattern names no number, except the discovery pattern, which is the second quotable NCr figure (§15.2). The exact amount inside a range is set at generation and lives on the instance and in the ledger, never in dialogue. A favour whose type has no offer node falls through to the offer stub with no matching choice — per §12.6 rule 2, control returns to the topic menu. That is the correct behaviour until their nodes are authored: the topic never improvises an offer it has no node for. (No type is in that position today: all seven types have nodes, §15.2.)

*End of GDD-15 §15 + §15.1 — Unit BC, Queue 10 + Unit BO, Queue 12.*

### 15.2 Lost-item + discovery favour nodes (Unit BR · Queue 13 · 2026-11-22)

**Status:** DATA + DESIGN. The nodes live in `data/dialogue-lines.json` (favour topic); this section is their contract. It authors the nodes Unit BO deferred — offer / accept / complete nodes for `find_a_lost_item` and `discovery` — now that the BL/BM records exist (GDD-04 §3.3 lost-item record, §3.4 discovery progress). Nothing here changes the §15.1 flow for the other five types: the precedence, the instance key, and the effect shapes are the same, and this section only adds the two types to them.

**Two new `favour_type` values** (`condition_vocabulary`, `data/dialogue-lines.json`; guarded by `tools/validate_data.py`):

| Value | §3.1 row it serves | Reward pattern quoted verbatim |
|---|---|---|
| `find_a_lost_item` | Favours — find a lost item (§3.3) | "Relationship + small credits" (the §3 `favours` pattern — the lost-item favour is a favours sub-kind, like lend and mediate) |
| `discovery` | Discovery (§3.4) | "500 NCr each + Explorer progress" (the §3 `discovery` pattern) |

**The nodes** (favour topic, `data/dialogue-lines.json`; node order follows §15.1 — completion first, then the reminder, then a new offer — and the new nodes sit with their own kind in §3 table order: the lost-item nodes after the mediate nodes, the discovery nodes last):

| Nodes | Condition | What happens |
|---|---|---|
| `dlg_favour_complete_find_a_lost_item`, `dlg_favour_complete_discovery` | `favour_type: <type>`, `favour_state: objective_complete` | The NPC confirms completion. Effect: `mission_complete` with `mission_id_ref: favour_instance` + `rewards_ref: favour_instance` — the reward paid is the one recorded on the favour instance (GDD-04 §3.1), never a number in the line |
| `dlg_favour_offer_find_a_lost_item` | `favour_available: true`, `favour_type: find_a_lost_item` | The NPC offers the favour, quoting the §3 favours pattern verbatim ("Relationship + small credits") and naming where the item went missing through `<lost_place_name>`. Choices: accept → the accept node; "Not now" → `dlg_favour_decline` |
| `dlg_favour_offer_discovery` | `favour_available: true`, `favour_type: discovery` | The NPC offers the favour, quoting the §3 discovery pattern verbatim ("500 NCr each + Explorer progress") and naming the unfound discoverable through `<discoverable_name>`. Choices: accept → the accept node; "Not now" → `dlg_favour_decline` |
| `dlg_favour_accept_find_a_lost_item`, `dlg_favour_accept_discovery` | `favour_type: <type>` | Effect: `mission_progress` with `mission_id_ref: favour_instance`, state `accepted` — the runtime substitutes the §3.1 instance key (`side:<type>:<giver>:<generated_at_game_minutes>`) for the id. The row is created `active` with `accepted_at_game_minutes` (§13.3) |
| `dlg_topic_favour` (existing stub) | `favour_available: true` | Gains one choice per new type, conditioned on `favour_type`, leading to that type's offer node — seven choices in §3 table order. Only the matching choice shows (§12.2 step 7) |

**Two new placeholders** (filled from the favour instance, never invented; documented in `data/dialogue-lines.json` `notes`):

| Placeholder | Filled from | When |
|---|---|---|
| `<lost_place_name>` | The favour instance's `lost_zone` (+ `lost_anchor` where set, GDD-04 §3.3) | The anchor display name + zone display name when `lost_anchor` is set (e.g. "the tea stall in Boro Bazar"); the zone display name alone when it is not. Anchor display names are the GDD-06 §3 token words ("tea stall", "market", "riverfront", …) — no new names are invented for them |
| `<discoverable_name>` | The favour instance's `discoverable_id` (GDD-04 §3.4) | The GDD-02 §4 landmark name for a District 1 landmark id (e.g. "The Clock Tower"); the `district2-blockout.json` name for a District 2 landmark id (e.g. "Northgate Tower"); "the terminal loop bus route" for `bus_route_terminal_loop` (GDD-07 §1) |

**The amount rule — the second NCr figure.** The discovery offer line carries "500 NCr each + Explorer progress" — the §3 pattern verbatim. It is the **second** NCr figure any dialogue line may carry (the first is the errand pattern, §15.1), and `validate_data.py`'s no-invented-amount check now allows exactly these two patterns verbatim. The lost-item offer names no amount: the §3 pattern for its type ("Relationship + small credits") names none, and the line states none. The exact amount inside a pattern is set at generation and lives on the instance and in the ledger, never in dialogue — as §15.1 already requires.

**Completion.** The lost-item favour completes when the item is handed back: the mission system sets `progress.objectives_complete` on the favour instance row when the `lost_items` row reaches `returned` (GDD-04 §3.3), and the complete node pays the recorded reward. *(Update, Unit DF · Queue 16: the sim-side transitions the mission system keys off now exist — `find_lost_item()` writes `found`, `return_lost_item()` writes `returned` and refuses an item never found, and `favour_objective_complete()` is the predicate (true iff status is `returned`); the mission system itself is still Phase 6 work.)* The discovery favour completes when the discovery is recorded: the mission system sets `progress.objectives_complete` when the `discovery_progress` row appears for the offered discoverable (GDD-04 §3.4), and the complete node pays the recorded reward — 500 NCr each + Explorer progress, the §3 pattern verbatim. Neither complete line states an amount.

**What the nodes do not change.** The generator's eligibility checks are unchanged (§3.1): the lost-item favour is offered only while a `lost` row exists for the giver — and no merged event writes a loss yet (GDD-04 §3.3), so the node exists but the generator still finds no row to offer from; the discovery favour is offered only while an unfound discoverable exists for the player's account. Photograph-the-district is generatable — the photo record exists (GDD-04 §3.5, Unit BY, Queue 14): a photograph writes the `photographs` row and the `discovery_progress` row together, so the discovery favour can complete by photographing the named landmark, and no new node is authored for it because the nodes above already offer, accept, and complete the discovery type. The §15.1 precedence (completion > reminder > offer, at most one non-completed favour per pair) covers the new types without change, because `favour_state` reads the most recent instance whichever type it is.

*End of GDD-15 §15.2 — Unit BR, Queue 13.*

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

**Data fix applied (Queue 12, Unit BP — 2026-11-22).** The restructure specified above is now in `data/dialogue-lines.json`: (a) the `propose_goal` effect moved off node entry and onto the accept path — the data format carries effects on nodes and lines, not on choices, so the accept *choice* targets an accept *node* (`dlg_topic_goals_accepted`) that carries the effect on entry, on its line and its node, per the shipped pattern; (b) a decline choice ("Not right now.") leads to `dlg_topic_goals_declined`, whose effect is `none`; (c) the help node's line is the proposal itself ("Take it on as one of your own? My goal is <life_goal> — having you in it would mean a lot."), with effect `none`. The choice labels are authored here ("I'll take it on." / "Not right now.") — written, not generated (GDD-15 §5). The accept choice carries the condition `goals_full: false` — a new condition key (`condition_vocabulary` + `tools/validate_data.py`), true when the player already holds 2 active stage goals (GDD-01 §2.2) — so the accept choice is hidden, not greyed out, when the stack is full, exactly as §16.2 requires. The sim function that writes the `character_goals` row remains Phase 6 (no sim code changed by this unit); the data side of the accept path now has a node to run on.

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

---

## 17. Edge Selection for the Greeting Band (AV gap G4 — resolved)

**Unit BF · Queue 11 · Version 1.0 · 2026-11-22**
**Status:** DESIGN ONLY. This section defines which relationship edge supplies the greeting band, `relationship_mean_min`, and `respect_min` when several directed edges exist between one NPC–player pair. It adds no table, no column, and no sim code change — the selection rule is the deliverable. The runtime (Phase 6) implements against it.

### 17.1 The problem

`get_edge(store, a, b, relation_type)` (`tools/sim/relationships.py`) requires a `relation_type`, and GDD-01 §6.1 allows several directed edges between one pair — a spouse who is also a colleague, a friend who is also an employer. §12.3 reads "the same edge" for the band, the mean, and respect without naming which one. The ambiguity is not theoretical: `adjust_scores()` called with no `relation_type` moves the scores on **every** edge from A to B, so an unscoped dialogue drift would warm the colleague edge when the greeting had read the spouse edge. Until this section, the binding had no edge to read and no edge to write.

### 17.2 The rule — one edge, by priority

At conversation open, the runtime selects exactly one NPC→player edge: the **highest-priority edge present**, by the table below. The table covers all 13 `relation_type` values GDD-01 §6.1 lists, so the selection is total — there is no pair of types the table cannot order, and no tie-break beyond the table is needed (one edge exists per (pair, type), so two edges never share a type).

| Priority | `relation_type` | Why it outranks what follows |
|---|---|---|
| 1 | `spouse` | The household bond; the pair's primary social frame |
| 2 | `partner` | The same household bond, unmarried |
| 3 | `best_friend` | The closest non-kin bond |
| 4 | `parent` | Kin — the family frame outranks work and acquaintance |
| 5 | `child` | Kin (in one direction only one of `parent`/`child` can exist, so their relative order never decides a real selection; the table is total anyway) |
| 6 | `sibling` | Kin — derived via shared parents, cached as an edge (GDD-01 §6.1) |
| 7 | `friend` | A live personal tie |
| 8 | `colleague` | A work tie |
| 9 | `employer` | A work tie in the authority direction |
| 10 | `employee` | A work tie in the subordinate direction |
| 11 | `acquaintance` | The weakest live tie |
| 12 | `rival` | Adversarial — never outranks a live bond, so a conflict does not reframe the pair |
| 13 | `ex_partner` | A former bond — last; it is read only when nothing live exists |

**The priority order is this unit's decision** (labelled as such): no source ranks the types. The principle behind it is the greeting's own nature (GDD-15 §3 — the first line is a read of the relationship, not a script): the greeting reads the relationship that defines the pair's primary social frame, most intimate first, adversarial ties last. A spouse who has become a rival after a conflict still greets as a spouse — the conflict lives in the spouse edge's scores, not in a switch of frame. The order is data, not code: it lives with the dialogue data so tuning it is a data edit, like the band thresholds (§3).

### 17.3 What the selected edge supplies

Everything §12.3 reads from "the same edge" now reads from the selected edge, and nothing else:

| Read / write | Source |
|---|---|
| Greeting band (§3) | Mean of trust and affection on the selected edge |
| `relationship_mean_min` (§12.3) | The selected edge's mean (e.g. 40 for `dlg_2_4_entry`) |
| `respect_min` (§12.3) | The selected edge's `respect` |
| Drift target (§12.4) | `adjust_scores()` is called with `relation_type` = the selected type — **never unscoped**. One conversation moves exactly the edge it read. Symmetric mirroring still applies: a symmetric selected type mirrors to the return edge of the same type, per `adjust_scores()` |
| Semantic flags (§12.1, §12.3 `flag`) | Read from and written to the selected edge (`get_flag()` / `set_flag()` take a type) |

**Honest limit — flags on a non-selected edge are invisible to dialogue.** Flags are pair facts, but the store holds them per edge, and the binding reads the selected edge only. A `met_player` written to the colleague edge while the spouse edge is selected is not seen by the next conversation. **Resolved by design in §17.7 (Unit BV, Queue 13):** flags move to a pair-level store, so a flag written on any edge is seen whichever edge is selected next. No sim code changes in this unit, so the move is specified here and the store changes when Phase 6 implements it; until then the limit stands as the sim's current behaviour, not as the decided rule. (The debt flags are the exception: they are derived from the ledger at snapshot time per §14, not read from any edge.)

### 17.4 No edge, no scores

- **No NPC→player edge at all** → band `neutral` (§12.3), the first-meeting greeting. The greeting never fails (§12.6 rule 4).
- **Selected edge exists with the sim's default scores** (an edge formed with 0/0/0) → `neutral`, exactly like no edge. A zero-score edge reads as a stranger's greeting, not as a special case.
- **The return edge is never read for the greeting.** GDD-01 §6.2: behaviour reads the actor's outgoing scores; the actor here is the NPC, so the NPC→player edge governs. The player→NPC edge is the player's view of the pair, not the NPC's greeting.

### 17.5 Worked examples

- **Spouse + colleague** (married co-workers): the `spouse` edge is selected. The greeting is the spouse's greeting; the `colleague` edge's scores are untouched by the conversation's drift, and a `respect_min` check reads the spouse edge's respect, not the colleague's.
- **Colleague + rival** (a workplace conflict, Session 02): the `colleague` edge is selected (priority 8 beats 12). The rivalry shows as low scores on the colleague edge — the band may read `wary` — but the pair is still framed as colleagues, and the apology tree (§12.3) still has its edge to work on.
- **`ex_partner` only**: the `ex_partner` edge is selected (priority 13, but the only edge). Its scores govern the band; there is no livelier frame to prefer.
- **No edge**: `neutral` greeting, then the introduction exchange (§5) writes `met_player` on the edge the next conversation selects — which, once formed, is the edge the formation event created (e.g. `acquaintance`).

### 17.6 What this section does not do

It does not merge scores across edges, create or delete edges, or change `adjust_scores()`'s unscoped behaviour for non-dialogue callers (the weekly drift and event writes keep their own rules — Session 02). It fixes only the dialogue binding's read and write target. **Gap G4 is resolved by this section** — §12.8 G4 now reads as defined, not undefined — with the priority order itself the one decision this unit makes, labelled in §17.2, and the flag-visibility limit of §17.3 resolved by design in §17.7 (Unit BV, Queue 13), awaiting Phase 6 implementation.

### 17.7 The fix — flags live on the pair (Unit BV · Queue 13 · 2026-11-22)

**Status:** DESIGN ONLY. This section designs the fix for the §17.3 limit: flags are pair facts stored per edge, so a flag written on a non-selected edge is invisible to the next conversation. It adds no sim code change and no schema change — the store, the accessors, and the migration are the deliverable, for Phase 6 implementation. Where a choice would be needed and no source gives one, the section decides it and labels the decision.

**The diagnosis.** Every semantic flag in the shipped vocabulary is a fact about the *pair*, not about one edge: `met_player` (the pair has met), `worked_with_player`, `employs_player`, `apologised_for_offence` — none of them is true of a spouse edge and false of a colleague edge of the same pair. Storing them per edge was a storage accident (the flags JSONB happens to sit on the `relationships` row), not a modelling decision: GDD-01 §2.3 defines semantic memory as "facts" about the pair, and no source ever says a flag belongs to one relation type. The debt flags (`owes_player`, `player_owes`) are the proof the model already knows this: they are derived from the ledger per pair (§14), never stored on an edge at all.

**The decision: a pair-level flag store.** Flags move out of the edge and onto the pair:

| Item | Design |
|---|---|
| New store (sim) | `relationship_pair_flags` table in the sim store: `(character_a_id TEXT, character_b_id TEXT, flags TEXT /* JSONB-shaped */, PRIMARY KEY (character_a_id, character_b_id))` — one row per unordered pair, ever |
| Canonical pair key | The two character ids in lexicographic order (`a < b` by string comparison — the sim's ids and the server's UUIDs both order as strings). The pair (X, Y) and the pair (Y, X) are the same row; the accessors canonicalise before every read and write |
| New accessors (`tools/sim/relationships.py`, Phase 6) | `get_pair_flag(store, a, b, key, default=None)` and `set_pair_flag(store, a, b, key, value)` — the pair-level twins of `get_flag()` / `set_flag()`, with the same signatures minus `relation_type` |
| What moves | All six stored semantic flags: `met_player`, `worked_with_player`, `employs_player`, `apologised_for_offence` — plus any future pair flag declared in GDD-01 §2.3. The debt flags do **not** move: they stay derived from the ledger (§14), never stored in either store |
| What stays | The `relationships.flags` JSONB column stays (no column is dropped — dropping a column is a breaking migration) but holds **only edge-specific flags**, of which none is defined today. A future edge-specific flag must be declared in GDD-01 §2.3 before any code writes it, and the pair store is never used for it |

**The migration (sim store + Phase 9 server schema, forward-only).** One row per unordered pair that carries any flag on any of its edges; the merge rule decides conflicts (two edges holding different values for the same key): for each key, the value from the edge with the latest `last_interaction_at_game_minutes` wins — the most recent write is the pair's current fact — and ties break by the §17.2 edge priority (spouse first). After the migration, the edge flags are deleted from `relationships.flags` (the values now live on the pair row) and the column holds only edge-specific flags. On the server the migration is the same shape as a forward-only `schema.sql` note (Appendix B pattern): create the table, backfill by the same merge rule, then stop writing pair flags to the edge — with no down-migration, and the pair rows kept as the audit evidence of what each pair knew. **No live rows exist to migrate today:** `set_flag()` has no sim callers (`tools/sim/*.py` — flags are written only by dialogue effects at runtime, in data), so the sim store holds no flags; the migration exists so the rule is correct for a live Phase 6/9 world that has accumulated edge flags by then.

**What changes for the §12.1 snapshot table.** The "Semantic flags" row changes: flags are read from the pair store once per pair at conversation open, not from the selected edge. Everything else the selected edge supplies is unchanged — band, mean, respect, and the drift target (§17.3 table) still read the selected edge, because scores *are* edge facts (a spouse's trust and a colleague's trust are genuinely different numbers, §17.1). Only the flags move, because only the flags are pair facts.

**What changes for the §17.3 read/write rules.** The `flag` condition (§12.3) reads the pair store; `set_flag` effects write the pair store. The edge-level `set_flag()` / `get_flag()` stay for edge-specific flags only, and no pair flag may be written through them after the move — a write that names a pair flag with a `relation_type` is a data bug, caught the same way §12.7's audit rule catches a forbidden dialogue write. The §12.4 precedence rule and the transaction rule are unchanged: the pair-store write is one effect in the node's single transaction, and it rolls back with the rest.

**The rejected alternative: union-read across edges.** Read the flag from *any* edge of the pair (true if set on any edge) and keep writing to the selected edge. Rejected for two reasons. (1) **Conflicts have no winner:** two edges can hold different values for the same key (`met_player` true on the spouse edge, false on the colleague edge after a later write), and a union-read needs a precedence rule plus a timestamp it does not have — the pair store has one value by construction. (2) **The model stays confused:** a pair fact smeared across edges is still stored in the wrong place, and every future reader must re-derive the union; the pair store fixes the home once, and every reader reads one row. Union-read is cheaper to implement and would have fixed the *visibility* symptom — this section records that honestly — but it does not fix the *home*, and the home is the bug.

**Implemented (Unit CA · Queue 14 · 2026-11-23).** The sim side of this design now exists: `tools/sim/persistence.py` creates the `relationship_pair_flags` table (`character_a_id`, `character_b_id`, `flags`, PK on the pair, `CHECK (character_a_id < character_b_id)`), and `tools/sim/relationships.py` implements `get_pair_flag()` / `set_pair_flag()` with lexicographic canonicalisation, plus a `PAIR_FLAGS` tuple naming the four stored flags. Existing worlds gain the table on next open (`CREATE TABLE IF NOT EXISTS` in `Store.__init__`); no rows exist to migrate — `set_flag()` has no sim callers, so the §17.7 merge rule has nothing to merge, and the migration note above stands for a live Phase 6/9 world that has accumulated edge flags by then. The §12.3 `flag` condition and the §12.4 `set_flag` effect already read/write the pair store in the binding tables, so no §12 change is needed: the binding now resolves against real functions. What stays Phase 6: the dialogue runtime that calls them, and the Phase 9 server-schema note (same table, same migration rule). *(Update, Unit DB · Queue 15: the server-schema note is now written — `docs/TECH-PERSISTENT-WORLD.md` Appendix C, proposed migration `004_relationship_pair_flags`, same table and same merge rule, no down-migration. What stays is only the dialogue runtime.)* Tests: `tools/sim/tests/test_relationships.py` proves the round-trip, the canonicalisation, the cross-edge visibility, and the separation from edge flags.

*End of GDD-15 §17.7 — Unit BV, Queue 13.*

*End of GDD-15 §17 — Unit BF, Queue 11.*

---

## 18. Current-Zone Accessor (AV gap G8 — resolved)

**Unit BG · Queue 11 · Version 1.0 · 2026-11-22**
**Status:** DESIGN ONLY. This section defines the accessor the binding reads for an NPC's current zone at a given game time — the input GDD-06 §3 leaves unnamed. It adds no sim function and no sim code change: the accessor is specified here against the schedule state the sim already stores, and the UE runtime (Phase 6) implements the same contract against live schedule instantiation. Where the stored state simplifies the truth, the simplification is recorded, not smoothed over. *(Update, Unit ED · Queue 19 · 2026-11-23: the sim implementation now exists — `tools/sim/lost_items.py` `current_zone_at()`, written for the hand-back fallback (GDD-04 §3.3, Unit DP): it reads the `instantiated_schedules` row for the day and returns the `zone` of the block containing the minute, exactly per §18.1 — never a re-instantiation. The design-only status above stands for the dialogue binding, which still reads the contract rather than calling the function.)*

### 18.1 The accessor contract

```
current_zone_at(store, character_id, game_minutes) -> zone id | None
```

| Step | Rule |
|---|---|
| 1. Day | `day_index = game_minutes // 1440` (1440 game minutes per day; Day 1 is index 0, a Monday — `tools/sim/scheduler.py`). |
| 2. Read the stored day | Read the `instantiated_schedules` row for (`character_id`, `day_index`) and parse its `blocks_json`. The engine writes one row per character per day it runs (`tools/sim/engine.py`), asserting the blocks cover exactly 1440 minutes. |
| 3. Find the block | The block with `start <= game_minutes < end` (starts/ends are absolute game minutes). Return its `zone` field. |
| 4. No row, no block | Return `None`. A day the engine has not run has no row, and a conversation at that time has no zone to read. |

The accessor **reads stored state; it never re-instantiates and never recomputes jitter.** Re-instantiation would need the day's needs, traits, and weather effects as they were at the tick — inputs the conversation does not hold — and would risk disagreeing with the day the engine actually ran. The stored day is the truth about where the NPC was scheduled to be.

### 18.2 Where the stored zone comes from

`scheduler.instantiate()` assigns every block a `zone` before the engine stores the day:

| Block `location` | Stored `zone` | Source |
|---|---|---|
| `home` | The NPC's `home_zone` (household property's district) | `scheduler.py` zone resolution; `engine.py` builds `home_zone` from the household's property |
| `workplace` | The NPC's `workplace_zone` (profession's workplace zone, `data/professions.json`) | Same |
| `riverfront` / `park` / `market` / `college` / `school` / `college_para` | `d1_riverfront` / `d1_park` / `d1_market` / `d1_education` / `d1_education` / `d1_education` | `scheduler.py` `LEISURE_ZONE` |
| `tea_stall` / `restaurant` | The zone of the nearest anchor of that type — `d1_market` or `d1_riverfront` for a tea stall, `d1_market` or `d1_uptown` for a restaurant | `scheduler.py` `resolve_service_anchor()` (Unit BS, Queue 13 — GDD-15 §21.2/§21.3; no `LEISURE_ZONE` entry, the answer is per-NPC) |
| `transit`, `mobile` | The NPC's `home_zone` | `scheduler.py` fallback: "local to home/work path" |

Two guarantees behind the accessor: `_normalise()` tiles the day — gaps become explicit `home`/`idle` blocks, so a block always contains the queried minute — and the engine asserts the day's blocks sum to 1440. A conversation therefore always finds a block for a stored day, and `None` means only "no stored day", never "a hole in the day".

### 18.3 Between anchors — commute (`transit`)

A `Commute` block (GDD-06 §2: the only state that moves an NPC between anchors) carries location `transit`, and its stored zone is the NPC's `home_zone` by the §18.2 fallback. The accessor returns that stored value — it does **not** substitute the commute's destination. Honest consequence: a commuting NPC reports the home zone, not the destination zone, so a `zone` condition on the destination is false mid-commute and the `ask_about_place` topic answers for the home zone. The commute's destination is not tracked as a position anywhere in the sim (a Scheduled NPC's position is derived from schedule + anchor graph on both sides — TECH-PERSISTENT-WORLD §2, "Never persisted"), so no truer answer exists to read. The UE runtime resolves `transit` the same way GDD-06 §3 specifies (nearest stop on the commute path) and reports that stop's zone; the sim's stored value and the UE's resolved value may differ for the same block, and the difference is a store difference, not a bug in either.

### 18.4 `mobile` — work that is movement

The taxi fare loop and the business owner's mobile block (GDD-06 §4.6, §4.10) carry location `mobile`, and the stored zone is again `home_zone` by the same fallback. The accessor returns it unchanged. No position is tracked mid-loop, so there is no zone to report beyond the stored one; a `zone` condition on any other zone is false while the NPC is mobile.

### 18.5 The `tea_stall` discrepancy — resolved by implementation

The sim's fallback used to map `tea_stall` to `home_zone`, but GDD-06 §3 resolves location tokens to anchors at spawn, and the authored line library places the tea stalls in Boro Bazar (`data/dialogue-lines.json`, `dlg_topic_place_market`: "the market hall, the shop units, the tea stalls"). Under the UE anchor resolution a tea-stall block would report `d1_market`; under the sim's stored blocks it reported `home_zone`. **Implemented by Queue 13, Unit BS (GDD-15 §21.2):** `scheduler.instantiate()` now resolves the `tea_stall` (and `restaurant`) anchor at schedule time and stores the anchor + its zone on the block, so the sim's stored answer is the anchor's zone and the two stores no longer disagree for these tokens. The `home_zone` fallback survives only for `transit` and `mobile` (§18.3–§18.4), where no anchor exists. Practical consequence for the shipped data: `dlg_topic_place_market` now fires for a tea-stall NPC whenever the nearest stall is in `d1_market` — the lines the authors wrote for those zones finally fire for the NPCs sitting in the tea stalls, instead of answering for wherever the NPC happens to live.

### 18.6 Off-schedule — there is no such time in the sim

"Off-schedule" has no meaning against stored days: blocks tile the day, gaps are explicit `home` blocks (§18.2), and the `OffDuty` state (GDD-06 §2 — a template with no block for the current time, e.g. the pilot, §4.11) resolves inside the schedule to `AtHome`/`Leisure` blocks the accessor reads normally. The only `None` case is §18.1 step 4: no stored row for the day. When the accessor returns `None`, every `zone` condition is false, no place node matches, and §12.6 rule 1 applies — the node contributes no line and control returns to the topic menu. The conversation never invents a zone.

### 18.7 What becomes evaluable

| Item | Now evaluable because |
|---|---|
| The `zone` condition (§12.3) | The accessor supplies the value it tests |
| All 10 `dlg_topic_place_*` nodes (`data/dialogue-lines.json`, `topics.ask_about_place.nodes`) | Each conditions on one zone id, and the accessor returns exactly one zone per conversation: `dlg_topic_place_market` (`d1_market`), `dlg_topic_place_oldtown` (`d1_oldtown`), `dlg_topic_place_riverfront` (`d1_riverfront`), `dlg_topic_place_midtown` (`d1_midtown`), `dlg_topic_place_civic` (`d1_civic`), `dlg_topic_place_education` (`d1_education`), `dlg_topic_place_industry` (`d1_industry`), `dlg_topic_place_park` (`d1_park`), `dlg_topic_place_transport` (`d1_transport`), `dlg_topic_place_uptown` (`d1_uptown`) |
| The `ask_about_place` topic (GDD-15 §4, unlock Always) | It now resolves to exactly one node — the current zone's — instead of being unevaluable. A `None` zone resolves to no node (§12.6 rule 1), not to a wrong one |
| The `<zone_name>` placeholder (§12.2 step 6) | Fills from the display name of the accessor's zone (GDD-02 §2) |

Small-talk lines are per profession, not per zone (`data/dialogue-lines.json` `small_talk.by_profession` / `by_zone` — the `by_zone` set is authored per zone, not selected by the accessor), so the accessor changes nothing there. The `zone` condition is the only condition this unit unlocks.

### 18.8 What this section does not do

It does not add a sim function, change `instantiate()`, or move the `tea_stall` fallback — those are sim changes for a later unit if the owner orders one. It does not give the accessor a memory: the zone is read fresh at conversation open into the §12.1 snapshot and is not re-read mid-conversation (the NPC's schedule state is suspended in `Converse`, GDD-06 §2). **Gap G8 is resolved by this section** as an accessor question — the function contract, the stored read path, and the between-anchors/off-schedule answers now exist — with the `tea_stall` store difference (§18.5) kept as a recorded limit.

*End of GDD-15 §18 — Unit BG, Queue 11.*

---

## 19. Mission Deadlines — Dialogue Note (AV gap G10 — resolved)

**Unit BH · Queue 11 · Version 1.0 · 2026-11-22**
**Status:** DESIGN ONLY. The dialogue-side note for mission deadlines; the field itself is defined in `docs/GDD-04-MISSIONS-AND-PROGRESSION.md` §3.2 (Unit BH), which is the authoritative text. Nothing here duplicates it.

**How the lead trigger evaluates.** GDD-15 §4 lets an NPC lead with a time-sensitive mission; §12.2 step 3 checks the three lead triggers in order (debt → memory → mission). The mission trigger fires when, at conversation open (§12.1 snapshot), the mission's state is `available` (per §13) **and** its deadline is set **and** `0 < remaining <= 4320` game minutes — the sourced "within 3 days" window (GDD-15 §4), 3 days × 1440 minutes. `remaining` is `available_at_game_minutes + deadline_days × 1440 − now`, per GDD-04 §3.2. The trigger opens the mission offer node (`dlg_1_3_offer`, `dlg_2_4_offer` pattern); after the led topic resolves, the menu opens, as §4 requires.

**What happens on expiry.** When `remaining <= 0`, the mission system — not dialogue — sets the row to `failed` (GDD-04 §1; §13.4: dialogue never writes `failed`). A failed mission has no dialogue state (§13.2): every `mission` condition on it is false, and no node offers, reminds, or completes it. Retry after 7 in-game days returns the row to `available` with a fresh `available_at_game_minutes` — a new deadline window, not a continuation of the expired one. Dialogue plays no part in the retry.

**Interaction with the §13 mapping.** The deadline adds no dialogue state: `available`, `accepted`, and `objective_complete` evaluate exactly as §13 defines, and the clock keeps running from availability whether the mission is accepted or not — accepting does not reset the client's deadline. A mission that expires while `accepted` fails the same way; its `accepted_at_game_minutes` stays on the row as the record of when it was taken up. Favours never carry a deadline (GDD-04 §3.1), so the lead trigger never fires for a favour. **Gap G10 is resolved by this note together with GDD-04 §3.2** — the field, the window, and the expiry now exist — and the per-mission values are now set (Unit BW, Queue 13: 4.2 → 30 days, 6.2 → 45, 7.4 → 60), so the lead trigger can fire for those three missions while their deadlines are within 3 days. The other 29 missions carry no deadline, and the trigger never fires for them.

*End of GDD-15 §19 — Unit BH, Queue 11.*

---

## 20. Character↔Character Loan Source (AV gap G3 follow-up — the loan the favour creates)

**Unit BN · Queue 12 · Version 1.0 · 2026-11-22**
**Status:** DESIGN ONLY. This section defines the loan instance GDD-15 §14.5 named as missing: the favour lend-money path is the only designed source of an NPC↔player loan, but no such loan existed yet, so both debt flags derived false and the debt tree waited. The loan instance is the deliverable — it adds no table, no column, and no sim code change; the favour generator and the mission system implement against it. Where a term would be needed and no source gives one, the section records the absence instead of inventing it.

### 20.1 What the loan is

A loan between two characters — the player and one NPC — created by accepting a lend-money favour (GDD-04 §3, §3.1). It is a pair of `economy_ledger` rows and nothing else: `data/schema.sql` has **no `loans` table**, so on the server the ledger rows *are* the loan record and the outstanding balance is derived by aggregation per §14.2, never by reading a loan balance. The sim's `loans` table (`tools/sim/banking.py`) holds bank loans only and never holds this loan.

| Row | Writer | Fields that matter |
|---|---|---|
| Disburse | The mission system, on the favour's accept | `from_character_id` = lender, `to_character_id` = borrower, `amount` = the favour's recorded amount, `reason_code = 'loan_disburse'`, `transfer_key` = the favour instance key, `event_ref` = the favour instance key |
| Repay | The dialogue settlement effect (§12.4), via the ledger's own functions | `from_character_id` = borrower, `to_character_id` = lender, `amount` = the amount repaid, `reason_code = 'loan_repay'` (per the §14.4 ruling — the effect vocabulary's `repayment` is the effect's name, not the ledger code), `transfer_key` / `event_ref` = the favour instance key |

The favour instance key — `side:favours:<giver_character_id>:<generated_at_game_minutes>` (GDD-04 §3.1) — is the loan's traceability spine: both rows carry it as `transfer_key` and `event_ref`, so the loan is traceable to the favour that created it, and the favour's `mission_progress` row and its loan rows share one key. A loan row whose `transfer_key` is not a favour instance key is not this loan.

### 20.2 Direction — the player lends, the NPC borrows

The §3.1 eligibility rule names the NPC in need — the NPC's household is in arrears, or the NPC has an active bank loan with at least one missed payment — so the designed direction is **player → NPC**: the player lends, the NPC owes, and the flag that sets is `owes_player` (§14.2). The reverse direction (an NPC lending to the player) has no eligibility rule in any source — no rule says when an NPC would offer the player money — so it is **not designed here**: the generator never offers it, and a favour that would create it is a generator bug. The debt tree's `player_owes` branch therefore waits on a future eligibility rule; it is not fed by this section.

### 20.3 Terms — what the favour's amount is, and what it is not

- **Principal.** The amount lent is the favour's recorded amount: the generator sets it at generation, inside the §3 pattern for the type ("Relationship + small credits"), and records it on the favour instance. Dialogue never states it (amounts live in the ledger; §12.4), and the player never haggles it (GDD-04 §3.1). "Small" is the pattern's own wording and is not quantified anywhere — no cap is sourced, and this section does not invent one: the amount is set at generation and recorded, and the only bound the generator must respect is the pattern.
- **Interest: none.** No source gives a person-to-person interest rate. The bank's 12% annual (GDD-03 §4.3) is the bank's price for its own money and does not transfer to a loan between two people. The loan is principal-only: what is repaid is what was lent, to the credit.
- **Due date: none.** Favours have no deadline (GDD-04 §3.1), so the loan has no due date, no instalment schedule, and no late fee. Repayment is one settlement through the debt topic (`ledger_settlement`, amount read from the ledger — `amount_ref: ledger_debt_amount`), or several partial settlements: each repayment is a `loan_repay` row, the outstanding is the §14.2 difference, and the flag clears when it reaches 0.
- **Funds check at accept.** The player's ability to pay is checked at accept time (GDD-04 §3.1): the transaction validates funds when the mission system writes the disburse row. If the player cannot cover the principal, the accept node's effects roll back as one transaction (§12.4) — no `mission_progress` row, no loan row, and the conversation returns to the topic menu. The offer itself never checks funds; the offer is only words.

### 20.4 One outstanding loan per pair

**Decided here (labelled as this unit's decision):** the generator offers a lend-money favour to an NPC only when no outstanding character↔character loan exists between that NPC and the player — outstanding > 0 by the §14.2 derivation. The rule prevents debt stacking (a second loan on top of an unpaid first) and keeps the debt topic unambiguous: one open loan per pair, one flag, one settlement. No source states this gate; it is this unit's generator rule, and it joins the §3.1 eligibility row for lend-money as an additional gate, not a replacement for the arrears/missed-payment condition.

### 20.5 Missed repayment — what happens, and what does not

There is no due date, so there is no "missed" in the time sense: a loan that is not yet repaid is open, not overdue. **No enforcement is invented.** In particular: no interest accrues, no penalty is charged, no collector is sent, and no automatic deduction is taken — none of those mechanisms exists for a character loan in any merged system. What does exist, and is all that happens:

| Mechanism | What it does to an unpaid character loan |
|---|---|
| The §14.2 derivation | The `owes_player` flag stays set while the outstanding is > 0, and the debt topic stays available — the NPC keeps owing, visibly, until repaid |
| The debt topic (§12.3) | The player can raise it in any conversation; the NPC answers through the shipped debt nodes (`dlg_debt_npc_refuses` while they cannot pay, `dlg_debt_repay_now` when they settle) |
| Session 02 conflicts (`tools/sim/conflicts.py`) | An unpaid debt is a circumstance a conflict can cite, and a diagnosed conflict can be mediated — but no conflict is auto-created by a loan: the conflict system diagnoses from measured conflict levels, not from the ledger |
| Session 05 courts (`tools/sim/justice.py`) | A case reaches court only from a real dispute via the existing referral path (an escalated conflict, a referred default). A character loan reaches court only if a conflict over it escalates and is referred — the court does not take loan rows directly |

The bank-loan machinery is the contrast, not the model: `banking.py` `disburse_loan` lends only what SYS-BANK holds, assesses credit, charges interest, amortises monthly, records misses, defaults after three misses, and forecloses a mortgage — every one of those steps is a property of a bank loan, and none of it applies to a loan between two people. A character loan that is never repaid stays outstanding forever: the flag never clears except by repayment (§14.2 — no write-off, no expiry, no forgiveness mechanic exists), and that absence is recorded here as an open point for the mission/economy design, not filled in by this section.

### 20.6 What becomes true

With this section, the favour lend-money path has a defined loan: the accept writes a `loan_disburse` row keyed to the favour instance, the settlement writes `loan_repay` rows against the same key, and the §14.2 derivation reads both — so the first lend-money favour accepted in a live world makes `owes_player` derive true for the first time, and the debt tree (`dlg_topic_debt` and its 7 nodes) becomes reachable through a favour instead of waiting on a future mechanic. **Gap note:** §12.8 G3 stays resolved by §14 as a derivation question; this section resolves the *source* question G3's §14.5 left open — the loan now has a defined origin — while the loan itself still exists only once a favour is accepted in play. No sim code is changed, no bank rule is touched, and no NPC↔player loan row exists today.

*End of GDD-15 §20 — Unit BN, Queue 12.*

---

## 21. Service-Anchor Zone Resolution (AV gap G8 follow-up — the `tea_stall` decision)

**Unit BQ · Queue 12 · Version 1.0 · 2026-11-22**
**Status:** DESIGN ONLY. This section decides the rule GDD-15 §18.5 recorded but did not fix: the sim maps `tea_stall` blocks to `home_zone`, while GDD-06 §3 anchor resolution would report `d1_market`. It adds no sim function and changes no sim code — the rule and the exact scheduler change it implies are the deliverable, for a later implementation unit. Where an anchor's zone cannot be derived from a merged source, the section says so instead of inventing it.

### 21.1 The rule — a place resolves to its own zone; movement resolves to home

A schedule token resolves to the zone of the anchor it names when the token names a **place** the world locates, and to the NPC's `home_zone` only when the token names **movement** with no anchor:

| Token | Resolves to | Why |
|---|---|---|
| `home` | The NPC's `home_zone` | The home anchor is the household property (GDD-06 §3) |
| `workplace` | The NPC's `workplace_zone` | The employment property's zone (`data/professions.json`) |
| `market` | `d1_market` | The market anchor is Boro Bazar (`LEISURE_ZONE`, GDD-02 §2) |
| `riverfront` | `d1_riverfront` | The riverfront anchor (`LEISURE_ZONE`) |
| `park` | `d1_park` | The park anchor (`LEISURE_ZONE`) |
| `college` / `school` / `college_para` | `d1_education` | The education anchors (`LEISURE_ZONE`) |
| `tea_stall` | **The zone of the nearest tea stall** — `d1_market` or `d1_riverfront` | See §21.2: the stall is a place, and its zone is the stall's, not the NPC's home |
| `restaurant` | **The zone of the restaurant anchor actually used** — `d1_market` (kitchen) or `d1_uptown` (rooftop) | See §21.3: the `LEISURE_ZONE` mapping to `d1_midtown` has no sourced restaurant behind it |
| `transit` | The NPC's `home_zone` | Movement: the commute path, no anchor (§18.3) |
| `mobile` | The NPC's `home_zone` | Movement: the work *is* movement, no anchor (§18.4) |

**The rule is this unit's decision** (labelled as such): no source states a general place-vs-movement rule, though GDD-06 §3's anchor table is the place side of it and §18.3–§18.4 are the movement side. The principle is the anchor's own nature — a token that names somewhere the world built resolves there; a token that names travelling resolves nowhere, so the stored fallback stands.

### 21.2 `tea_stall` — the nearest stall's zone

The tea stall is a place: GDD-02 §2 puts six tea stalls in Boro Bazar (`d1_market`) and GDD-02 §5 puts a sittable tea stall on the riverfront (`d1_riverfront`), and the authored line library places the tea stalls in Boro Bazar (`dlg_topic_place_market`). Under the §21.1 rule a `tea_stall` block resolves to the zone of the nearest tea stall to the NPC — `d1_market` for the Boro Bazar stalls, `d1_riverfront` for the riverfront stall — not to `home_zone`. That decides the §18.5 difference in favour of the GDD-06 §3 anchor reading: the sim's stored fallback was the simplification, and the anchor is the truth.

**Implemented (Unit BS, Queue 13 — 2026-11-22).** `tools/sim/scheduler.py` now implements this section: `resolve_service_anchor(location, home_zone, workplace_zone)` resolves the anchor at schedule time and `instantiate()` stores the resolved anchor (`"<token>:<zone>"`) and its zone on the block. Two operationalisations were needed that §21.2 left open, and both are this unit's labelled decisions: (1) the NPC's "zone cluster" is `{home_zone, workplace_zone}` — the sim stores no coordinates for a household property, so "nearest" is decided on zones: a stall in the NPC's own home zone is nearest by definition, else one in the workplace zone, else the default candidate `d1_market` (six of the seven tea stalls stand in Boro Bazar, and the market kitchen is the everyday restaurant); (2) the stored anchor id is `"<token>:<zone>"` — no per-stall or per-restaurant ids exist in any merged source, so the anchor is identified by type + zone, never by an invented id. `LEISURE_ZONE` gains no `tea_stall` entry, as specified. The sim's stored answer for a `tea_stall` block is now the anchor's zone (§18.5 updated); the `home_zone` fallback survives only for `transit` and `mobile`.

**Scale of the change.** Six `tea_stall` blocks across the profession templates (`data/npc-schedules.json`: construction_worker break, civil_engineer break + leisure, police_officer break + leisure, taxi_driver break — including the leisure defaults of civil_engineer and police_officer) resolve differently under the rule whenever the nearest stall is not in the NPC's home zone — which, for a stall in the market or on the riverfront, is most NPCs. Until the scheduler change lands, the sim's stored answer stays `home_zone` (§18.5 stands as the sim's current answer, not as the decided rule).

**Named anchors (Unit CB · Queue 14 · 2026-11-23).** The anchor id is no longer `"<token>:<zone>"`: the nine named anchors are authored in `data/district1-blockout.json` (`service_anchors` — 6 Boro Bazar tea stalls, 1 riverfront tea stall, the market kitchen, the rooftop restaurant; GDD-02 §5), and `scheduler.resolve_service_anchor()` returns the named id for the resolved zone, falling back to `"<token>:<zone>"` only when no anchor list is supplied. The stall names are this unit's authored labels (no source names the stalls); the counts, zones, and buildings are sourced. Within a zone the scheduler picks the first anchor in file order — the sim stores no NPC coordinates, so "nearest" within a zone is file order, and the UE layer (which has positions) picks the truly nearest. The zone rule, the zone cluster, and the default candidate are unchanged: only the id the block carries is now a real anchor.

### 21.3 `restaurant` — the `d1_midtown` mapping has no sourced restaurant

**Recorded discrepancy — resolved by implementation (Unit BS, Queue 13).** `scheduler.py` `LEISURE_ZONE` used to map `restaurant` → `d1_midtown`, but no restaurant exists in `d1_midtown` in any merged source: GDD-02 §5 puts the restaurant kitchen + dining in `d1_market` and the rooftop restaurant in `d1_uptown` (the district's only high-rise, GDD-02 §4.6). The `d1_midtown` mapping was unsourced — no document, data file, or building row puts a restaurant there. Under the §21.1 rule the token resolves to the zone of the restaurant anchor actually used: `d1_market` for the kitchen, `d1_uptown` for the rooftop. The one `restaurant` block in the templates (business_owner break, 13:30–14:30) therefore resolves to one of those two zones now that the anchor is resolved at schedule time, exactly as §21.2 specifies for `tea_stall`. **The `LEISURE_ZONE` restaurant entry is removed by this unit** — the mapping stood in the sim only "until the scheduler change" (§21.3 as written by BQ), and BS is that change; keeping a known-unsourced mapping as live data would preserve a false statement in code. No midtown restaurant is invented to justify the old mapping.

### 21.4 What changes for the 10 `dlg_topic_place_*` evaluations

The `ask_about_place` topic resolves to exactly one node — the current zone's (§18.7). Under the implemented rule (Unit BS, Queue 13), the zone that `current_zone_at()` returns changes for two tokens and stays the same for the rest:

| Token | Before (old sim stored) | Now (implemented rule, Unit BS) | Place node that fires |
|---|---|---|---|
| `tea_stall` | `home_zone` (any of the 10) | `d1_market` or `d1_riverfront` (nearest stall) | `dlg_topic_place_market` or `dlg_topic_place_riverfront`, instead of the home-zone node |
| `restaurant` | `d1_midtown` | `d1_market` or `d1_uptown` (anchor used) | `dlg_topic_place_market` or `dlg_topic_place_uptown`, instead of `dlg_topic_place_midtown` |
| `transit` | `home_zone` | `home_zone` (unchanged) | The home-zone node, as now |
| `mobile` | `home_zone` | `home_zone` (unchanged) | The home-zone node, as now |
| `market`, `riverfront`, `park`, `college`, `school`, `college_para` | Their `LEISURE_ZONE` zone | Unchanged | Unchanged |
| `home`, `workplace` | `home_zone` / `workplace_zone` | Unchanged | Unchanged |

Practical consequence for the shipped data: a tea-stall NPC now answers for the market or the riverfront — the lines the authors wrote for those zones (`dlg_topic_place_market` names "the market hall, the shop units, the tea stalls") finally fire for the NPCs sitting in the tea stalls, instead of answering for wherever the NPC happens to live. The `zone` condition (§12.3) and the `<zone_name>` placeholder (§12.2 step 6) need no change: they read the accessor's value, and the accessor's value is what this section corrects. The `None` case (§18.6) is untouched — a day with no stored row still has no zone, and no place node matches.

**Gap note.** §12.8 G8 stays resolved by §18 as an accessor question; this section resolved the *store difference* §18.5 left open — the rule is decided, and the sim change that implements it has now landed (Unit BS, Queue 13: `scheduler.py` `resolve_service_anchor()` + stored `anchor` on the block; the `LEISURE_ZONE` restaurant entry is removed). No anchor is invented, and no place node's lines change: the lines already describe the right zones; the accessor was pointing at the wrong one.

### 21.5 UE nearest-anchor selection (Unit DC · Queue 15 · 2026-11-23)

**Status:** DESIGN ONLY — a UE-side rule. No sim code change, no data change. The sim's within-zone pick stays file order (§21.2, Unit CB): the sim stores no NPC coordinates, so it cannot do better, and this unit does not ask it to.

**The problem.** Within a zone the sim picks the first anchor in file order. In `d1_market` that always sends every NPC to Boro Bazar Tea Stall 1, however far from the NPC they stand — six stalls exist in that zone and five of them can never be chosen. The UE has what the sim lacks: the NPC's live position. File order is the sim's honest approximation; on the UE it would be the wrong answer rendered — the stall the NPC actually walks to should be the nearest one.

**The rule.** The zone rule is unchanged: the zone is resolved exactly as the sim resolves it (§21.2 — home zone, else workplace zone, else the default candidate `d1_market`). What changes is only the pick *within* the resolved zone:

1. The UE picks the anchor of that token's type minimising Euclidean distance in blockout metres (local metres, ground plane `x` east / `z` south — TECH-DISTRICT1-BLOCKOUT §1) from the NPC's position at the moment the block starts (the actor's live position), measured to the anchor's `at` point (the interaction point).
2. Ties break by file order in `service_anchors` — the sim's rule as the tie-break, so the two stores agree whenever two anchors are equidistant.
3. The stored anchor id on the block is the named id either way. The sim and the UE can therefore name *different* stalls in the same zone for the same NPC and block. Only the rendered destination differs: the zone answer (§21.1/§18.5) never differs, so no dialogue line changes and §21.4 stands untouched.

**What the UE resolves, per anchor type:**

| Token | Named anchors in the blockout | UE pick within the resolved zone |
|---|---|---|
| `tea_stall` | 7 — 6 Boro Bazar (`d1_market`), 1 riverfront (`d1_riverfront`) | Nearest by position; this is where the rule matters — in `d1_market` six stalls compete and file order would always pick Stall 1 |
| `restaurant` | 2 — market kitchen (`d1_market`), rooftop (`d1_uptown`) | Nearest by position; vacuous today, because each zone holds exactly one restaurant, so the UE pick and the sim pick always agree — stated so the rule already covers a second restaurant authored in a zone later |
| `market`, `riverfront`, `park`, `college_para`, `college`, `school`, `home`, `workplace`, `transit`, `mobile` | None — no named service anchors exist in the blockout for these tokens | Not covered by this rule: the UE resolves them by the existing rules (zone box / building rows), as before |

**Worked example (computed from `data/district1-blockout.json`, verifiable without a UE build).** An NPC whose block starts at the market kitchen, `(60, 40)`, with a `tea_stall` block resolving to `d1_market`: file order sends them to Boro Bazar Tea Stall 1 at `(60, −20)` — 60 m away. The UE rule measures all six: Stall 2 at `(90, 20)` is √(30² + 20²) ≈ 36 m; Stall 3 at `(120, 50)` ≈ 61 m; Stall 1 is 60 m; the rest are further. The UE sends them to Stall 2, the nearest. Same zone, same dialogue, a shorter walk.

**What stays sim-side.** The zone rule, the zone cluster, and the default candidate (§21.2); the schedule-time resolution and the stored block (the UE reads the stored zone and re-picks only the anchor id within that zone, at block start); the `"<token>:<zone>"` fallback when no anchor list is supplied; and the dialogue evaluation (§21.4), which reads the zone and never the anchor id. The sim's `resolve_service_anchor()` is untouched — its docstring already states the UE picks the truly nearest, and this section is that pick, written down.

**Honest boundaries.** No UE code ships here — the rule is stated in blockout metres so it is testable against the data file without a UE build (a headless check can compute the same distances from the JSON). *(Update, Unit DI · Queue 16: the rule is now tested — `tools/verify_queue16_di.py` computes the UE nearest pick headlessly from `data/district1-blockout.json` for six sample positions (market kitchen, riverfront, uptown, plus the single-anchor controls) and the equidistant tie-break, asserting zone agreement with the sim's `resolve_service_anchor()` and a different pick wherever positions differ; the harness tests the rule as stated, it does not compile or run UE.)* Positions are negotiable under the build law (TECH-DISTRICT1-BLOCKOUT: ids are forever, positions are negotiable): if the PC build moves a stall inside its zone box, the nearest pick may change, and that is a data revision, not a redesign. The rule never moves an NPC between zones — a stall in another zone is never "nearest", because the zone rule gates first.

*End of GDD-15 §21 — Unit BQ, Queue 12.*

## 22. Ledger Reason-Code Alignment (Phase 9)

**Unit BU · Queue 13 · Version 1.0 · 2026-11-22**
**Status:** DESIGN ONLY. This section delivers the Phase 9 alignment GDD-15 §14.4 calls for: every sim reason string the schema `CHECK` would reject, mapped to its schema code, with the server-ingest translation rule. It adds no sim code change and no schema change — the mapping table and the rule are the deliverable, and the ingest itself is Phase 9 work. Where a mapping loses a distinction the server's own rules need, the section says so instead of hiding it.

### 22.1 The inventory — how the 47 strings were found, and the corrected count

The inventory was taken by scanning every `store.transfer()` call in `tools/sim/*.py` — including the two `_pay()` forwarders that pass a `reason` variable through (`tools/sim/construction.py` `_pay`, `tools/sim/engine.py` `_pay`/`_pay_purchase`, resolved to their call-site literals) — and collecting every constant reason string that reaches the ledger. `tools/economy_sim.py` is excluded: it simulates in memory and writes no ledger rows. The result:

| | Count |
|---|---|
| Distinct reason strings the sim writes | **47** |
| Pass the `data/schema.sql` `CHECK` (15 codes) | **9** |
| Rejected by the `CHECK` | **38** |

**Correction to §14.4:** §14.4 said the sim writes "~39 reason strings the schema `CHECK` would reject". The exact count is **38** — the "~39" was an estimate made before the inventory was taken, and this section corrects it. The 9 that pass are `business_expense`, `business_revenue`, `inheritance`, `pension`, `purchase`, `rent`, `seed`, `tax`, `wage`. The 6 schema codes the sim never writes are `sale`, `mission_reward`, `loan_disburse`, `loan_repay`, `transfer`, `fine` — the last three matter: the sim never writes a loan in the schema's own vocabulary (which is why both debt flags derive false, §14.5), never writes a mission reward (missions are Phase 6), and never uses the schema's generic `transfer` code even though this section maps 13 strings to it.

### 22.2 The mapping table — every rejected string, mapped

The principle behind the table: `reason_code` is the **coarse act vocabulary** — the fine grain lives in `event_ref`, `transfer_key`, `note`, and the `related_*` ids the row already carries. A mapping is a rename where the sim's word names the same act as a schema code, and a nearest-code match where the act fits an existing code; **no new schema code is proposed for any string** — the 15-code list does not change, and the sim does not change either (§22.3). Each row names the writer site(s) so the mapping can be checked against the code, not trusted on authority.

| Sim string | Schema code | Writer site(s) | Rationale |
|---|---|---|---|
| `loan_disbursement` | `loan_disburse` | `banking.py` `disburse_loan` | Same act, sim word differs; the loan kind is in the note |
| `loan_repayment` | `loan_repay` | `banking.py` `monthly_repayments`; `justice.py` court-ordered repayment to SYS-BANK | Same act; the court-ordered repayment *is* a loan repayment, ordered by a court — the case id is in the note |
| `mortgage_disbursement` | `loan_disburse` | `decisions.py` mortgage path | A mortgage disbursement is a loan disbursement; the mortgage identity survives in the note + `related_property_id` |
| `commercial_rent` | `rent` | `business.py` monthly commercial rent | Rent on a commercial unit is rent; `related_business_id` carries the business |
| `business_sale` | `sale` | `market.py` supply order | A business selling goods to another business is a sale |
| `sales_tax` | `tax` | `engine.py` `_pay_purchase` tax split | A sales tax is a tax; the note ("sales tax on purchases") preserves the kind |
| `tariff` | `tax` | `trade.py` tariff on a trade flow | A tariff is a tax on trade; `transfer_key` `tariff:<flow_id>` preserves the flow |
| `land_purchase` | `purchase` | `parcels.py` parcel transfer | Buying land is a purchase; the note carries the parcel id |
| `vehicle_purchase` | `purchase` | `transport.py` monthly vehicle purchase | Buying a vehicle is a purchase; `transfer_key` `vehbuy:<cid>:<month>` preserves it |
| `debt_repayment` | `transfer` | `family_economy.py` household arrears repayment | **Not a loan** (§14.3): household arrears to SYS-MARKET, not a character↔character loan — so it must not map to `loan_repay`. `transfer` is the generic movement code; the note ("household arrears repayment") preserves the meaning |
| `court_refund` | `transfer` | `justice.py` appeal refund (overturned remedy) | A return of money on appeal; the note carries the appeal id |
| `restitution` | `transfer` | `justice.py` court-ordered restitution, defendant → plaintiff | Compensation to a person, not a fine — `fine` is a penalty paid to the city, and restitution goes to the victim; the note carries the case id |
| `retail_takings` | `business_revenue` | `market.py` system-retailer takings | Takings are the retailer's revenue |
| `production_cost` | `business_expense` | `market.py` recipe materials | Materials bought to produce are an operating expense |
| `shipping` | `business_expense` | `market.py` supply-order shipping | Shipping a supply order is an operating expense of that order |
| `taxi_fare` | `purchase` | `transport.py` trip fare | The rider buys a ride; the note carries origin → destination |
| `transit_subsidy` | `transfer` | `transport.py` per-boarding subsidy | A subsidy payment from a city account to SYS-MARKET — the city buys nothing; the note carries boardings + city, `transfer_key` `transit-subsidy:<city>:<month>` |
| `medical_procurement` | `purchase` | `healthcare.py` monthly procurement | The facility buys medicine; the note carries facility + item + units |
| `municipal_service` | `purchase` | `services.py` city pays for a service | SYS-CITY buys a service from SYS-MARKET; the note carries the service description |
| `policy_spend` | `purchase` | `policies.py` road maintenance; clinic investment | Government buys work/goods from the market (road maintenance, clinic investment); the note carries the policy id + purpose. Rejected alternative: a new `government_spend` code — `purchase` already covers money for goods/services received, and the policy id preserves the purpose |
| `disaster_repair` | `purchase` | `environment.py` repair payments | The account buys repair work; `transfer_key` `repair:<did>:<impact>:<day>` preserves the disaster |
| `construction_funding` | `transfer` | `construction.py` project funding | Funding a project (client or SYS-CITY → engineer) is a transfer of project funds, not a purchase of goods; the note carries the project id |
| `office_allowance` | `wage` | `government.py` office-holder allowance | An allowance for holding office is pay for service; the note carries the office title |
| `welfare` | `transfer` | `policies.py` welfare top-up | A benefit payment to a citizen — not pay for work, so not `wage`; the note carries the policy id |
| `disaster_relief` | `transfer` | `environment.py` relief payments | Relief to a household head; the note carries the disaster id, `transfer_key` `relief:<did>:<ref>` |
| `treasury_allocation` | `transfer` | `government.py` treasury split; municipal revenue allocation | A split of treasury funds between government accounts — the purest case for the generic code; the note carries the city |
| `party_dues` | `transfer` | `politics.py` monthly party dues | Membership dues, citizen → party; `transfer_key` `dues:<party>:<cid>:<month>` |
| `party_funding` | `transfer` | `politics.py` founder contribution | A capital contribution to a party; `transfer_key` `party-seed:<pid>:<cid>` |
| `campaign` | `purchase` | `politics.py` campaign spending | The party buys campaign materials/services from the market; the note carries the election id, `transfer_key` `campaign:<election>:<party>` |
| `cooperation_grant` | `transfer` | `diplomacy.py` monthly cooperation grant | A grant between accounts (partner → national); the note carries the agreement |
| `genesis_grant` | `seed` | `diplomacy.py` external-partner seeding | Genesis funding of a new account — exactly the sim's own `seed` usage (`population.py` seeds initial character balances); the note preserves "external partner model seeded". Recorded risk: if `seed` is later defined narrowly as character genesis balances, this mapping is revisited — the note prefix (§22.3 rule 2) makes that revisit possible |
| `bank_capital` | `transfer` | `banking.py` bank genesis capitalisation | Moving capital between system accounts (SYS-MARKET → SYS-BANK); the note preserves "bank genesis capitalisation" |
| `bank_deposit` | `transfer` | `banking.py` deposit | Money moves into the bank; the `transfer_key` is preserved |
| `bank_withdrawal` | `transfer` | `banking.py` withdrawal | Money moves out of the bank; the `transfer_key` is preserved |
| `interest` | `transfer` | `banking.py` savings interest | The bank's payment to a saver; the note ("savings interest") preserves the kind. `business_expense` was considered and rejected: SYS-BANK is not a business in the schema sense |
| `dividend` | `transfer` | `banking.py` business dividend | A distribution of profit to an investor; `related_business_id` preserves the business |
| `investment` | `purchase` | `banking.py` equity purchase | The character buys equity — acquiring ownership for money; `related_business_id` preserves the business |
| `business_capital` | `transfer` | `business.py` genesis capital (owner + system firms); `decisions.py` founding capital | Capitalising a business; `to_business_id` / `related_business_id` preserve the business. `seed` was considered and rejected: `seed` stays reserved for first balances of new accounts (the sim's own usage), and business capitalisation must not mix with account genesis in `seed` queries |

### 22.3 The server-ingest translation rule

1. **Translate at ingest, never rewrite sim history.** Translation is a pure function — sim reason string → schema code, via the §22.2 table — applied when the server writes the row to the PostgreSQL `economy_ledger`. The sim's SQLite rows are never rewritten, and no sim code changes: renaming 38 call sites would churn the proven sim for no behavioural gain, and the sim's SQLite store enforces no `CHECK` (that is how the drift arose, §14.4).
2. **Fidelity — the original string survives on the server row.** Every translated row's `note` gains a `[sim:<original>]` prefix (e.g. `[sim:loan_disbursement] personal loan disbursement`). The original string stays readable on the server row, so the translation is auditable and reversible, and any query that needs the fine distinction reads the note prefix or the `transfer_key`/`event_ref` — never the translated code alone. Consequences, stated plainly: the Session 04 indicators query that reads `sales_tax` rows and the trade query that reads `tariff` rows must move to note-prefix / `transfer_key`-prefix filters (`[sim:sales_tax]`, `tariff:<flow_id>`) at ingest time, because both translate to `tax` and the code alone can no longer tell them apart.
3. **Fail closed.** A sim string with no row in the table is **rejected at ingest**: the row is not written, the rejection is logged with the `transfer_key`, and the ingest run stops. A new string means the sim grew a reason the contract does not cover; the fix is a table update (this section, extended the same way), never a silent default code — a silent default would launder an unmapped act into a code that misdescribes it.
4. **The code list does not change.** The schema `CHECK` stays at its 15 codes. No string in the table needs a code that does not exist, so no extension is proposed — and the table is the evidence for that: every act the sim performs fits a code the schema already has, once the fine grain is read from the note and keys rather than the code.
5. **The BD migration is untouched.** The §10/Appendix B migration adds `transfer_key`/`event_ref` columns and explicitly does not change `reason_code` — this alignment is a separate Phase 9 item and is not smuggled into it. The translated rows carry the same `transfer_key`/`event_ref` the sim wrote, so idempotency is unaffected by the translation.

### 22.4 What this section does not do

It does not change the sim, the schema, or the §10 migration (see §22.3 rules 1, 4, 5). It does not decide the dialogue effect vocabulary: the effect names `repayment` and `loan` (`check_dialogue_lines_effects` allows them) are a third vocabulary — effect names, not ledger codes — and §14.4 already rules that a settlement row written by the dialogue settlement effect carries `loan_repay`. It does not correct the GDD-01 §8 doc drift — that correction is Unit BZ's job (Queue 14), recorded below. *(Correction applied, Unit BZ · Queue 14: GDD-01 §8 listed reason codes as "(wage, rent, purchase, sale, tax, inheritance, mission_reward, loan, …)" — `loan` is not a schema code (the schema has `loan_disburse`/`loan_repay`); §8 now lists the CHECK's 15 codes verbatim and states the CHECK is authoritative. This paragraph keeps the old wording quoted so the drift's history stays readable.)*

*End of GDD-15 §22 — Unit BU, Queue 13.*

*End of GDD-15 v1.0 + Unit AV §12 (Queue 9) + Queue 10 §§13–16 + Queue 11 §§17–19 + Queue 12 §§20–21 + Queue 13 §§15.2/21.2/21.3/22.*
