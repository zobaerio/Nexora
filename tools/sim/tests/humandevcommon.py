"""Session 06 test fixtures: a hand-built citizen world with the
city layer and the Session 06 education/health layer set up (no
economy/government layers — the Session 06 units must stand on
the citizen + city records, with government added only where a
test asks for it)."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))

from tools.sim import cities as cities_mod  # noqa: E402
from tools.sim import humandev as humandev_mod  # noqa: E402
from tools.sim.tests.common import (data, employ, make_household,  # noqa: E402
                                    make_person, make_store, rng)

GM = 480  # genesis game_minutes, matching the engine


def hd_world():
    """(store, data) with cities + Session 06 layer seeded."""
    store = make_store()
    d = data()
    r = rng()
    cities_mod.setup_cities(store, d, r)
    humandev_mod.setup_humandev(store, d, GM)
    store.commit()
    return store, d


def citizen(store, age=30, profession_id=None, first="Citizen",
            household=None, r=None):
    """A person, optionally employed, optionally placed in a
    household (a fresh one by default so residence city resolves
    to Rupsha). Returns the character_id."""
    r = r or rng()
    cid = make_person(store, age=age, first=first, game_minutes=GM,
                      r=r)
    if household is None:
        household, _ = make_household(store, [cid], game_minutes=GM)
    else:
        store.insert("household_members", household_id=household,
                     character_id=cid, role="member",
                     joined_at_game_minutes=GM)
        store.execute("UPDATE characters SET household_id = ?"
                      " WHERE character_id = ?", (household, cid))
    if profession_id:
        employ(store, data(), cid, profession_id, game_minutes=GM)
    return cid
