"""Session 07 test fixtures: a hand-built citizen world with the
city layer and the Session 07 transport layer set up (plus the
Session 06 layer where a test needs clinic records)."""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))

from tools.sim import cities as cities_mod  # noqa: E402
from tools.sim import transport as transport_mod  # noqa: E402
from tools.sim.tests.common import (data, employ, make_person,  # noqa: E402
                                    make_store, rng)

GM = 480  # genesis game_minutes, matching the engine


def transport_world(with_humandev=False):
    """(store, data) with cities + Session 07 layer seeded."""
    store = make_store()
    d = data()
    r = rng()
    cities_mod.setup_cities(store, d, r)
    if with_humandev:
        from tools.sim import humandev as humandev_mod
        humandev_mod.setup_humandev(store, d, GM)
    transport_mod.setup_transport(store, d, GM)
    store.commit()
    return store, d


def make_household_zone(store, member_ids, zone, game_minutes=GM,
                        rent=4000):
    """common.make_household with a chosen residence zone."""
    hid = store.next_id("HH", "households", "household_id")
    pid = store.next_id("PR", "properties", "property_id")
    store.insert("properties", property_id=pid,
                 property_type="apartment", district_id=zone,
                 address_label="Transport Test Block", tier=3,
                 status="rented", market_value=750000,
                 building_ref="test", unit_index=0)
    store.insert("households", household_id=hid, name="Test Household",
                 home_property_id=pid, district_id=zone,
                 created_at_game_minutes=game_minutes)
    for i, cid in enumerate(member_ids):
        store.insert("household_members", household_id=hid,
                     character_id=cid,
                     role="head" if i == 0 else "member",
                     joined_at_game_minutes=game_minutes)
        store.execute("UPDATE characters SET household_id = ?"
                      " WHERE character_id = ?", (hid, cid))
    tid = store.next_id("TN", "tenancies", "tenancy_id")
    store.insert("tenancies", tenancy_id=tid, property_id=pid,
                 tenant_household_id=hid, rent_per_month=rent,
                 started_at_game_minutes=game_minutes)
    return hid, pid


def citizen(store, zone="d1_midtown", age=30, profession_id=None,
            first="Citizen", balance=0, r=None):
    r = r or rng()
    cid = make_person(store, age=age, first=first, game_minutes=GM,
                      r=r)
    make_household_zone(store, [cid], zone, game_minutes=GM)
    if profession_id:
        employ(store, data(), cid, profession_id, game_minutes=GM)
    if balance:
        store.transfer("SYS-MARKET", cid, balance, "seed_grant", GM,
                       transfer_key=f"seed:{cid}")
    store.commit()
    return cid


def set_schedule(store, character_id, day_index, legs):
    """Persist an instantiated schedule for one day. legs is a
    list of (start, end, activity, zone) covering the full day."""
    blocks = [{"start": s, "end": e, "activity": a, "location": "home",
               "zone": z} for s, e, a, z in legs]
    store.execute(
        "INSERT OR REPLACE INTO instantiated_schedules"
        " (character_id, day_index, blocks_json) VALUES (?, ?, ?)",
        (character_id, day_index, json.dumps(blocks)))
    store.commit()


def day_schedule(store, character_id, day_index, home_zone, work_zone,
                 work_start=480, work_end=960):
    """A simple home -> work -> home day."""
    set_schedule(store, character_id, day_index, [
        (0, work_start, "home", home_zone),
        (work_start, work_end, "work", work_zone),
        (work_end, 1440, "home", home_zone)])
