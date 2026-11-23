"""The simulation engine — tick loop binding Units 01-10 together.

Update model (the audit's "scheduled/tiered updates", stated
plainly): agents are processed at *schedule block boundaries* and at
a daily rollover — never per frame, never per minute. A day runs:

  1. Weather for the day is drawn from a seeded stream (persisted in
     daily_weather, so a restart cannot re-roll it). District 1
     weights; snow is zone-gated away by the data and never drawn.
  2. Every living agent's schedule is instantiated from its GDD-06
     template (Unit 04) with yesterday's needs bending it, the day's
     weather interrupting it, and a decision-set rest day honoured.
     Blocks are asserted to cover the full day exactly once — the
     audit's schedule-coverage criterion is an engine invariant, not
     a hope.
  3. Block boundaries are processed in time order: needs accrue per
     activity (Unit 05), meals happen inside home blocks, and agents
     starting leisure/break/errand blocks at the same anchor meet
     (Unit 10).
  4. Daily rollover: needs' daily components, emotional regression
     (Unit 06), life-cycle checks — transitions, retirement, death
     with its inheritance cascade (Unit 09), one decision per adult
     (Unit 08), weekly relationship drift (Unit 07).
  5. Every 30th day, the monthly settlement runs the household
     economy through the ledger using economy_sim.py's own functions
     (Unit X reconciliation): wages net of marginal tax, business
     P&L net of the 8% business tax, rent, banded living costs with
     the household scaling documented in _living_costs, lifestyle
     uplift, cab rental for taxi drivers, and the elder pension.

Money timing note: economy_sim models daily/per-fare pay timing for
its min-balance trajectory; the headless core settles all income
monthly (amounts identical, timing simplified) — stated here and in
the Session 01 report, and the reconciliation test compares monthly
amounts, not trajectories.

PENSION_NCR_PER_MONTH = 3500 is a SIM ASSUMPTION: the merged data
defines no pension figure (GDD-01 mentions pensions as an income
kind; prices.json has none). It is labelled wherever it surfaces.
"""
import json

from . import analytics as analytics_mod
from . import banking as banking_mod
from . import business as business_mod
from . import cities as cities_mod
from . import crises as crises_mod
from . import govfinance as govfinance_mod
from . import indicators as indicators_mod
from . import labour as labour_mod
from . import market as market_mod
from . import trade as trade_mod
from . import community as community_mod
from . import conflicts as conflicts_mod
from . import construction as construction_mod
from . import distribution as distribution_mod
from . import growth as growth_mod
from . import infrastructure as infrastructure_mod
from . import regional as regional_mod
from . import services as services_mod
from . import culture as culture_mod
from . import decisions as decisions_mod
from . import education as education_mod
from . import emotions as emotions_mod
from . import events as events_mod
from . import family_economy
from . import government as gov_mod
from . import health as health_mod
from . import humandev as humandev_mod
from . import generations as generations_mod
from . import kinship as kinship_mod
from . import mobility as mobility_mod
from . import social as social_mod
from . import transport as transport_mod
from . import environment as environment_mod
from . import agents as agents_mod
from . import integration as integration_mod
from . import identity as identity_mod
from . import interaction as interaction_mod
from . import lifecycle
from . import memory as memory_mod
from . import needs as needs_mod
from . import population as population_mod
from . import relationships as rel
from . import scheduler
from .dataio import WorldData
from .persistence import Store
from .rng import SimRng

PENSION_NCR_PER_MONTH = 3500  # SIM ASSUMPTION — see module docstring
WEATHER_WEIGHTS = (("clear_day", 34), ("sunrise_clear", 8),
                   ("night_clear", 6), ("cloudy", 20), ("rain", 16),
                   ("storm", 5), ("fog", 6), ("windy", 5))
BUSINESS_PROFESSIONS = ("shop_owner", "business_owner")


class Simulation:
    def __init__(self, db_path, seed="nexora-1"):
        self.store = Store(db_path)
        self.store.init_world(seed)
        self.data = WorldData()
        self.rng = SimRng(self.store.world()["sim_seed"])

    def close(self):
        self.store.close()

    # -- setup ---------------------------------------------------------------
    def generate_population(self, target=240):
        stats = population_mod.generate(self.store, self.data, self.rng,
                                        target_population=target)
        # Session 03: the city layer bootstraps with the world
        # (idempotent; hand-built test worlds that never call this
        # simply have no city layer and every city pass no-ops).
        cities_mod.setup_cities(self.store, self.data, self.rng)
        # Session 04: the economy layer bootstraps the same way
        # (commercial stock, genesis businesses, the bank, market
        # prices) — hand-built worlds have no economy layer and
        # every Session 04 pass no-ops for them.
        stats["economy"] = business_mod.setup_economy(
            self.store, self.data, self.rng)
        # Session 05: the national government is founded with the
        # world (one country, both cities, caretaker leadership
        # until the month-1 election) — hand-built worlds have no
        # government layer and every Session 05 pass no-ops.
        stats["government"] = gov_mod.setup_government(
            self.store, self.data, self.rng, 480)
        # Session 06: the education / healthcare / human
        # development layer seeds with the world (institutions
        # and facilities from the real buildings, health profiles
        # for the population) — hand-built worlds have no Session
        # 06 layer and every Session 06 pass no-ops for them.
        stats["humandev"] = humandev_mod.setup_humandev(
            self.store, self.data, 480)
        # Session 07: the transportation layer seeds last (its
        # fleets and trucks read the economy's businesses and the
        # population's taxi drivers) — hand-built worlds have no
        # Session 07 layer and every Session 07 pass no-ops.
        stats["transport"] = transport_mod.setup_transport(
            self.store, self.data, 480)
        # Session 08: the environment layer seeds after the city
        # layer exists (water state, soil, vegetation, wildlife)
        # — hand-built worlds have no Session 08 layer and every
        # Session 08 pass no-ops.
        stats["environment"] = environment_mod.setup_environment(
            self.store, self.data, 480)
        # Session 09: the agent coordination layer seeds last —
        # its registry reads every actor the earlier layers
        # created (citizens, businesses, institutions, cities,
        # the government). Hand-built worlds have no agent layer
        # and every Session 09 pass no-ops.
        stats["agents"] = agents_mod.setup_agents(
            self.store, self.data, 480)
        # Session 10: the integration layer seeds last of all —
        # its event registry indexes every earlier layer's
        # history tables, its technology derivation reads the
        # research/education records, and its resource balance
        # reads every layer's stores. Hand-built worlds have no
        # integration layer and every Session 10 pass no-ops.
        stats["integration"] = integration_mod.setup_integration(
            self.store, self.data, 480)
        return stats

    def weather_for_day(self, day_index):
        row = self.store.row("SELECT preset_id FROM daily_weather"
                             " WHERE day_index = ?", (day_index,))
        if row:
            return row["preset_id"]
        names = [n for n, _ in WEATHER_WEIGHTS]
        weights = [w for _, w in WEATHER_WEIGHTS]
        preset = self.rng.stream("weather", day_index).choices(
            names, weights=weights)[0]
        self.store.insert("daily_weather", day_index=day_index,
                          preset_id=preset)
        return preset

    # -- one day ---------------------------------------------------------------
    def run_day(self):
        store, data = self.store, self.data
        world = store.world()
        day = world["day_index"]
        day_start, day_end = day * 1440, day * 1440 + 1440
        preset = self.weather_for_day(day)
        effects = data.weather_presets[preset].get("gameplay_effects") or []
        storm = "npc_cover_seeking_strong" in effects

        agents = store.rows(
            "SELECT * FROM characters WHERE is_system = 0"
            " AND died_at_game_minutes IS NULL ORDER BY character_id")
        home_zone = {r["household_id"]: r["district_id"] for r in
                     store.rows("SELECT h.household_id, p.district_id"
                                " FROM households h JOIN properties p"
                                " ON p.property_id = h.home_property_id")}
        home_tier = {r["household_id"]: r["tier"] for r in
                     store.rows("SELECT h.household_id, p.tier"
                                " FROM households h JOIN properties p"
                                " ON p.property_id = h.home_property_id")}

        schedules, events = {}, []
        work_hours, study_hours = {}, {}
        for char in agents:
            cid = char["character_id"]
            age = identity_mod.age_years(char["born_at_game_minutes"],
                                         day_start)
            emp = store.row("SELECT * FROM employments"
                            " WHERE character_id = ?"
                            " AND ended_at_game_minutes IS NULL", (cid,))
            template_id, is_ls = lifecycle.template_id_for(
                store, cid, age, emp)
            state = store.row("SELECT rest_day FROM agent_state"
                              " WHERE character_id = ?", (cid,))
            prof = data.professions.get(emp["profession_id"]) if emp \
                else None
            ctx = {"character_id": cid, "template_id": template_id,
                   "is_life_stage": is_ls,
                   "home_zone": home_zone.get(char["household_id"],
                                              "d1_old_town"),
                   "workplace_zone": prof["workplace_zone"] if prof
                   else "d1_old_town"}
            blocks, _ = scheduler.instantiate(
                data, ctx, day, self.rng,
                needs=needs_mod.get_needs(store, cid), traits=char,
                weather_effects=effects,
                rest_day=bool(state and state["rest_day"]))
            total = sum(b["end"] - b["start"] for b in blocks)
            assert total == 1440, f"schedule coverage broken for {cid}"
            schedules[cid] = blocks
            store.execute(
                "INSERT OR REPLACE INTO instantiated_schedules"
                " (character_id, day_index, blocks_json) VALUES (?, ?, ?)",
                (cid, day, json.dumps(blocks)))
            store.execute(
                "UPDATE agent_state SET schedule_template_id = ?,"
                " rest_day = 0 WHERE character_id = ?", (template_id, cid))
            for i, b in enumerate(blocks):
                events.append((b["start"], cid, i))
                hours = (b["end"] - b["start"]) / 60.0
                if b["activity"] == "work":
                    work_hours[cid] = work_hours.get(cid, 0) + hours
                elif b["activity"] == "study":
                    study_hours[cid] = study_hours.get(cid, 0) + hours

        # Block boundaries in time order.
        events.sort()
        current, meals, groups = {}, {}, {}

        def flush_groups(at_minute):
            for (zone, loc, act), members in sorted(groups.items()):
                interaction_mod.process_group(
                    store, self.rng, members, act, at_minute)
            groups.clear()

        prev_minute = None
        for minute, cid, idx in events:
            if prev_minute is not None and minute != prev_minute:
                flush_groups(prev_minute)
            prev_minute = minute
            block = schedules[cid][idx]
            prev = current.get(cid)
            if prev is not None:
                needs_mod.apply_activity(
                    store, cid, prev["activity"], prev["location"],
                    (minute - prev["start"]) / 60.0, minute)
            current[cid] = block
            store.execute(
                "UPDATE agent_state SET current_activity = ?,"
                " current_location = ?, current_zone = ?"
                " WHERE character_id = ?",
                (block["activity"], block["location"], block["zone"], cid))
            if block["activity"] == "home" \
                    and block["end"] - block["start"] >= 45 \
                    and meals.get(cid, 0) < 2:
                needs_mod.apply_activity(store, cid, "home", "home", 0,
                                         minute, meal=True)
                meals[cid] = meals.get(cid, 0) + 1
            if block["activity"] in interaction_mod.INTERACTION_ACTIVITIES:
                key = (block["zone"], block["location"], block["activity"])
                groups.setdefault(key, []).append(cid)
        flush_groups(prev_minute)
        for cid, block in current.items():
            needs_mod.apply_activity(
                store, cid, block["activity"], block["location"],
                (day_end - block["start"]) / 60.0, day_end)

        # Family time at home.
        for hid in sorted({c["household_id"] for c in agents
                           if c["household_id"]}):
            interaction_mod.household_time(store, hid, day_end)

        # Skill growth from the day's work and study.
        for cid, hours in work_hours.items():
            emp = store.row("SELECT profession_id FROM employments"
                            " WHERE character_id = ?"
                            " AND ended_at_game_minutes IS NULL", (cid,))
            if emp:
                skills = data.professions[emp["profession_id"]][
                    "primary_skills"]
                decisions_mod.add_skill_xp(store, cid, skills[0],
                                           int(hours * 0.5))
                if len(skills) > 1:
                    decisions_mod.add_skill_xp(store, cid, skills[1],
                                               int(hours * 0.25))
        for cid, hours in study_hours.items():
            # Session 02 Unit 08: study accrues by enrolment —
            # school students into subject_knowledge under the
            # GDD-11 cap, college students into their programme
            # skill under its cap, everyone else as before.
            if education_mod.is_school_student(store, cid):
                education_mod.accrue_school_study(store, cid, hours)
            elif education_mod.college_enrolment(store, cid):
                education_mod.accrue_college_study(store, cid, hours)
            else:
                decisions_mod.add_skill_xp(store, cid,
                                           "subject_knowledge",
                                           int(hours))

        # Session 03 Unit 11: construction projects advance with
        # the day (weather-halting outdoor stages on storm days).
        construction_mod.daily_progress(self.store, self.data,
                                        self.rng, day, preset, day_end)

        # Daily rollover.
        used_names = {(c["first_name"], c["last_name"]) for c in
                      store.rows("SELECT first_name, last_name"
                                 " FROM characters WHERE is_system = 0")}
        estimates = self._household_estimates()
        for char in agents:
            cid = char["character_id"]
            fresh = store.row("SELECT * FROM characters"
                              " WHERE character_id = ?", (cid,))
            if fresh is None or fresh["died_at_game_minutes"] is not None:
                continue
            age = identity_mod.age_years(fresh["born_at_game_minutes"],
                                         day_end)
            hid = fresh["household_id"]
            needs_mod.daily_update(
                store, cid, age=age,
                home_tier=home_tier.get(hid, 2),
                balance=store.balance(cid),
                monthly_cost_estimate=estimates.get(hid, 9000),
                studied_today=study_hours.get(cid, 0) > 0,
                storm_today=storm, game_minutes=day_end)
            emotions_mod.daily_regress(store, cid)
            if lifecycle.daily_check(store, self.rng, fresh, day,
                                     day_end, data=data) == "died":
                continue
            decisions_mod.decide(store, data, self.rng, fresh, day,
                                 day_end, used_names)
        # Session 06: the health layer's daily cadence — onsets
        # from the day's actual exposures, disease transmission,
        # clinic queues, course resolution, rest bends for
        # tomorrow. No-ops when the layer was never set up.
        if humandev_mod.is_setup(store):
            health_mod.daily_pass(store, data, self.rng, day, day_end,
                                  preset)
        # Session 07: the day's physical movement — trips from the
        # day's instantiated schedules, clinic journeys and
        # emergency referrals from today's Session 06 records, and
        # the traffic those trips create. Runs after the health
        # pass so today's visits exist. No-ops when not set up.
        if transport_mod.is_setup(store):
            transport_mod.daily_pass(store, data, self.rng, day,
                                     day_end, preset)
        # Session 08: the environmental day — regional weather,
        # hydrology, flood episodes, configured disaster
        # scenarios, recovery. Runs last so today's flood road
        # closures govern tomorrow's routing.
        if environment_mod.is_setup(store):
            environment_mod.daily_pass(store, data, self.rng, day,
                                       day_end)
        # Session 09: disaster coordination tracks the day's
        # Session 08 response while a disaster is live (the pass
        # itself checks and no-ops cheaply otherwise).
        if agents_mod.is_setup(store):
            agents_mod.daily_pass(store, data, self.rng, day,
                                  day_end)
        if day % 7 == 6:
            rel.weekly_drift(store, day_end)
            self._weekly_social(day_end)
            # Session 03 Unit 07: infrastructure loads recomputed
            # weekly from residents + workplaces.
            infrastructure_mod.weekly_update(store, data, day_end)
        # Session 02 Unit 09: culture festivals fall on their
        # calendar day (day-of-year), for the households whose
        # culture celebrates them.
        for profile, festival in culture_mod.festivals_on(
                data, day % 365):
            for h in store.rows("SELECT household_id FROM households"
                                " WHERE dissolved_at_game_minutes"
                                " IS NULL"):
                culture_mod.ensure_culture(store, data,
                                           h["household_id"], day_end)
            events_mod.run_festival(store, data, self.rng, profile,
                                    festival, day_end)
        if (day + 1) % 30 == 0:
            self._settle_month(day)
            self._monthly_social(day)
            self._monthly_economy(day)
            self._monthly_city(day)
            self._monthly_economy_close(day)
            self._monthly_government(day)
            self._monthly_humandev(day)
            self._monthly_transport(day)
            self._monthly_environment(day)
            self._monthly_agents(day)
            self._monthly_integration(day)
        # Session 10: the unified event registry syncs at the
        # very end of the day — after every daily pass, the
        # festival block and (on month-end days) every monthly
        # pass — so the day's events from all subsystems are
        # indexed the day they happen.
        if integration_mod.is_setup(store):
            integration_mod.daily_pass(store, data, self.rng, day,
                                       day_end)
        store.set_world(game_minutes=day_end, day_index=day + 1,
                        weather_preset=preset)
        store.commit()

    # -- Session 02 social cadences -------------------------------------
    # Weekly and monthly batch passes, in the same scheduled-update
    # spirit as Session 01: no per-tick full scans, every pass is a
    # bounded sweep over the tables its unit owns.

    def _weekly_social(self, day_end):
        store, data = self.store, self.data
        social_mod.neighbour_gathering(store, self.rng, data, day_end)
        social_mod.weekly_decay(store, day_end)
        community_mod.weekly_update(store, data, self.rng, day_end)
        conflicts_mod.weekly_scan(store, self.rng, data, day_end)
        kinship_mod.ensure_guardianship(store, day_end)

    def _monthly_social(self, last_day):
        store, data = self.store, self.data
        game_minutes = (last_day + 1) * 1440
        for h in store.rows("SELECT household_id FROM households"
                            " WHERE dissolved_at_game_minutes IS NULL"):
            culture_mod.ensure_culture(store, data, h["household_id"],
                                       game_minutes)
        education_mod.monthly_sweep(store, data, game_minutes)
        events_mod.celebrate_life_events(store, data, self.rng,
                                         game_minutes)
        events_mod.family_gathering(store, data, self.rng, game_minutes)
        for zone in sorted(data.zones):
            events_mod.public_meeting(store, data, self.rng, zone,
                                      game_minutes)
        mobility_mod.monthly_check(store, data, game_minutes)
        generations_mod.knowledge_transfer(store, data, game_minutes)
        generations_mod.record_history_sweep(store, game_minutes)
        kinship_mod.maybe_adopt(store, data, game_minutes)

    # -- Session 03 city cadence ------------------------------------
    # Monthly, after the economy settlement and the society passes
    # (migration reads settled debt; services read settled taxes).
    # Every pass no-ops when the city layer was never set up.

    def _monthly_city(self, last_day):
        store, data = self.store, self.data
        if not cities_mod.is_setup(store):
            return
        game_minutes = (last_day + 1) * 1440
        month_index = (last_day + 1) // 30
        month_days = range(last_day - 29, last_day + 1)
        storm_days = [self.weather_for_day(d) for d in
                      month_days].count("storm")
        infrastructure_mod.monthly_effects(store, data, game_minutes)
        services_mod.monthly_pass(store, data, month_index,
                                  game_minutes, storm_days=storm_days)
        distribution_mod.monthly_migration(store, data, game_minutes)
        growth_mod.monthly_growth(store, data, month_index,
                                  game_minutes)
        flows = regional_mod.monthly_flows(store, data, month_index,
                                           game_minutes)
        # Session 04 Unit 13: the flows become physical (inventory
        # moves between the cities) and fiscal (tariffs collect).
        trade_mod.settle_trade(store, data, month_index,
                               game_minutes)
        # Session 07: each flow also leaves a freight shipment
        # record (route + congested arrival over the bridge).
        if transport_mod.is_setup(store):
            transport_mod.record_trade_shipments(
                store, data, month_index, game_minutes, flows)
        analytics_mod.record_snapshots(store, data, month_index,
                                       game_minutes)
        cities_mod.refresh_registry(store, data, game_minutes)

    # -- Session 04 economy cadence ---------------------------------
    # Monthly, in two halves around the city cadence: the economy
    # half runs after the settlement (production, supply chains,
    # consumption allocation, prices, commercial rent, the labour
    # market, banking, business P&L, dividends, distress); the
    # closing half runs after the city cadence, when municipal
    # budgets and trade flows for the month exist (government
    # finance, indicators, crisis detection). Every pass no-ops
    # when the economy layer was never set up.

    def _monthly_economy(self, last_day):
        store, data = self.store, self.data
        if not business_mod.is_setup(store):
            return
        game_minutes = (last_day + 1) * 1440
        month_index = (last_day + 1) // 30
        month_days = range(last_day - 29, last_day + 1)
        storm_days = [self.weather_for_day(d) for d in
                      month_days].count("storm")
        effects = crises_mod.active_effects(store)
        market_mod.production_pass(store, data, month_index,
                                   game_minutes, storm_days=storm_days)
        orders = market_mod.supply_chain_pass(store, data,
                                              month_index,
                                              game_minutes)
        # Session 07: the orders become physical freight
        # shipments (vehicle, route, congested arrival, delay).
        # The money already moved inside the supply pass; this
        # records the journey only. No-ops when not set up.
        if transport_mod.is_setup(store):
            transport_mod.record_shipments(store, data, month_index,
                                           game_minutes, orders)
        # Converters run once more on what the supply chain just
        # delivered, so this month's inputs become this month's
        # food and garments rather than next month's.
        market_mod.production_pass(store, data, month_index,
                                   game_minutes, storm_days=storm_days,
                                   converters_only=True)
        market_mod.retail_allocation(store, data, month_index,
                                     game_minutes)
        market_mod.update_prices(store, data, month_index,
                                 game_minutes)
        business_mod.pay_commercial_rent(store, data, month_index,
                                         game_minutes)
        labour_mod.monthly_pass(
            store, data, self.rng, month_index, game_minutes,
            hiring_freeze=effects["hiring_freeze"])
        banking_mod.monthly_pass(store, data, month_index,
                                 game_minutes)
        business_mod.record_monthly_pnl(store, data, month_index,
                                        game_minutes)
        banking_mod.pay_dividends(store, data, month_index,
                                  game_minutes)
        business_mod.evaluate_distress(store, data, month_index,
                                       game_minutes)

    def _monthly_economy_close(self, last_day):
        store, data = self.store, self.data
        if not business_mod.is_setup(store):
            return
        game_minutes = (last_day + 1) * 1440
        month_index = (last_day + 1) // 30
        govfinance_mod.monthly_snapshot(store, data, month_index,
                                        game_minutes)
        indicators_mod.snapshot_month(store, data, month_index,
                                      game_minutes)
        crises_mod.detect(store, data, month_index, game_minutes)

    # -- Session 05 government cadence ---------------------------
    # Monthly, last: the government reads the settled month
    # (wages, taxes, budgets, indicators, trade) and acts on it —
    # opinion, elections, civil service, allowances, treasury
    # allocation, the annual budget, decisions, policies,
    # courts, police, audit, diplomacy. No-ops when no
    # government was founded.

    def _monthly_government(self, last_day):
        store, data = self.store, self.data
        if not gov_mod.is_setup(store):
            return
        game_minutes = (last_day + 1) * 1440
        month_index = (last_day + 1) // 30
        gov_mod.monthly_pass(store, data, self.rng, month_index,
                             game_minutes)

    # -- Session 06 human development cadence -------------------
    # Monthly, last: institutions, academics, healthcare budgets,
    # disease surveillance, health profiles, wellbeing, research
    # and the human-development indicators all read the settled
    # month. No-ops when the layer was never set up.

    def _monthly_humandev(self, last_day):
        store, data = self.store, self.data
        if not humandev_mod.is_setup(store):
            return
        game_minutes = (last_day + 1) * 1440
        month_index = (last_day + 1) // 30
        humandev_mod.monthly_pass(store, data, self.rng, month_index,
                                  game_minutes)

    # -- Session 07 transportation cadence ----------------------
    # Monthly, after human development: taxi cabs for new
    # drivers, the vehicle purchase sweep, fleet maintenance,
    # the transit subsidy, migration journeys and the monthly
    # transport statistics. No-ops when the layer was never
    # set up.

    def _monthly_transport(self, last_day):
        store, data = self.store, self.data
        if not transport_mod.is_setup(store):
            return
        game_minutes = (last_day + 1) * 1440
        month_index = (last_day + 1) // 30
        transport_mod.monthly_pass(store, data, self.rng, month_index,
                                   game_minutes)

    # -- Session 08 environment cadence -------------------------
    # Monthly, last: agriculture cycles, pollution indices,
    # vegetation/wildlife drift and the climate trend snapshots
    # all read the settled month (transport statistics included).

    def _monthly_environment(self, last_day):
        store, data = self.store, self.data
        if not environment_mod.is_setup(store):
            return
        game_minutes = (last_day + 1) * 1440
        month_index = (last_day + 1) // 30
        environment_mod.monthly_pass(store, data, self.rng,
                                     month_index, game_minutes)

    # -- Session 09 agent coordination cadence -------------------
    # Monthly, last of all: the coordination cycle (registry,
    # multi-level memory, extended goals, scored forecasts,
    # disaster coordination, city/national assessments) reads
    # every other layer's settled month. No-ops when the agent
    # layer was never set up.

    def _monthly_agents(self, last_day):
        store, data = self.store, self.data
        if not agents_mod.is_setup(store):
            return
        game_minutes = (last_day + 1) * 1440
        month_index = (last_day + 1) // 30
        agents_mod.monthly_pass(store, data, self.rng, month_index,
                                game_minutes)

    # -- Session 10 integration cadence -----------------------
    # Monthly, last of all: technology levels are recomputed
    # from the settled month's research + certification records,
    # and configured global scenarios resolve after their
    # duration. No-ops when the layer was never set up.

    def _monthly_integration(self, last_day):
        store, data = self.store, self.data
        if not integration_mod.is_setup(store):
            return
        game_minutes = (last_day + 1) * 1440
        month_index = (last_day + 1) // 30
        integration_mod.monthly_pass(store, data, self.rng,
                                     month_index, game_minutes)

    def run_days(self, n):
        for _ in range(n):
            self.run_day()

    # -- economy ---------------------------------------------------------------
    @staticmethod
    def _banded(table, band):
        """A prices.json banded value. The data nulls inapplicable
        cells (no car costs at the lower band, no public-transport
        price at the upper band — economy_sim's single-profession
        households never mix the two). A mixed household falls back
        to the nearest defined band; the fallback is documented in
        the Session 01 report as a data gap."""
        if table.get(band) is not None:
            return table[band]
        for fallback in ("mid", "lower", "upper"):
            if table.get(fallback) is not None:
                return table[fallback]
        return 0

    def _living_costs(self, band, adults, children, earner_pids):
        """Monthly living costs from prices.json, scaled from
        economy_sim's single-adult model: food and clothing scale
        with household size (children at half/third), transport is
        per earner (car for economy_sim's CAR_PROFESSIONS), eating
        out per earner, utilities, services and medical flat per
        household. A one-adult household reduces exactly to
        economy_sim's numbers — that is the reconciliation contract.
        (Queue 7 / Unit AJ: the medical line is flat per household
        here, matching economy_sim v4's per-household band charge.)"""
        lc = self.data.prices["living_costs_monthly"]
        econ = self.data.econ
        transport = sum(
            self._banded(lc["transport_own_car_fuel_upkeep"], band)
            if pid in econ.CAR_PROFESSIONS
            else self._banded(lc["transport_public_bus_rickshaw"], band)
            for pid in earner_pids)
        return {
            "food": round(lc["food_home_cooking"][band]
                          * (adults + 0.5 * children)),
            "utilities": lc["utilities_power_water_internet"][band],
            "clothing": round(lc["clothing_personal"][band]
                              * (adults + 0.3 * children)),
            "transport": transport,
            "eating": lc["eating_out_monthly"][band]
                      * max(1, len(earner_pids)),
            "services": lc["household_services_monthly"][band],
            "medical": lc["medical_monthly"][band],
        }

    def _households(self):
        store = self.store
        out = []
        for h in store.rows("SELECT * FROM households"
                            " WHERE dissolved_at_game_minutes IS NULL"):
            members = store.rows(
                "SELECT c.* FROM household_members hm JOIN characters c"
                " ON c.character_id = hm.character_id"
                " WHERE hm.household_id = ?"
                " AND hm.left_at_game_minutes IS NULL"
                " AND c.died_at_game_minutes IS NULL"
                " ORDER BY c.character_id", (h["household_id"],))
            if members:
                out.append((h, members))
        return out

    def _household_estimates(self):
        """Per-household monthly cost estimate (rent + living) used
        by the financial need."""
        store = self.store
        world = store.world()
        now = world["game_minutes"]
        estimates = {}
        for h, members in self._households():
            earners = [m for m in members if store.row(
                "SELECT 1 FROM employments WHERE character_id = ?"
                " AND ended_at_game_minutes IS NULL",
                (m["character_id"],))]
            adults = sum(1 for m in members if identity_mod.age_years(
                m["born_at_game_minutes"], now) >= 18)
            children = len(members) - adults
            band = "lower"
            if earners:
                emp = store.row("SELECT profession_id FROM employments"
                                " WHERE character_id = ?"
                                " AND ended_at_game_minutes IS NULL",
                                (earners[0]["character_id"],))
                band = self.data.econ.band_for(
                    self.data.wage(emp["profession_id"], "entry"))
            living = self._living_costs(
                band, max(adults, 1), children,
                [store.row("SELECT profession_id FROM employments"
                           " WHERE character_id = ?"
                           " AND ended_at_game_minutes IS NULL",
                           (e["character_id"],))["profession_id"]
                 for e in earners])
            tenancy = store.row("SELECT rent_per_month FROM tenancies"
                                " WHERE tenant_household_id = ?"
                                " AND ended_at_game_minutes IS NULL",
                                (h["household_id"],))
            rent = tenancy["rent_per_month"] if tenancy else 0
            estimates[h["household_id"]] = rent + sum(living.values())
        return estimates

    def _pay(self, from_id, to_id, amount, reason, game_minutes, note):
        """Pay what the payer can afford; return the unpaid remainder.
        Partial payment is a simulated fact (arrears), never a crash."""
        if amount <= 0:
            return 0
        balance = self.store.balance(from_id)
        paid = min(amount, balance)
        if paid > 0:
            self.store.transfer(from_id, to_id, paid, reason,
                                game_minutes, note=note)
        return amount - paid

    def _pay_purchase(self, from_id, amount, game_minutes, note):
        """Pay a household market purchase. With the Session 04
        economy live, the configured sales tax is split out of the
        amount (data/economy-config.json — a SIM MODEL rate): the
        household pays exactly what it paid before the tax existed;
        the tax share routes to SYS-CITY with reason 'sales_tax'
        instead of to the market. Returns the unpaid remainder."""
        if amount <= 0:
            return 0
        if not business_mod.is_setup(self.store):
            return self._pay(from_id, "SYS-MARKET", amount, "purchase",
                             game_minutes, note)
        balance = self.store.balance(from_id)
        paid_total = min(amount, balance)
        if paid_total <= 0:
            return amount
        rate = self.data.economy_config["tax_rules"][
            "sales_tax_percent"]
        if gov_mod.is_setup(self.store):
            # Session 05 Unit 09: an enacted sales-tax law sets
            # the rate (the accessor falls back to the configured
            # rate when no law exists — identical behaviour).
            from . import justice as justice_mod
            rate = justice_mod.effective_sales_tax_percent(
                self.store, self.data)
        tax = round(paid_total * rate / (100 + rate))
        if tax > 0:
            self.store.transfer(from_id, "SYS-CITY", tax, "sales_tax",
                                game_minutes,
                                note="sales tax on purchases")
        rest = paid_total - tax
        if rest > 0:
            self.store.transfer(from_id, "SYS-MARKET", rest, "purchase",
                                game_minutes, note=note)
        return amount - paid_total

    def _pay_business_wages(self, month_index, game_minutes):
        """Session 04 Unit 03: wages for employments carrying an
        employer_business_id are paid by the business's own account
        (reason 'wage', keyed per employment+month — idempotent),
        not by the SYS-EMPLOYERS aggregate. A business pays what it
        holds; the shortfall is recorded on the business as a
        'wage_shortfall' event (the distress machinery reads the
        consequences) and the employee is taxed in the settlement
        on what they actually received. Returns
        {employment_id: paid_gross}."""
        store = self.store
        paid = {}
        if not business_mod.is_setup(store):
            return paid
        for emp in store.rows(
                "SELECT * FROM employments WHERE"
                " employer_business_id IS NOT NULL"
                " AND ended_at_game_minutes IS NULL"
                " ORDER BY employment_id"):
            bid = emp["employer_business_id"]
            biz = store.row("SELECT status FROM businesses WHERE"
                            " business_id = ?", (bid,))
            if biz is None or biz["status"] == "closed":
                paid[emp["employment_id"]] = 0
                continue
            due = emp["wage_per_month"]
            amount = min(due, store.business_balance(bid))
            if amount > 0:
                store.transfer(
                    None, emp["character_id"], amount, "wage",
                    game_minutes,
                    note=f"{emp['profession_id']} monthly wage"
                         " (business employer)",
                    related_business_id=bid,
                    transfer_key=f"bwage:{emp['employment_id']}:"
                                 f"{month_index}",
                    event_ref=f"month:{month_index}",
                    from_business_id=bid)
            if amount < due:
                business_mod.log_event(
                    store, bid, "wage_shortfall",
                    {"employment_id": emp["employment_id"],
                     "character_id": emp["character_id"],
                     "due_ncr": due, "paid_ncr": amount,
                     "month_index": month_index}, game_minutes)
            paid[emp["employment_id"]] = amount
        return paid

    def _pay_government_wages(self, month_index, game_minutes):
        """Session 05 Unit 08: civil servants employed by a
        treasury are paid by that treasury in government.py's
        pre-pass (the national treasury pays in full — overdraft
        is recorded public debt; a municipal treasury pays what
        it holds and records the shortfall). Returns
        {employment_id: paid_gross} for the settlement's tax."""
        if not gov_mod.is_setup(self.store):
            return {}
        return gov_mod.pay_government_wages(
            self.store, self.data, month_index, game_minutes)

    def _settle_month(self, last_day):
        store, data = self.store, self.data
        econ = data.econ
        game_minutes = (last_day + 1) * 1440
        month_days = range(last_day - 29, last_day + 1)
        presets = [self.weather_for_day(d) for d in month_days]
        rain_days = presets.count("rain")
        storm_days = presets.count("storm")
        taxi_factor = 1 + 0.25 * rain_days / 30 + 0.5 * storm_days / 30
        brackets = data.prices["tax"]["income_monthly_brackets"]
        biz_rate = data.prices["tax"]["business_monthly_percent_of_profit"]
        rental_day = data.prices["taxi_fares"]["cab_rental_ncr_per_day"]
        # Session 04 Unit 03: business-employed wages are paid by
        # the businesses themselves, before the household loop
        # taxes and spends what was actually received.
        biz_wages = self._pay_business_wages((last_day + 1) // 30,
                                             game_minutes)
        # Session 05: treasury-paid civil servants, same pattern.
        gov_wages = self._pay_government_wages((last_day + 1) // 30,
                                               game_minutes)

        for h, members in self._households():
            hid = h["household_id"]
            now = game_minutes
            ages = {m["character_id"]: identity_mod.age_years(
                m["born_at_game_minutes"], now) for m in members}
            adults = sum(1 for a in ages.values() if a >= 18)
            children = len(members) - adults
            earners = []
            for m in members:
                emp = store.row("SELECT * FROM employments"
                                " WHERE character_id = ?"
                                " AND ended_at_game_minutes IS NULL",
                                (m["character_id"],))
                if emp:
                    earners.append((m, emp))
            head = members[0]
            for m in members:
                mrow = store.row(
                    "SELECT role FROM household_members WHERE household_id"
                    " = ? AND character_id = ? AND left_at_game_minutes"
                    " IS NULL", (hid, m["character_id"]))
                if mrow and mrow["role"] == "head":
                    head = m
                    break
            # Session 02 Unit 03: last month's arrears are repaid
            # before this month's costs (no-op when debt-free).
            family_economy.repay_debt(store, hid, head["character_id"],
                                      game_minutes)
            band = "lower"
            if earners:
                band = econ.band_for(data.wage(
                    earners[0][1]["profession_id"], "entry"))

            # Income.
            gross_by = {}
            uplift_total = 0
            for m, emp in earners:
                cid, pid = m["character_id"], emp["profession_id"]
                if pid in BUSINESS_PROFESSIONS:
                    pnl = econ.business_pnl(
                        data.prices, pid, data.business_tier_key(emp["tier"]))
                    costs = pnl["revenue"] - pnl["profit"]
                    store.transfer("SYS-MARKET", cid, pnl["revenue"],
                                   "business_revenue", game_minutes,
                                   note=f"{pid} monthly revenue")
                    self._pay(cid, "SYS-MARKET", costs, "business_expense",
                              game_minutes, note=f"{pid} monthly costs")
                    tax = round(pnl["profit"] * biz_rate / 100) \
                        if pnl["profit"] > 0 else 0
                    if tax:
                        self._pay(cid, "SYS-CITY", tax, "tax",
                                  game_minutes, note="business tax")
                    gross = pnl["profit"]
                    entry_income = econ.business_pnl(
                        data.prices, pid, "entry")["profit"]
                else:
                    if emp["employer_business_id"] \
                            and business_mod.is_setup(store):
                        # Session 04: the business already paid
                        # this wage (see _pay_business_wages); tax
                        # falls on what was actually received.
                        gross = biz_wages.get(emp["employment_id"], 0)
                        tax = econ.monthly_tax(gross, brackets)
                        if tax > 0:
                            store.transfer(cid, "SYS-CITY", tax, "tax",
                                           game_minutes,
                                           note="income tax")
                    elif emp["employer_character_id"] \
                            in gov_mod.TREASURY_ACCOUNTS \
                            and gov_mod.is_setup(store):
                        # Session 05: the treasury already paid
                        # this wage (see _pay_government_wages);
                        # tax falls on what was received.
                        gross = gov_wages.get(emp["employment_id"], 0)
                        tax = econ.monthly_tax(gross, brackets)
                        if tax > 0:
                            store.transfer(cid, "SYS-CITY", tax, "tax",
                                           game_minutes,
                                           note="income tax")
                    else:
                        gross = emp["wage_per_month"]
                        if pid == "taxi_driver":
                            gross = round(gross * taxi_factor)
                        tax = econ.monthly_tax(gross, brackets)
                        if gross > 0:
                            store.transfer("SYS-EMPLOYERS", cid, gross,
                                           "wage", game_minutes,
                                           note=f"{pid} monthly wage"
                                                " (gross)")
                        if tax > 0:
                            store.transfer(cid, "SYS-CITY", tax, "tax",
                                           game_minutes,
                                           note="income tax")
                    entry_income = data.wage(pid, "entry")
                gross_by[cid] = gross
                uplift_total += round(max(0, gross - entry_income)
                                      * data.prices["lifestyle_uplift"]
                                      ["percent_of_raise_consumed"] / 100)
                emotions_mod.apply_event(store, cid, "payday")
            # Pensions (SIM ASSUMPTION amount — see module docstring).
            pension_total = 0
            for m in members:
                cid = m["character_id"]
                if ages[cid] >= 65 and cid not in gross_by:
                    store.transfer("SYS-CITY", cid, PENSION_NCR_PER_MONTH,
                                   "pension", game_minutes,
                                   note="elder pension (sim assumption)")
                    pension_total += PENSION_NCR_PER_MONTH

            # Costs: rent by the head (or richest member if the head
            # cannot cover it), living costs split by income share.
            unpaid = 0
            tenancy = store.row("SELECT * FROM tenancies"
                                " WHERE tenant_household_id = ?"
                                " AND ended_at_game_minutes IS NULL", (hid,))
            if tenancy:
                rent = tenancy["rent_per_month"]
                payer = head["character_id"]
                if store.balance(payer) < rent and gross_by:
                    payer = max(gross_by, key=lambda c: store.balance(c))
                unpaid += self._pay(payer, "SYS-CITY", rent, "rent",
                                    game_minutes, note="monthly rent")
            living = self._living_costs(
                band, max(adults, 1), children,
                [e[1]["profession_id"] for e in earners])
            total_living = sum(living.values()) + uplift_total
            taxi_rental_total = 0
            for m, emp in earners:
                if emp["profession_id"] == "taxi_driver":
                    taxi_rental_total += rental_day * econ.WORK_DAYS
            total_living += taxi_rental_total
            if gross_by:
                total_gross = sum(gross_by.values()) or 1
                for cid, gross in gross_by.items():
                    share = round(total_living * gross / total_gross)
                    unpaid += self._pay_purchase(
                        cid, share, game_minutes,
                        note="monthly living costs")
            else:
                unpaid += self._pay_purchase(
                    head["character_id"], total_living, game_minutes,
                    note="monthly living costs")
            if unpaid > 0:
                memory_mod.log_life_event(
                    store, head["character_id"], "financial_distress",
                    game_minutes, details={"unpaid_ncr": unpaid,
                                           "household_id": hid})
            # Savings goals complete when the balance covers them.
            for m in members:
                cid = m["character_id"]
                for g in store.rows(
                        "SELECT goal_id, target FROM character_goals"
                        " WHERE character_id = ? AND goal_type ="
                        " 'save_amount' AND status = 'active'", (cid,)):
                    target = json.loads(g["target"]).get("amount", 0)
                    if target and store.balance(cid) >= target:
                        decisions_mod.complete_goals_of_type(
                            store, cid, "save_amount", game_minutes)
            # Session 02 Unit 03: the family's monthly accounts,
            # written from this settlement's own numbers. Education
            # and healthcare stay 0 — civic provision, no fee line
            # exists in prices.json (family_economy docstring).
            rent_paid = tenancy["rent_per_month"] if tenancy else 0
            family_economy.record_month(
                store, hid, (last_day + 1) // 30, game_minutes,
                income=sum(gross_by.values()) + pension_total,
                food=living["food"], housing=rent_paid,
                transport=living["transport"] + taxi_rental_total,
                other=(living["utilities"] + living["clothing"]
                       + living["eating"] + living["services"]
                       + uplift_total),
                emergency=unpaid)

    # -- reporting ---------------------------------------------------------------
    def summary(self):
        store = self.store
        world = store.world()
        alive = store.row("SELECT COUNT(*) AS n FROM characters"
                          " WHERE is_system = 0"
                          " AND died_at_game_minutes IS NULL")["n"]
        dead = store.row("SELECT COUNT(*) AS n FROM characters"
                         " WHERE is_system = 0"
                         " AND died_at_game_minutes IS NOT NULL")["n"]
        employed = {r["profession_id"]: r["n"] for r in store.rows(
            "SELECT profession_id, COUNT(*) AS n FROM employments"
            " WHERE ended_at_game_minutes IS NULL"
            " GROUP BY profession_id ORDER BY profession_id")}
        events = {r["event_type"]: r["n"] for r in store.rows(
            "SELECT event_type, COUNT(*) AS n FROM life_events"
            " GROUP BY event_type ORDER BY event_type")}
        decisions = {r["decision_type"]: r["n"] for r in store.rows(
            "SELECT decision_type, COUNT(*) AS n FROM decision_log"
            " GROUP BY decision_type ORDER BY decision_type")}
        emo = store.row(
            "SELECT ROUND(AVG(happiness),2) AS h, ROUND(AVG(stress),2)"
            " AS s FROM emotional_state es JOIN characters c"
            " ON c.character_id = es.character_id WHERE c.is_system = 0"
            " AND c.died_at_game_minutes IS NULL")
        return {
            "day_index": world["day_index"],
            "game_minutes": world["game_minutes"],
            "seed": world["sim_seed"],
            "population_alive": alive,
            "population_dead": dead,
            "households": store.row(
                "SELECT COUNT(*) AS n FROM households"
                " WHERE dissolved_at_game_minutes IS NULL")["n"],
            "employed_by_profession": employed,
            "total_character_balance": store.row(
                "SELECT COALESCE(SUM(balance_cached),0) AS s FROM"
                " characters WHERE is_system = 0")["s"],
            "ledger_rows": store.row(
                "SELECT COUNT(*) AS n FROM economy_ledger")["n"],
            "ledger_mismatches": len(store.ledger_sum_check()),
            "life_events": events,
            "decisions": decisions,
            "avg_happiness": emo["h"],
            "avg_stress": emo["s"],
            # Session 02 society layer, same read-live discipline.
            "communities": store.row(
                "SELECT COUNT(*) AS n FROM communities")["n"],
            "social_events": store.row(
                "SELECT COUNT(*) AS n FROM social_events")["n"],
            "households_in_debt": store.row(
                "SELECT COUNT(*) AS n FROM household_state"
                " WHERE debt_ncr > 0")["n"],
            "students_enrolled": store.row(
                "SELECT COUNT(*) AS n FROM education_records"
                " WHERE status = 'enrolled'")["n"],
            "credentials_completed": store.row(
                "SELECT COUNT(*) AS n FROM education_records"
                " WHERE status = 'completed' AND programme !="
                " 'school'")["n"],
            "open_conflicts": store.row(
                "SELECT COUNT(*) AS n FROM conflict_records"
                " WHERE status = 'open'")["n"],
            "neighbour_edges": store.row(
                "SELECT COUNT(*) AS n FROM relationships"
                " WHERE relation_type = 'neighbour'")["n"],
            # Session 03 city layer (zeros/empty when not set up).
            "city_populations": {
                spec["city_id"]: cities_mod.city_population(
                    store, self.data, spec["city_id"])
                for spec in self.data.city_specs()}
            if cities_mod.is_setup(store) else {},
            "active_construction_projects": store.row(
                "SELECT COUNT(*) AS n FROM construction_projects"
                " WHERE status = 'active'")["n"],
            "completed_construction_projects": store.row(
                "SELECT COUNT(*) AS n FROM construction_projects"
                " WHERE status IN ('completed', 'occupied')")["n"],
            "migrations_total": store.row(
                "SELECT COUNT(*) AS n FROM migration_records")["n"],
            "trade_flows_total": store.row(
                "SELECT COUNT(*) AS n FROM trade_flows")["n"],
            # Session 04 economy layer (zeros/empty when not set up).
            "businesses_active": store.row(
                "SELECT COUNT(*) AS n FROM businesses WHERE"
                " closed_at_game_minutes IS NULL")["n"],
            "businesses_closed": store.row(
                "SELECT COUNT(*) AS n FROM businesses WHERE"
                " closed_at_game_minutes IS NOT NULL")["n"],
            "bank_reserves_ncr": store.balance("SYS-BANK"),
            "loans_active": store.row(
                "SELECT COUNT(*) AS n FROM loans WHERE status ="
                " 'active'")["n"],
            "vacancies_open": store.row(
                "SELECT COUNT(*) AS n FROM vacancies WHERE status ="
                " 'open'")["n"],
            "price_index": round(market_mod.price_index(
                store, self.data), 2) if business_mod.is_setup(store)
            else None,
            "active_crises": [c["crisis_type"] for c in
                              crises_mod.active_crises(store)],
            "latest_indicators": (indicators_mod.latest(
                store, "national") or {}).get("metrics"),
            # Session 05 government layer (empty when not set up).
            "government": self._government_summary()
            if gov_mod.is_setup(store) else {},
            # Session 06 human development layer (empty when not
            # set up).
            "humandev": self._humandev_summary()
            if humandev_mod.is_setup(store) else {},
            # Session 07 transportation layer (empty when not
            # set up).
            "transport": transport_mod.transport_summary(store)
            if transport_mod.is_setup(store) else {},
            # Session 08 environment layer (empty when not set up).
            "environment": environment_mod.environment_summary(store)
            if environment_mod.is_setup(store) else {},
            # Session 09 agent coordination layer (empty when not
            # set up).
            "agents": agents_mod.agents_summary(store)
            if agents_mod.is_setup(store) else {},
            # Session 10 integration layer (empty when not
            # set up).
            "integration": self._integration_summary()
            if integration_mod.is_setup(store) else {},
        }

    def _integration_summary(self):
        store = self.store
        by_source = {r["source"]: r["n"] for r in store.rows(
            "SELECT source, COUNT(*) AS n FROM world_events"
            " GROUP BY source ORDER BY source")}
        return {
            "registry_events": sum(by_source.values()),
            "registry_by_source": by_source,
            "technology": {f: v["level"] for f, v in
                           integration_mod.latest_technology(
                               store).items()},
            "global_scenarios_active": store.row(
                "SELECT COUNT(*) AS n FROM crisis_records WHERE"
                " status = 'active' AND details LIKE"
                " '%global_scenario%'")["n"],
        }

    def _humandev_summary(self):
        store = self.store
        latest = store.row(
            "SELECT indicators FROM human_development_indicators"
            " WHERE scope = 'national' ORDER BY month_index DESC"
            " LIMIT 1")
        return {
            "institutions": store.row(
                "SELECT COUNT(*) AS n FROM"
                " educational_institutions")["n"],
            "facilities": store.row(
                "SELECT COUNT(*) AS n FROM healthcare_facilities"
            )["n"],
            "conditions_open": store.row(
                "SELECT COUNT(*) AS n FROM health_conditions"
                " WHERE status IN ('active', 'recovering')")["n"],
            "conditions_total": store.row(
                "SELECT COUNT(*) AS n FROM health_conditions")["n"],
            "patient_visits": store.row(
                "SELECT COUNT(*) AS n FROM patient_visits")["n"],
            "certifications": store.row(
                "SELECT COUNT(*) AS n FROM certifications")["n"],
            "vaccinations": store.row(
                "SELECT COUNT(*) AS n FROM vaccination_records"
            )["n"],
            "research_records": store.row(
                "SELECT COUNT(*) AS n FROM research_records")["n"],
            "latest_indicators": json.loads(latest["indicators"])
            if latest else None,
        }

    def _government_summary(self):
        from . import policies as policies_mod
        store = self.store
        governing = store.row(
            "SELECT holder_character_id FROM offices WHERE"
            " institution_id = 'GOV-PM' AND title ="
            " 'prime_minister' AND status = 'active' LIMIT 1")
        governing_party = None
        if governing and governing["holder_character_id"]:
            from . import politics as politics_mod
            governing_party = politics_mod.party_of(
                store, governing["holder_character_id"])
        approval = store.row("SELECT ROUND(AVG(approval), 2) AS a"
                             " FROM citizen_opinion")
        return {
            "governing_party": governing_party,
            "mean_approval": approval["a"],
            "treasuries": gov_mod.government_balances(store),
            "public_debt_ncr": policies_mod.public_debt(store),
            "elections_held": store.row(
                "SELECT COUNT(*) AS n FROM elections WHERE"
                " winner_party_id IS NOT NULL")["n"],
            "active_policies": store.row(
                "SELECT COUNT(*) AS n FROM policies WHERE status"
                " = 'active'")["n"],
            "open_cases": store.row(
                "SELECT COUNT(*) AS n FROM court_cases WHERE"
                " status IN ('filed', 'appealed')")["n"],
            "incidents_total": store.row(
                "SELECT COUNT(*) AS n FROM incidents")["n"],
            "civil_servants": store.row(
                "SELECT COUNT(*) AS n FROM civil_service WHERE"
                " status = 'active'")["n"],
            "laws_enacted": store.row(
                "SELECT COUNT(*) AS n FROM laws WHERE status ="
                " 'enacted'")["n"],
        }

    def profile(self, character_id):
        return identity_mod.profile_card(self.store, character_id)
