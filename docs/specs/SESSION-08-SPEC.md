# SESSION 08 — Weather, Climate, Environment & Ecosystem Intelligence Engine (owner spec, received 2026-11-21)

Gate rule: starts only after Session 07 passes. Audit existing environmental functionality first (weather presets + daily weather in the engine, terrain regions from Session 03). Weather/environment must produce ACTUAL simulation effects — no disconnected weather animations, no fabricated measurements. Simulated conditions must always be distinguished from real-world weather observations; never claim scientific forecasting accuracy.

## Global weather (configurable)
Temperature, humidity, atmospheric pressure, wind speed + direction, cloud coverage, precipitation, visibility, weather conditions — across multiple geographical regions with different characteristics. (Extends the existing daily-weather system; regions = the two cities + terrain regions.)

## Day/night
Sunrise, sunset, day/night duration, seasonal daylight variation, solar position approximation, lighting changes — connected to human routines + city activity (the GameClock is the single time source).

## Seasons (configurable)
Spring/summer/autumn/winter, monsoon, dry, wet seasons. Seasonal change influences temperature, rainfall, agriculture, energy demand, daily activities. Different climate patterns per region.

## Precipitation & atmosphere (simplified configurable models)
Cloud formation + movement, rainfall, heavy rainfall, snowfall where geographically appropriate, hail scenarios, precipitation accumulation. Wind fields, regional wind patterns, storm conditions, pressure changes, wind effects on infrastructure. NO claim of scientifically accurate numerical weather prediction.

## Water systems
Rivers, lakes, reservoirs, groundwater, wetlands, drainage basins, water storage, availability, consumption, quality — connected to cities, households, agriculture, industries (Session 03 infrastructure water network is the distribution layer).

## Hydrology & flooding
Rainfall accumulation, surface runoff, river water levels, drainage capacity, floodplain mapping, urban flooding, river flooding, coastal inundation scenarios, flood risk indicators. Floods affect roads, buildings, businesses and population safety according to geographic exposure (terrain data decides exposure).

## Vegetation
Forests, grasslands, trees, vegetation density, plant growth, deforestation, reforforestation, habitat conditions — responding to water availability, temperature, land use.

## Agriculture
Agricultural land, crop selection, planting schedules, irrigation, soil fertility, crop growth, harvesting, productivity, crop failures, farm economics — connected to Session 04 food production + market pricing.

## Soil
Classification, moisture, fertility, erosion, land degradation, slope stability, ground conditions — influencing construction, agriculture, infrastructure.

## Pollution (traceable sources, measurable consequences)
Air, water, soil pollution; industrial emissions; vehicle emissions (Session 07); waste contamination; urban heat; noise pollution.

## Natural disasters (configurable scenarios, simplified models)
Cyclones, hurricanes, severe storms, floods, droughts, heatwaves, wildfires, earthquakes, landslides, tsunami where geographically appropriate. Each event: ID, geographic extent, intensity, duration, affected population, infrastructure exposure, economic damage, response activities, recovery records. NO precise disaster prediction claims.

## Long-term climate trends (configurable scenarios + assumptions)
Temperature trends, rainfall patterns, sea-level scenarios, extreme weather frequency, vegetation change, water availability, environmental vulnerability.

## Wildlife & biodiversity (abstracted models)
Wildlife populations, habitat regions, biodiversity indicators, ecosystem relationships, species migration, habitat loss, conservation programs. No claim of complete biological accuracy.

## Environmental governance (Session 05)
Regulations, protected areas, pollution restrictions, conservation policies, disaster preparedness, climate adaptation programs, environmental impact assessments. Government decisions must affect environmental outcomes.

## Disaster response (actual resources only)
Evacuation, emergency shelters, medical response, infrastructure repair, relief distribution, reconstruction, economic recovery — integrating emergency services, hospitals (Session 06), transportation (Session 07), government agencies, populations, financial resources. Operations use ACTUAL available resources.

## Effects on people (Sessions 01/02/06)
Comfort, outdoor activities, health conditions, agricultural employment, housing demand, water availability, daily routines, disaster exposure.

## Observatory
Environmental views = data layer over engine data only (live weather, regional climate, rainfall, temperature/wind, water levels, floods, agricultural productivity, forest coverage, pollution, biodiversity, disaster events, climate trends).

## Performance
Region-based updates, time-stepped climate simulation, event-driven disaster effects, spatial calculations, background weather updates, efficient historical aggregation, configurable parameters. Avoid unnecessary high-frequency global calculations.

## Acceptance criteria (test-verified, repeatable scenarios)
1 Weather varies by region. 2 Day/night cycles work. 3 Seasons affect conditions. 4 Rainfall changes water accumulation. 5 Water systems interact with cities. 6 Flood scenarios affect exposed infrastructure. 7 Agriculture responds to climate + soil. 8 Pollution has traceable sources. 9 Disasters create measurable impacts. 10 Emergency response uses available resources. 11 Recovery updates the world. 12 Environmental policies influence outcomes. 13 Historical environmental records persist. 14 Previous sessions remain functional.

Do NOT proceed to Session 09 until Session 08 passes.
