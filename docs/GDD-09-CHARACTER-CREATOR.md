# NEXORA — GDD-09: Character Creator & Clothing

**Unit Y · Version 1.0 · 2026-11-21**
**Parent documents:** `docs/GDD-01-LIFE-AND-DATA-MODEL.md` §1 (the canonical profile card; `characters.avatar_ref` points at the MetaHuman configuration), §2 (tiers), §3 (life stages — the child/elder gate), §8 (ledger) · `docs/PHASE2-METAHUMAN-SHEET.md` §3 (the owner's character spec — the first creator output), §5 (outfit & hair rules), §6 (LOD/crowd tiers) · `data/prices.json` `clothing` (v1.2 — owns every garment price) · `data/clothing.json` (the catalogue: slots, contexts, profession uniforms) · `data/professions.json` (the 11 profession ids the uniform mapping covers) · `docs/GDD-06-NPC-BEHAVIOUR.md` §4 (the work sub-states uniforms are worn in), §5 (crowd tiers)
**Status:** DESIGN ONLY. No creator UI, wardrobe asset or MetaHuman exists yet; the first real creator output is built on the owner's PC in Phase 2 against the PHASE2 sheet. This document is the contract that phase implements against.

> **Design law:** the player *chooses a person*, MetaHuman *renders the person*. Everything the player picks is stored as data on the character record (`avatar_ref` → creator parameters); nothing about a face is baked into code, and no outfit is ever a code change (PHASE2 §5). If a choice cannot be written down as data, it is not a creator feature.

---

## 1. The Creator Flow (player character)

The creator runs once per new character (GDD-01 §1: an account outlives its characters; each new life starts here). Five steps, in order:

| Step | The player picks | MetaHuman generates / the system does |
|---|---|---|
| 1. Start point | A preset from the approved pool (PHASE2 §6: ~40 presets, varied age, tone, build, hair) **or** "the owner's character" template when the account holder plays himself | The preset's base mesh, skeleton and skin material |
| 2. Face | Sculpt sliders (jaw, cheekbones, nose, eyes, brow) within the preset's range; one optional distinguishing feature (the PHASE2 §3.1 scar rule: one memorable feature beats a perfect face, and it is the player's call, never forced) | Blended face mesh; face-animation rig (Animator/Live Link compatibility is a Phase 2 exit check, not a creator promise) |
| 3. Skin & grooming | Skin tone (never lightened past the chosen preset's family — PHASE2 §3.2 rule), facial hair as a **toggle** (light stubble on/off — a grooming option, not a fixed trait) | Skin material parameters; grooming meshes |
| 4. Hair | Hairstyle from the approved list + black/brown/grey colour. **Every style is previewed from behind before it can be confirmed** (PHASE2 §5: the third-person camera lives behind the head) | Groom asset bound to the head |
| 5. Body & name | Build (within the life-stage's legal range, §3), height ~160–190 cm, display name, starting profession (from `professions.json` `playable_in_v1` set) | Body mesh; the `characters` row + `avatar_ref` storing every parameter above |

**What the player never picks:** age as a number to edit later (GDD-01 §1: age is derived from `born_at_game_time`), economic class (derived, GDD-01 §7), and anything about another character. NPC faces are never player-edited.

**The approval gate (from PHASE2 §3.1):** the owner's own character is approved by the owner looking at the Creator preview before export. A MetaHuman the owner does not recognise as himself is a failed Phase 2, however good the render is. The creator therefore keeps the owner's spec sheet (§3.1 of the PHASE2 sheet) as its first template, not as a suggestion.

## 2. Who Gets What Creator (by tier, GDD-01 §2)

| Tier | Creator treatment |
|---|---|
| **Player** | Full flow above; unique face — no two Full-tier characters share a face (PHASE2 §6) |
| **Full NPC** (~25 named per district) | Authored by the developer through the same flow, stored the same way; unique faces |
| **Scheduled NPC** | Assembled from the preset pool + randomised hair/outfit from `clothing.json`; no sculpting. Reuse is expected and invisible because hair/outfit/context differ |
| **Ambient** | **Not MetaHumans at all** (PHASE2 §6): Mass representation, clothing is texture-level variation. The creator never runs for the crowd |
| **Child / Elder** | **Not creatable in v1.** MetaHuman ships no child/elder bodies (GDD-01 §3 gate; master plan Phase 7). Children and elders exist in data, households and schedules today; their authored bodies are a Phase 7 deliverable. The creator says so on the life-stage screen instead of offering a shrunk adult |

## 3. Outfit Model — Slots & Contexts

An **outfit** is a named list of `clothing.json` item ids, at most one item per slot. Slots (from `clothing.json` `slots`):

`top · bottom · full_body · footwear · headwear · outerwear · accessory · workwear · uniform_set · outfit_set`

Rules:
- A `full_body` item (panjabi, saree, salwar kameez) occupies top+bottom; an `outfit_set`/`uniform_set` occupies every slot it lists and is worn alone except `accessory`/`outerwear` (a uniform under a raincoat is legal; a suit under a uniform is not).
- **Contexts, not moods** (PHASE2 §5): every character carries at most three outfits — `work`, `casual`, `formal` — plus two system overlays that are not outfits: `weather` (raincoat/umbrella, auto-suggested by the weather manager's rain/storm presets) and `home` (the casual outfit's relaxed subset). The player character's three are built in the creator's final step from the catalogue at catalogue prices (the starting balance is charged — GDD-01 §8: a ledger `purchase` row; the owner's 25,000 start covers a work set, a casual set and one formal piece with room to spare, which is deliberate).
- **NPCs get one or two outfits** (PHASE2 §5): Scheduled NPCs get `work` + `casual`; Ambient crowds get texture variants, never catalogue outfits.
- **Outfits are data, not code:** an outfit is a MetaHuman wardrobe preset + a list of item ids (PHASE2 §5). Adding a garment = adding a catalogue row + a mesh; swapping an outfit never touches C++. Wardrobe state (owned items, current outfit per context) is character data, mapped for saving alongside GDD-01 §9.
- **No real-brand logos, ever** (PHASE2 §5): original NEXORA garments only — the same originality rule as the whole project.

## 4. The Catalogue (`data/clothing.json` + `prices.json` `clothing`)

31 items in three families. **Prices live only in `prices.json`** (`clothing`, added in v1.2 by this unit — before this unit prices.json carried only the monthly `clothing_personal` budget lines, no item prices); `clothing.json` entries point at them via `price_ref`, following the `vehicles.json` convention. If the two ever disagree, prices.json wins.

| Family | Contents | Price logic |
|---|---|---|
| Everyday (18) | lungi, genji vest, basic/formal shirts & trousers, panjabi (simple/festive), saree (cotton/silk-blend/silk), salwar kameez, sandals, leather/premium shoes, light jacket, blazer, suit set | Banded lower/mid/upper so a band's normal replacement cycle stays inside its `clothing_personal` monthly budget (600 / 1,500 / 5,000 NCr) |
| Weather (2) | umbrella, raincoat | The `weather` overlay (§3); rain also raises their shop visibility — a nudge, not a price change (prices never move for weather) |
| Workwear & uniforms (11) | work gloves, hi-vis vest, safety helmet, safety boots, construction PPE set, and the six uniform sets of §5 | PPE set priced as the exact sum of its parts (750 + 600 + 1,800 + 200 = 3,350) so buying the set never beats or loses to buying pieces |

**Where clothes are bought:** the market hall interior and premium shops of District 1 (GDD-02 §5/§6 stock) — shopping is a place, not a menu, once interiors exist; until Phase 5 the creator's starting outfits are the only clothing transaction, charged at creation.

## 5. Profession Uniforms (all 11 professions)

The mapping is data: `clothing.json` `profession_uniforms`. Summary (the JSON is the authority):

| Profession | Work outfit | Issued by |
|---|---|---|
| `construction_worker` | Construction PPE set | Employer (site contractor) |
| `civil_engineer` | PPE set on site; own formal clothes in the office (a dress code, not a uniform — the split day of GDD-06 §4.2) | Employer (project) for the PPE |
| `doctor` | Medical scrubs + white coat | Employer (clinic) |
| `teacher` | None — formal dress code in own clothes | — (students wear `uniform_school`, bought by their household; the student loop is Unit AB's) | *(Update, Unit DK · Queue 17: implemented — `education.enrol_school_sweep` seeds `uniform_school` beside the enrolment, context "school", issued "household", one set per student; a student who already holds it is not issued a second.)* |
| `police_officer` | Police uniform set | Police service (city) |
| `taxi_driver` | Depot driver uniform — **from progression tier 2** (depot car); tier-1 rented-CNG drivers wear their own clothes | Depot (`d1_industry`) |
| `chef` | Chef whites + apron | Employer (restaurant) |
| `software_developer` | None — own casual/formal | — |
| `shop_owner` | None — own clothes behind the counter | — |
| `business_owner` | None — own formal (`suit_set` is the senior-tier marker) | — |
| `pilot` | Airline uniform set — **catalogued but not issuable in District 1** | Airline (none operates here yet) |

**Uniform economics:** a uniform is *issued*, not bought — hiring writes the set into the character's wardrobe with no ledger charge. Replacement is the only charge: a lost/ruined set is replaced at the catalogue price, charged to the employer unless the loss was the character's negligence (a relationship/employment flag, Phase 6 tuning). The pilot row is the honest gap, stated in the data as well as here: District 1 has no airport and no airline (GDD-06 §4.11), so the pilot's uniform exists for the future airport district and the pilot wears his own formal clothes on District 1 rest days. A uniform that cannot be issued is never faked as worn.

**Uniforms and behaviour:** the Work sub-states of GDD-06 §4 assume the mapped outfit for their context; the OffDuty interrupt (police) and the civil engineer's site/office split are outfit changes, which is why outfit state is simulation data, not cosmetics.

## 6. What This Document Deliberately Does Not Decide

- **The preset pool itself** (~40 faces) — approved one by one in Phase 2 on the owner's PC (PHASE2 §6); this document fixes the rules the pool must satisfy, not its faces.
- **Child/elder bodies** — Phase 7 authored assets (GDD-01 §3 gate). Not a creator setting.
- **Clothing physics, wear-and-tear visuals, laundry** — no system; garments do not degrade in v1 (the PPE replacement rule in §5 is an employment event, not a wear simulation).
- **A clothing shop UI** — Phase 5 interiors own it; this document owns the catalogue and prices it will sell from.
- **Cosmetic microtransactions** — none. NEXORA has no real-money clothing store in any phase of the current plan; if that ever changes it is an owner's decision, not a design default.

## 7. Acceptance Checks (for Phase 2 implementation)

- [ ] Creator produces the owner's character to the PHASE2 §3.1 spec and the owner approves the preview (the gate of §1).
- [ ] Every creator choice round-trips: pick → save (`avatar_ref`) → reload → identical character.
- [ ] The three starting outfits are charged to the ledger at `prices.json` prices and the balance after creation matches the ledger sum.
- [ ] All 11 `profession_uniforms` rows resolve: profession ids exist in `professions.json`, every outfit item id exists in `clothing.json`, every `price_ref` exists in `prices.json` `clothing` (script-checked in this unit; re-run when either file changes).
- [ ] Hair preview includes the from-behind view; no hairstyle can be confirmed without it.
- [ ] A Scheduled NPC assembled from pool + catalogue is visually distinct from its preset sibling (hair or outfit differs) in the Phase 2 crowd capture.
