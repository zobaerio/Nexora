"""Session 02 Unit 01 — Family Formation System (extended kinship).

Session 01 stored the nuclear graph: parent/child edges (directional),
spouse and sibling edges (symmetric). Extended kinship is NEVER
stored as its own edges — grandparents, uncles/aunts, cousins,
in-laws and grandchildren are *derived* from that graph on every
query, so the family tree can never disagree with itself. The only
new stored facts this unit adds are the ones that are genuinely new
events in a life:

- guardianship: when a minor loses both parents, an adult takes
  legal care — a 'guardian'/'ward' edge pair plus a household role;
- adoption: when the simulation rules enable it (the household's
  culture profile carries `adoption_enabled`) and a non-kin guardian
  has actually raised the child for a sustained period, the
  guardianship converts to parent edges flagged {"adoptive": true}
  — after which every derived-kinship query treats the child as
  family, because in the simulated world, they are.

Both are recorded in relationship_history (Unit 01's history table)
and in the life-event log. Consistency rule: derivation only ever
reads parent/spouse/sibling edges, and those are written once by
Session 01's engines — this module never rewrites them except the
adoption conversion above, which is itself a recorded life event.
"""
from . import lifecycle
from . import memory as memory_mod
from . import relationships as rel

ADOPTION_MIN_GUARDIAN_DAYS = 90  # sustained care before conversion


# -- derived kinship (computed, never stored) --------------------------------

def grandparents(store, cid):
    out = set()
    for p in rel.parents_of(store, cid):
        out.update(rel.parents_of(store, p))
    return sorted(out)


def grandchildren(store, cid):
    out = set()
    for c in rel.children_of(store, cid):
        out.update(rel.children_of(store, c))
    return sorted(out)


def uncles_aunts(store, cid):
    """Parents' siblings."""
    out = set()
    for p in rel.parents_of(store, cid):
        out.update(rel.siblings_of(store, p))
    return sorted(out)


def cousins(store, cid):
    """Children of uncles/aunts, excluding own siblings."""
    out = set()
    sibs = set(rel.siblings_of(store, cid)) | {cid}
    for ua in uncles_aunts(store, cid):
        out.update(rel.children_of(store, ua))
    return sorted(out - sibs)


def nephews_nieces(store, cid):
    out = set()
    for s in rel.siblings_of(store, cid):
        out.update(rel.children_of(store, s))
    return sorted(out)


def parents_in_law(store, cid):
    sp = rel.spouse_of(store, cid)
    return rel.parents_of(store, sp) if sp else []


def siblings_in_law(store, cid):
    sp = rel.spouse_of(store, cid)
    return rel.siblings_of(store, sp) if sp else []


def extended_family(store, cid):
    """Everyone reachable by the derived kinship relations."""
    fam = set(rel.family_of(store, cid))
    fam.update(grandparents(store, cid), grandchildren(store, cid),
               uncles_aunts(store, cid), cousins(store, cid),
               nephews_nieces(store, cid), parents_in_law(store, cid),
               siblings_in_law(store, cid))
    fam.discard(cid)
    return sorted(fam)


def is_kin(store, a, b):
    return b in extended_family(store, a) or a in rel.family_of(store, b)


def family_tree(store, cid, depth=3):
    """A nested, query-time family tree for one person — built from
    the live graph, so it is the observation surface for kinship."""
    def node(x, d):
        char = store.row("SELECT display_name, died_at_game_minutes"
                         " FROM characters WHERE character_id = ?", (x,))
        out = {"character_id": x,
               "name": char["display_name"] if char else x,
               "alive": bool(char and char["died_at_game_minutes"] is None)}
        if d <= 0:
            return out
        sp = rel.spouse_of(store, x)
        if sp:
            out["spouse"] = node(sp, 0)
        kids = rel.children_of(store, x)
        if kids:
            out["children"] = [node(k, d - 1) for k in kids]
        return out
    tree = node(cid, depth)
    tree["parents"] = [node(p, 0) for p in rel.parents_of(store, cid)]
    tree["grandparents"] = [node(g, 0) for g in grandparents(store, cid)]
    tree["siblings"] = [node(s, 0) for s in rel.siblings_of(store, cid)]
    tree["uncles_aunts"] = [node(u, 0) for u in uncles_aunts(store, cid)]
    tree["cousins"] = [node(c, 0) for c in cousins(store, cid)]
    return tree


# -- guardianship & adoption ---------------------------------------------------

def guardian_of(store, cid):
    rows = rel._others(store, cid, "guardian", "to")
    return rows[0] if rows else None


def _candidate_guardian(store, child):
    """Who can take this child, in order of closeness: an adult
    sibling in the same household, a living grandparent, then the
    eldest adult of the child's household. None if nobody exists."""
    from .identity import age_years
    now = store.world()["game_minutes"]
    hid = child["household_id"]

    def is_adult(x):
        row = store.row("SELECT born_at_game_minutes,"
                        " died_at_game_minutes FROM characters"
                        " WHERE character_id = ?", (x,))
        return row and row["died_at_game_minutes"] is None \
            and age_years(row["born_at_game_minutes"], now) >= 18

    for sib in rel.siblings_of(store, child["character_id"]):
        if is_adult(sib):
            srow = store.row("SELECT household_id FROM characters"
                             " WHERE character_id = ?", (sib,))
            if srow and srow["household_id"] == hid:
                return sib
    for gp in grandparents(store, child["character_id"]):
        if is_adult(gp):
            return gp
    if hid:
        members = store.rows(
            "SELECT c.character_id, c.born_at_game_minutes FROM"
            " household_members hm JOIN characters c"
            " ON c.character_id = hm.character_id WHERE hm.household_id"
            " = ? AND hm.left_at_game_minutes IS NULL"
            " AND c.died_at_game_minutes IS NULL"
            " ORDER BY c.born_at_game_minutes ASC", (hid,))
        for m in members:
            if m["character_id"] != child["character_id"] \
                    and age_years(m["born_at_game_minutes"], now) >= 18:
                return m["character_id"]
    return None


def ensure_guardianship(store, game_minutes):
    """Sweep: every living minor whose parents are both dead or
    absent and who has no guardian gets one, if a candidate exists.
    Returns the list of (child, guardian) pairs created. Idempotent:
    a child with living parents or an existing guardian is skipped,
    so this can run on any cadence."""
    from .identity import age_years
    created = []
    minors = store.rows(
        "SELECT * FROM characters WHERE is_system = 0"
        " AND died_at_game_minutes IS NULL ORDER BY character_id")
    for child in minors:
        cid = child["character_id"]
        if age_years(child["born_at_game_minutes"], game_minutes) >= 18:
            continue
        parents = rel.parents_of(store, cid)
        if any(lifecycle.alive(store, p) for p in parents):
            continue
        if guardian_of(store, cid):
            continue
        guardian = _candidate_guardian(store, child)
        if not guardian:
            continue
        rel.add_edge(store, guardian, cid, "guardian", game_minutes,
                     trust=55, affection=60, respect=40, both_ways=False)
        rel.add_edge(store, cid, guardian, "ward", game_minutes,
                     trust=60, affection=55, respect=55, both_ways=False)
        rel.record_history(store, guardian, cid, "guardian",
                           "guardianship_started", game_minutes)
        # The guardian's household takes the child in, if needed.
        grow = store.row("SELECT household_id FROM characters"
                         " WHERE character_id = ?", (guardian,))
        if grow and grow["household_id"] \
                and grow["household_id"] != child["household_id"]:
            from . import relationships as _rel
            if child["household_id"]:
                _rel._move_household_member(
                    store, cid, child["household_id"],
                    grow["household_id"], game_minutes)
        memory_mod.log_life_event(store, cid, "guardianship",
                                  game_minutes, other_character_id=guardian)
        memory_mod.log_life_event(store, guardian, "became_guardian",
                                  game_minutes, other_character_id=cid)
        created.append((cid, guardian))
    return created


def maybe_adopt(store, data, game_minutes):
    """Adoption conversion, only where the simulation rules enable
    it: the guardian's household culture profile must carry
    adoption_enabled, the guardian must not already be kin, and the
    care must have lasted ADOPTION_MIN_GUARDIAN_DAYS. Converts the
    guardianship into parent edges flagged adoptive. Returns the
    list of adopted child ids."""
    from . import culture as culture_mod
    adopted = []
    wards = store.rows(
        "SELECT from_character_id AS guardian, to_character_id AS child,"
        " created_at_game_minutes FROM relationships"
        " WHERE relation_type = 'guardian'")
    for w in wards:
        guardian, child = w["guardian"], w["child"]
        if game_minutes - w["created_at_game_minutes"] \
                < ADOPTION_MIN_GUARDIAN_DAYS * 1440:
            continue
        if rel.get_edge(store, guardian, child, "parent"):
            continue
        if is_kin(store, guardian, child):
            continue  # kin guardianship stays guardianship
        grow = store.row("SELECT household_id FROM characters"
                         " WHERE character_id = ?", (guardian,))
        if not grow or not grow["household_id"]:
            continue
        profile = culture_mod.profile_for_household(
            store, data, grow["household_id"])
        if not profile or not profile.get("adoption_enabled"):
            continue
        rel.add_edge(store, guardian, child, "parent", game_minutes,
                     trust=60, affection=80, respect=35, both_ways=False,
                     flags={"adoptive": True})
        rel.add_edge(store, child, guardian, "child", game_minutes,
                     trust=65, affection=75, respect=50, both_ways=False,
                     flags={"adoptive": True})
        rel.record_history(store, guardian, child, "parent", "adopted",
                           game_minutes, details={"adoptive": True})
        memory_mod.log_life_event(store, child, "adopted", game_minutes,
                                  other_character_id=guardian)
        memory_mod.log_life_event(store, guardian, "adoption",
                                  game_minutes, other_character_id=child)
        adopted.append(child)
    return adopted
