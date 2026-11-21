"""Loading of the merged design data — the sim's only data inputs.

Integrates, never duplicates: every fact is read from the canonical
merged file named in tools/sim/__init__.py. The economy functions are
imported from tools/economy_sim.py so this engine and the balance
simulator can never drift apart arithmetically.
"""
import importlib.util
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_HERE, "..", "..", "data")
_TOOLS_DIR = os.path.join(_HERE, "..")


def _load_json(name):
    with open(os.path.join(DATA_DIR, name)) as f:
        return json.load(f)


def _load_economy_sim():
    path = os.path.join(_TOOLS_DIR, "economy_sim.py")
    spec = importlib.util.spec_from_file_location("nexora_economy_sim", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class WorldData:
    """All merged data, indexed for the engine."""

    def __init__(self):
        self.professions_file = _load_json("professions.json")
        self.professions = {p["id"]: p
                            for p in self.professions_file["professions"]}
        self.schedules_file = _load_json("npc-schedules.json")
        self.schedules = {s["profession_id"]: s
                          for s in self.schedules_file["schedules"]}
        self.life_stage_templates = self.schedules_file["life_stage_templates"]
        self.buildings_file = _load_json("buildings-district1.json")
        self.buildings = self.buildings_file["properties"]
        self.zones = self.buildings_file["zones"]
        self.prices = _load_json("prices.json")
        self.weather = _load_json("weather-presets.json")
        self.weather_presets = {p["id"]: p for p in self.weather["presets"]}
        self.econ = _load_economy_sim()

    # -- canonical accessors -------------------------------------------------
    # Employment tiers run 1..5 (professions.json progression), but
    # the canonical wage table has three bands — tiers 3-5 are mastery
    # ranks paid at the senior band. One mapping, used everywhere.
    TIER_WAGE_KEYS = ("entry", "mid", "senior", "senior", "senior")

    def wage(self, profession_id, tier):
        """Monthly gross wage — canonical source: prices.json."""
        row = next(w for w in self.prices["wages_monthly"]
                   if w["profession_id"] == profession_id)
        return row[tier]

    def wage_at(self, profession_id, tier_int):
        return self.wage(profession_id,
                         self.TIER_WAGE_KEYS[tier_int - 1])

    def business_tier_key(self, tier_int):
        return self.TIER_WAGE_KEYS[tier_int - 1]

    def pay_schedule(self, profession_id):
        row = next(w for w in self.prices["wages_monthly"]
                   if w["profession_id"] == profession_id)
        return row["pay_schedule"]

    def starting_balance(self, profession_id):
        return self.professions[profession_id].get("starting_balance_ncr", 0)

    def residential_stock(self):
        """Residential unit slots honouring the part_of rule (audit §2):
        single-unit entries counted inside their parents are excluded.
        Returns a list of unit dicts (building, unit_index, rent, tier,
        zone) — exactly 140 entries for District 1."""
        units = []
        for b in self.buildings:
            if b["property_type"] not in ("apartment", "house"):
                continue
            if "part_of" in b:
                continue
            for i in range(b.get("units", 1)):
                units.append({
                    "building_id": b["id"],
                    "building_name": b["name"],
                    "unit_index": i,
                    "rent": b["rent_monthly_ncr_per_unit"],
                    "buy_price": b.get("buy_price_ncr_per_unit"),
                    "tier": b["tier"],
                    "zone_id": b["zone_id"],
                    "property_type": b["property_type"],
                })
        return units

    def workplaces(self):
        """Non-residential buildings usable as workplace anchors."""
        return [b for b in self.buildings
                if b["property_type"] not in ("apartment", "house")
                and "part_of" not in b]
