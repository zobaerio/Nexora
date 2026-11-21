"""Session 05 test fixtures: a hand-built citizen world with a
founded government (no economy/city layers — the government
units must stand on the citizen records alone)."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))

from tools.sim import government as gov  # noqa: E402
from tools.sim.tests.common import (data, make_household,  # noqa: E402
                                    make_person, make_store, rng,
                                    set_profile)

GM = 480  # genesis game_minutes, matching the engine


def funded_world(adults=40, seed_money=20000):
    """A store with `adults` adult citizens in households, each
    holding seed money from SYS-MARKET (the sim's money source),
    and the Session 05 government founded. Returns
    (store, data, citizen_ids)."""
    store = make_store()
    d = data()
    r = rng()
    ids = []
    batch = []
    for i in range(adults):
        cid = make_person(store, age=24 + (i % 30),
                          sex="female" if i % 2 else "male",
                          first=f"Citizen{i}", last="Test",
                          game_minutes=GM, r=r)
        ids.append(cid)
        batch.append(cid)
        if len(batch) == 4 or i == adults - 1:
            make_household(store, batch, game_minutes=GM)
            batch = []
    # A bench of judge material: citizens aged 35+ (the
    # judiciary rule needs age >= 30) with high intelligence.
    for i, cid in enumerate(ids):
        if 24 + (i % 30) >= 35:
            set_profile(store, cid, intelligence=85, discipline=80)
    for cid in ids:
        if seed_money:
            store.transfer("SYS-MARKET", cid, seed_money,
                           "seed_grant", GM,
                           note="test seed money",
                           transfer_key=f"seed:{cid}")
    gov.setup_government(store, d, r, GM)
    store.commit()
    return store, d, ids
