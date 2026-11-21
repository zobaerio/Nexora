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
        # Session 02 Unit 07: culture is configuration, loaded like
        # every other data file — never hardcoded in engine code.
        self.culture_file = _load_json("culture-profiles.json")
        self.culture_profiles = {p["id"]: p
                                 for p in self.culture_file["profiles"]}
        self.default_culture = self.culture_file["default_profile"]
        # Session 03: the District 1 blockout (plots/roads/junctions/
        # river geometry) and the GENERATED second city (citygen.py
        # output — labelled generated in the file itself).
        self.blockout = _load_json("district1-blockout.json")
        self.city2_file = _load_json("city2-shibnagar.json")
        self.econ = _load_economy_sim()
        # Session 04: the economy layer's configuration — goods
        # catalogue, production recipes, economy config (tax rules
        # referencing prices.json, crisis thresholds, scenarios).
        self.goods_file = _load_json("economy-goods.json")
        self.goods = {g["id"]: g for g in self.goods_file["goods"]}
        self.recipes_file = _load_json("production-recipes.json")
        self.recipes = self.recipes_file["recipes"]
        self.economy_config = _load_json("economy-config.json")
        # Session 05: the government layer's configuration —
        # country identity (grounded in the identity data), parties
        # and ideologies as data, election rules, policy/budget/
        # judiciary/integrity parameters, legal bounds.
        self.government_config = _load_json("government-config.json")
        # Session 06: the education / healthcare / human-development
        # layer's configuration — institution + facility identities
        # grounded in the building data, curricula as data, and
        # every health/disease/research rate labelled SIM MODEL.
        self.education_health_config = _load_json(
            "education-health-config.json")
        # Session 07: the transportation layer's data — vehicle
        # classes (speeds, capacities, fuel consumption, road
        # rights) and the transport configuration (transit routes
        # over real zones, congestion/condition models, and every
        # rate with no design basis labelled SIM MODEL there).
        self.vehicles_file = _load_json("vehicles.json")
        self.vehicle_types = {v["id"]: v
                              for v in self.vehicles_file["vehicles"]}
        self.transport_config = _load_json("transport-config.json")

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

    # -- Session 03: the two cities, one spec shape ---------------------
    def city_specs(self):
        """Both cities in one unified spec shape, so every urban
        system consumes authored and generated cities identically.
        Rupsha City's spec is assembled from the authored files;
        Shibnagar's is the generated file's own content."""
        rupsha = {
            "city_id": "rupsha_city", "name": "Rupsha City",
            "kind": "seeded", "district_label": "District 1",
            "zones": list(self.zones),
            "zone_boxes_m": self.blockout["zone_boxes_m"],
            "properties": self.buildings,
            "plots": self.blockout["plots"],
            "road_segments": self.blockout["road_segments"],
            "junctions": self.blockout["junctions"],
            "river": self.blockout["river"],
            "terrain_regions": None,  # derived in terrain.py
        }
        c2 = self.city2_file
        shibnagar = {
            "city_id": c2["city"]["city_id"], "name": c2["city"]["name"],
            "kind": c2["city"]["kind"], "district_label": None,
            "zones": list(c2["zones"]),
            "zone_boxes_m": c2["zone_boxes_m"],
            "properties": c2["properties"],
            "plots": c2["plots"],
            "road_segments": c2["road_segments"],
            "junctions": c2["junctions"],
            "river": c2["river"],
            "terrain_regions": c2["terrain_regions"],
        }
        return [rupsha, shibnagar]

    def city_spec(self, city_id):
        for spec in self.city_specs():
            if spec["city_id"] == city_id:
                return spec
        return None

    def zone_city(self, zone_id):
        """Which city a zone belongs to (None for non-city zones
        like professions' 'off_district')."""
        for spec in self.city_specs():
            if zone_id in spec["zones"]:
                return spec["city_id"]
        return None

    def all_buildings(self):
        """Every building of every city, keyed by building id."""
        out = {}
        for spec in self.city_specs():
            for b in spec["properties"]:
                out[b["id"]] = b
        return out

    def residential_stock_city(self, spec):
        """Residential unit slots of one city spec, honouring the
        part_of rule exactly like residential_stock() does for
        District 1."""
        units = []
        for b in spec["properties"]:
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

    def rent_index(self):
        """(building_id, unit_index) -> unit slot, over BOTH cities'
        residential stock. households.rent_of_property resolves
        through this so a unit is movable-to wherever it honestly
        exists; population genesis still uses residential_stock()
        (District 1 only) and is unchanged."""
        idx = {}
        for spec in self.city_specs():
            for u in self.residential_stock_city(spec):
                idx[(u["building_id"], u["unit_index"])] = u
        return idx
