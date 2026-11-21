"""Shared fixtures for the Session 01 test suite (stdlib unittest)."""
import os
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                    "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.sim import identity as identity_mod  # noqa: E402
from tools.sim.dataio import WorldData  # noqa: E402
from tools.sim.persistence import Store  # noqa: E402
from tools.sim.rng import SimRng  # noqa: E402

DATA = None


def data():
    global DATA
    if DATA is None:
        DATA = WorldData()
    return DATA


def rng(seed="test-seed"):
    return SimRng(seed)


def make_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    store = Store(path)
    store.init_world("test-seed")
    return store


def make_person(store, age=30, sex="male", sim_tier="full",
                profession_id=None, first="Test", last="Person",
                household_id=None, game_minutes=480, r=None):
    r = r or rng()
    born = game_minutes - age * 365 * 1440 - 100 * 1440
    return identity_mod.create_person(
        store, r, first_name=first, last_name=last, sex=sex,
        born_at_game_minutes=born, household_id=household_id,
        profession_id=profession_id, sim_tier=sim_tier,
        game_minutes=game_minutes)


def set_profile(store, character_id, **attrs):
    sets = ", ".join(f"{k} = ?" for k in attrs)
    store.execute(f"UPDATE personality_profiles SET {sets}"
                  " WHERE character_id = ?",
                  tuple(attrs.values()) + (character_id,))


def set_needs(store, character_id, **values):
    sets = ", ".join(f"{k} = ?" for k in values)
    store.execute(f"UPDATE needs_state SET {sets} WHERE character_id = ?",
                  tuple(values.values()) + (character_id,))


def set_emotions(store, character_id, **values):
    sets = ", ".join(f"{k} = ?" for k in values)
    store.execute(f"UPDATE emotional_state SET {sets}"
                  " WHERE character_id = ?",
                  tuple(values.values()) + (character_id,))


def make_household(store, member_ids, game_minutes=480, rent=4000,
                   market_value=750000, head_index=0):
    """A household + property + tenancy for the given members."""
    hid = store.next_id("HH", "households", "household_id")
    pid = store.next_id("PR", "properties", "property_id")
    store.insert("properties", property_id=pid,
                 property_type="apartment", district_id="d1_midtown",
                 address_label="Test Block #1", tier=3, status="rented",
                 market_value=market_value, building_ref="test",
                 unit_index=0)
    store.insert("households", household_id=hid, name="Test Household",
                 home_property_id=pid, district_id="d1_midtown",
                 created_at_game_minutes=game_minutes)
    for i, cid in enumerate(member_ids):
        store.insert("household_members", household_id=hid,
                     character_id=cid,
                     role="head" if i == head_index else "member",
                     joined_at_game_minutes=game_minutes)
        store.execute("UPDATE characters SET household_id = ?"
                      " WHERE character_id = ?", (hid, cid))
    tid = store.next_id("TN", "tenancies", "tenancy_id")
    store.insert("tenancies", tenancy_id=tid, property_id=pid,
                 tenant_household_id=hid, rent_per_month=rent,
                 started_at_game_minutes=game_minutes)
    return hid, pid


def employ(store, data_obj, character_id, profession_id, tier=1,
           game_minutes=480):
    eid = store.next_id("EM", "employments", "employment_id")
    store.insert("employments", employment_id=eid,
                 character_id=character_id, profession_id=profession_id,
                 tier=tier,
                 wage_per_month=data_obj.wage_at(profession_id, tier),
                 started_at_game_minutes=game_minutes)
    return eid
