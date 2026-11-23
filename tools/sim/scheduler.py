"""Unit 04 — Daily Life Engine (schedules).

A character's day is *data first* (GDD-06 design law): the merged
`npc-schedules.json` template for their profession — or a life-stage
template for children/students/elders — instantiated for one day with:

- per-NPC fixed jitter (±20 min, seeded by character id: the same NPC
  is consistently an early riser — GDD-06 §3);
- the template's weekend variant, applied on Fridays (the district
  weekend). The variants are free-text notes in the data; the rules
  below are their faithful transcription, one per profession, and are
  documented here rather than hidden in per-profession code paths
  elsewhere;
- needs bending (GDD-06 §8): yesterday's deficits edit today's
  template — edits, never rewrites;
- weather interrupts (GDD-06 §7): effect flags from the day's preset
  change blocks (cover-seeking, outdoor-work suspension);
- a rest-day flag set by the decision engine (illness/recovery).

Blocks are returned in absolute game minutes for the given day,
split at midnight, ordered, non-overlapping. An agent is always in
exactly one block — the engine asserts this (audit criterion 4).
"""

LEISURE_ZONE = {
    "riverfront": "d1_riverfront", "park": "d1_park",
    "market": "d1_market",
    "college": "d1_education", "school": "d1_education",
    "college_para": "d1_education",
}
# Service anchors whose zone depends on WHICH anchor the NPC uses, not
# on the token alone (GDD-15 §21; Unit BS, Queue 13). A tea stall is a
# place: six stalls stand in Boro Bazar (d1_market, GDD-02 §2) and one
# sittable stall on the riverfront (d1_riverfront, GDD-02 §5). A
# restaurant is a place too: the kitchen + dining in d1_market and the
# rooftop restaurant in d1_uptown (GDD-02 §5, §4.6). Neither token
# belongs in LEISURE_ZONE: the token alone cannot say which stall or
# which restaurant, and the answer is per-NPC, not per-token. The
# "restaurant": "d1_midtown" entry LEISURE_ZONE used to carry was
# unsourced — no restaurant exists in d1_midtown in any merged source
# (GDD-15 §21.3) — and is removed by this unit, not kept as dead data.
SERVICE_ANCHOR_ZONES = {
    "tea_stall": ("d1_market", "d1_riverfront"),
    "restaurant": ("d1_market", "d1_uptown"),
}
UNCOVERED = {"riverfront", "park"}  # leisure anchors with no cover


def resolve_service_anchor(location, home_zone, workplace_zone):
    """Resolve a service-anchor token to (zone, anchor id) at schedule
    time (GDD-15 §21.2; GDD-06 §3 "nearest anchor of that type in the
    NPC's zone cluster").

    The sim stores no coordinates for a household property, so
    "nearest" is operationalised on zones — this unit's decision,
    labelled here: the NPC's zone cluster is {home_zone,
    workplace_zone}, the two zones the NPC is anchored in daily.
    A stall/restaurant in the NPC's own home zone is nearest by
    definition; else one in the workplace zone; else the default
    candidate (d1_market — six of the seven tea stalls stand in Boro
    Bazar, and the market kitchen is the everyday restaurant).
    The anchor id is "<token>:<zone>": no per-stall or per-restaurant
    ids exist in any merged source, so the anchor is identified by
    type + zone, never by an invented id."""
    candidates = SERVICE_ANCHOR_ZONES[location]
    if home_zone in candidates:
        zone = home_zone
    elif workplace_zone in candidates:
        zone = workplace_zone
    else:
        zone = candidates[0]
    return zone, f"{location}:{zone}"


def _mins(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def jitter_for(rng, character_id):
    """Fixed per-NPC offset in [-20, +20] minutes (GDD-06 §3)."""
    return rng.stream("jitter", character_id).randint(-20, 20)


def _base_blocks(template):
    """Template blocks for one day, wrap-around blocks split so the
    day's own list includes the morning tail of the wrapping block
    (templates are daily-periodic, so the tail is identical)."""
    blocks = []
    for b in template:
        start, end = _mins(b["from"]), _mins(b["to"])
        if start < end:
            blocks.append({"start": start, "end": end,
                           "activity": b["activity"],
                           "location": b["location"]})
        else:  # wraps midnight (e.g. sleep 22:30 -> 05:30)
            blocks.append({"start": start, "end": 1440,
                           "activity": b["activity"],
                           "location": b["location"]})
            blocks.append({"start": 0, "end": end,
                           "activity": b["activity"],
                           "location": b["location"]})
    return sorted(blocks, key=lambda x: x["start"])


def _apply_friday(blocks, profession_id, character_id, day_index, rng):
    """Weekend-variant transcription (see module docstring). Only
    Fridays (weekday 4, Day 1 = Monday) reach this function."""
    week = day_index // 7

    def convert(activity_from, activity_to, location_to=None, pred=None):
        for b in blocks:
            if b["activity"] == activity_from and (pred is None or pred(b)):
                b["activity"] = activity_to
                if location_to:
                    b["location"] = location_to
                b["weekend_variant"] = True

    if profession_id == "construction_worker":
        for b in blocks:
            if b["activity"] != "work":
                continue
            if b["start"] >= 750:  # afternoon shift becomes leisure
                b["activity"] = "leisure"
                b["location"] = "riverfront"
                b["weekend_variant"] = True
            elif b["end"] > 750:  # morning shift ends at 12:30
                b["end"] = 750
                b["weekend_variant"] = True
    elif profession_id == "civil_engineer":
        convert("work", "study", "home")
    elif profession_id == "doctor":
        on_call = rng.stream("oncall", character_id, week).random() < 1 / 3
        if not on_call:
            convert("work", "home", "home")
    elif profession_id == "teacher":
        convert("work", "study", "home")
    elif profession_id == "police_officer":
        off = rng.stream("rotation", character_id, week).random() < 1 / 3
        if off:
            convert("work", "home", "home")
    elif profession_id == "taxi_driver":
        work = [b for b in blocks if b["activity"] == "work"]
        if work:
            work[-1]["end"] = max(work[-1]["end"], 1380)  # to 23:00
            work[-1]["weekend_variant"] = True
    elif profession_id == "chef":
        work = [b for b in blocks if b["activity"] == "work"]
        if work:
            work[-1]["end"] = max(work[-1]["end"], 1410)  # to 23:30
            work[-1]["weekend_variant"] = True
    elif profession_id == "software_developer":
        convert("work", "study", "home")
    elif profession_id == "shop_owner":
        # Closed 12:30-14:30: split the spanning work block.
        out = []
        for b in blocks:
            if b["activity"] == "work" and b["start"] < 750 < b["end"]:
                out.append({**b, "end": 750})
                out.append({"start": 750, "end": 870, "activity": "home",
                            "location": "home", "weekend_variant": True})
                out.append({**b, "start": 870})
            else:
                out.append(b)
        blocks[:] = sorted(out, key=lambda x: x["start"])
    elif profession_id == "business_owner":
        convert("work", "home", "home", pred=lambda b: b["start"] >= 720)
    # pilot: roster decides; template has no work blocks. No change.
    return blocks


def _insert_block(blocks, new):
    """Insert a block, splitting whatever it overlaps (the overlapped
    activity resumes afterwards)."""
    out = []
    for b in blocks:
        if b["end"] <= new["start"] or b["start"] >= new["end"]:
            out.append(b)
        else:
            if b["start"] < new["start"]:
                out.append({**b, "end": new["start"]})
            if b["end"] > new["end"]:
                out.append({**b, "start": new["end"]})
    out.append(new)
    return sorted(out, key=lambda x: x["start"])


def _apply_saturday(blocks, profession_id):
    if profession_id == "teacher":
        blocks[:] = _insert_block(blocks, {
            "start": 540, "end": 600, "activity": "errand",
            "location": "market", "weekend_variant": True})
    elif profession_id == "chef":
        work = [b for b in blocks if b["activity"] == "work"]
        if work:
            work[-1]["end"] = max(work[-1]["end"], 1410)
            work[-1]["weekend_variant"] = True
    return blocks


def _bend_for_needs(blocks, needs, traits, is_life_stage):
    """GDD-06 §8 needs bending. `needs` holds yesterday's satisfaction
    values (0..100; low = deficit). Traits weight the edits."""
    if needs is None:
        return blocks
    # Food deficit -> insert a market errand into the longest home block.
    if needs["hunger"] < 40 and not any(b["activity"] == "errand"
                                        for b in blocks):
        home = [b for b in blocks if b["activity"] == "home"
                and b["end"] - b["start"] >= 90]
        if home:
            longest = max(home, key=lambda b: b["end"] - b["start"])
            mid = (longest["start"] + longest["end"]) // 2
            blocks.append({"start": mid, "end": mid + 45,
                           "activity": "errand", "location": "market",
                           "need_bent": "food"})
    # Social deficit -> leisure moves to the most social anchor.
    if needs["social"] < 35:
        for b in blocks:
            if b["activity"] == "leisure" and b["location"] in ("home", "park"):
                b["location"] = "tea_stall"
                b["need_bent"] = "social"
    # Rest deficit -> sleep extends by up to an hour (taken from the
    # morning home block). High discipline resists (GDD-06 §8).
    if needs["sleep"] < 35 and traits and traits["trait_discipline"] < 70:
        morning_sleep = [b for b in blocks if b["activity"] == "sleep"
                         and b["start"] == 0]
        if morning_sleep:
            morning_sleep[0]["end"] = min(1440, morning_sleep[0]["end"] + 60)
            morning_sleep[0]["need_bent"] = "rest"
    # Security deficit -> elder/child templates drop evening leisure.
    # High risk tolerance ignores the bend.
    if (needs["safety"] < 35 and is_life_stage
            and not (traits and traits["trait_risk_tolerance"] >= 70)):
        for b in blocks:
            if b["activity"] == "leisure" and b["start"] >= 1080:
                b["activity"] = "home"
                b["location"] = "home"
                b["need_bent"] = "security"
    return blocks


def _apply_weather(blocks, weather_effects, profession_id):
    """GDD-06 §7 interrupts, driven by effect flags, never preset
    names. Blocks gain a `weather` note when changed."""
    if not weather_effects:
        return blocks
    eff = set(weather_effects)
    for b in blocks:
        if "npc_cover_seeking_strong" in eff:
            if b["activity"] == "work" and profession_id in (
                    "construction_worker",):
                b["activity"] = "home"
                b["location"] = "home"
                b["weather"] = "outdoor_work_suspended"
            elif b["activity"] == "leisure":
                b["activity"] = "home"
                b["location"] = "home"
                b["weather"] = "leisure_cancelled_storm"
        elif "npc_cover_seeking" in eff:
            if b["activity"] in ("leisure", "break") \
                    and b["location"] in UNCOVERED:
                b["location"] = "home"
                b["weather"] = "seek_cover"
        if "river_level_up_visual" in eff and b["location"] == "riverfront" \
                and b["activity"] == "leisure":
            b["location"] = "home"
            b["weather"] = "riverfront_closed"
    return blocks


def _normalise(blocks, day_start):
    """Sort, clamp overlaps (a block never starts before the previous
    one ends; minimum block length 5 min), drop empties, and shift to
    absolute game minutes. Guarantees the coverage invariant the
    engine asserts: no overlaps; gaps become explicit home/idle."""
    blocks = sorted(blocks, key=lambda b: b["start"])
    out = []
    cursor = 0
    for b in blocks:
        start = max(b["start"], cursor)
        end = max(b["end"], start + 5) if b["end"] > start else b["end"]
        if end <= start:
            continue
        if start > cursor:
            out.append({"start": day_start + cursor, "end": day_start + start,
                        "activity": "home", "location": "home",
                        "gap_fill": True})
        nb = dict(b)
        nb["start"] = day_start + start
        nb["end"] = day_start + min(end, 1440)
        out.append(nb)
        cursor = min(end, 1440)
    if cursor < 1440:
        out.append({"start": day_start + cursor, "end": day_start + 1440,
                    "activity": "home", "location": "home", "gap_fill": True})
    return out


def instantiate(data, character, day_index, rng, needs=None, traits=None,
                weather_effects=None, rest_day=False):
    """Build one character's schedule blocks for one day.

    `character` needs: character_id, template_id (profession id or
    life-stage template id), is_life_stage, home_zone, workplace_zone.
    Returns (blocks, template_id)."""
    day_start = day_index * 1440
    template_id = character["template_id"]
    if character["is_life_stage"]:
        template = data.life_stage_templates[template_id]
        profession_id = None
    else:
        template = data.schedules[template_id]["template"]
        profession_id = template_id
    blocks = _base_blocks(template)
    weekday = day_index % 7  # Day 1 (index 0) is a Monday; Friday = 4
    if weekday == 4 and profession_id:
        blocks = _apply_friday(blocks, profession_id,
                               character["character_id"], day_index, rng)
    if weekday == 5 and profession_id:
        blocks = _apply_saturday(blocks, profession_id)
    blocks = _bend_for_needs(blocks, needs, traits, character["is_life_stage"])
    blocks = _apply_weather(blocks, weather_effects, profession_id)
    if rest_day:
        # A rest day bends work AND study blocks home (Session 06:
        # GDD-12 §4.1 — illness replaces the day's work/study with
        # rest; GDD-11 §2 — illness is the only designed source of
        # school absence, and it acts through exactly this bend).
        for b in blocks:
            if b["activity"] in ("work", "study"):
                b["activity"] = "home"
                b["location"] = "home"
                b["rest_day"] = True
    # Per-NPC fixed jitter on boundaries, then normalise.
    jitter = jitter_for(rng, character["character_id"])
    for b in blocks:
        if b["start"] not in (0,):
            b["start"] += jitter
        if b["end"] not in (1440,):
            b["end"] += jitter
    blocks = _normalise(blocks, day_start)
    # Resolve zones. Service anchors resolve to the anchor's own zone
    # (GDD-15 §21.2); the rest resolve by token; movement tokens keep
    # the home_zone fallback (GDD-15 §18.3-18.4).
    for b in blocks:
        if b["location"] in SERVICE_ANCHOR_ZONES:
            zone, anchor = resolve_service_anchor(
                b["location"], character["home_zone"],
                character["workplace_zone"])
            b["zone"] = zone
            b["anchor"] = anchor
        elif b["location"] == "home":
            b["zone"] = character["home_zone"]
        elif b["location"] == "workplace":
            b["zone"] = character["workplace_zone"]
        elif b["location"] in LEISURE_ZONE:
            b["zone"] = LEISURE_ZONE[b["location"]]
        else:  # transit, mobile: local to home/work path
            b["zone"] = character["home_zone"]
    return blocks, template_id
