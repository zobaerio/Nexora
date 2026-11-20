# GTA-Style Nijer Game — Prototype Plan
> **⚠️ DIRECTION CHANGE (2026-11-20 night, owner):** Ei Godot plan-er Unit 0+1 build hoyeche (8/8 test pass, Windows exe export soho), kintu owner-er siddhanto — visual target ekhon **NEXORA photorealistic universe, Unreal Engine 5.8**. Current master plan: `NEXORA-MIGRATION-PLAN.md`. Ei document + Godot prototype design reference hishebe preserve thaklo, delete hobe na. Godot diye porer unit (2–7) ar egobe na.
**Date:** 2026-11-20 · **Status:** Plan ready, build shuru hoy nai
**Working title (placeholder, brand scan baki):** *Rupsha City*
**Rule (Replica skill):** GTA-r *functionality* — nijer code, nijer map, nijer character, nijer brand. Rockstar-er kono asset, map, logo, name, mission ba code na.

---

## 1. Positioning — keno ei game alada hobe

GTA copy kore labh nai. Er strong dik holo **Bangladeshi open-world city** — jeta keu banay nai:

> "Khulna/Dhaka-inspired city-te open-world driving, police chase ar mission — rickshaw, CNG, local dokan, nodi ar bridge soho."

Etai entrepreneur angle: GTA-style system + local flavour = nijer porichoy.

## 2. Engine Decision — Godot 4.7.2

| Engine | Valo dik | Somossa | Siddhanto |
|---|---|---|---|
| **Godot 4.7.2** (latest stable, 18 Aug 2026; 4.8 ekhono beta) | 100% free, MIT licence, royalty nai, halka (~100MB), GDScript shohoj, Windows/Android/Web export | AAA graphics na | ✅ **Prototype-er jonno eta** |
| Unity 6.6 | Asset store boro, job market | Licence/pricing jhamela, heavy editor | Pore lagle vabbo |
| Unreal 5.8 | Sera graphics | Khub bhari, tomar PC-te kosto, overkill | ❌ Prototype-e na |

**Locked:** Godot 4.7.2 stable (beta 4.8 na), GDScript, Blender for nijer model.

## 3. Prototype v0.1 — Definition of Done

Ekta Windows `.exe` jeta te **10 minute er purno gameplay loop** thakbe:

1. Player city-te spawn, third-person e hate/douray
2. Ekta gari-r kache giye `F` chaple gari te othe, chalate pare
3. Rastay traffic gari + pothchari (pedestrian) chole
4. Traffic gari te dhakka / oporadh korle **Wanted star** bare, police chase kore
5. Police er hat theke lukiye thakle wanted aste aste kome
6. Minimap + HUD (health, wanted, speed)
7. **1 ta mission:** somoyer moddhe checkpoint-e pouchano → reward → mission complete screen
8. Pause menu, restart, game over (busted/wasted — nijer wording-e)

**Playable na hole prototype sesh na** — sudhu scene/model dekhano sesh na.

## 4. Map — Chhoto, Kintu Jibonto

- Size: ~600m × 600m ekta district (boro na, ghono)
- Grid road: 4×4 block, footpath, street light, gacher sari
- 20–30 building — CC0 model + Blender-e nijer simple model, GTA theke kichu na
- Local flavour: rickshaw + CNG model (simple), cha-er dokan, nodi-r ghat + chhoto bridge
- 1 ta garage/safehouse point, 3 ta mission checkpoint point

## 5. Systems (ki ki banate hobe)

| System | Prototype version | Pore |
|---|---|---|
| PlayerController | Walk/run/jump, third-person camera, collision | Swim, combat, cover |
| VehicleSystem | 1 type drivable car — accelerate/brake/steering/handbrake, camera follow | 3+ vehicle, bike, rickshaw drive |
| Traffic AI | Gari lane dhore chole, samne badha pele thame | Signal, lane change |
| Pedestrian AI | Footpath e hate, gari ashle sore, dhakkay palay | Smart crowd |
| Police + Wanted | 1-3 star, police car chase, dhora porle busted | 4-5 star, roadblock |
| HUD / Minimap | Health, wanted star, speed, round minimap | Full map screen |
| MissionSystem | 1 timed checkpoint mission, timer, reward | Story mission chain |
| Audio | Engine, horn, siren — CC0 sound | Radio, voice |
| Save/Menu | Main menu, pause, restart | Save/load slot |

## 6. Build Units — ekta ekta kore, test kore, tarpor porer ta

Prottektar seshe playable build + test pass na hole porer unit na. Estimate = amar kajer session, calendar promise na.

| Unit | Kaj | Pass criteria |
|---|---|---|
| **0 — Setup** | Godot 4.7.2 project, folder structure, Git repo, test scene | Project khole, khali scene run hoy, Windows export test pass |
| **1 — Player** | Third-person character, walk/run/jump, camera orbit + collision | Character atke jay na, camera deyale dhoke na |
| **2 — City Block** | Road grid, footpath, 10+ building, street light, spawn point | Player puro block ghure aste pare, fps stable |
| **3 — Vehicle** | 1 drivable car, get in/out (F), driving physics, follow camera | Gari smooth chole, ultay na, player namte pare |
| **4 — Traffic + Pedestrian** | 6-8 traffic car lane follow, 10 pedestrian walk | 5 min e kono gari atke/jam hoye theme jay na |
| **5 — Police + Wanted** | Crime detection, 1-3 star, police chase, busted, wanted decay | Dhakka dile star bare, lukale kome, dhora porle busted screen |
| **6 — HUD + Mission** | HUD, minimap, 1 timed mission, reward, pause/restart | Mission start → complete/fail duitai kaj kore |
| **7 — Polish + Export** | Sound (engine/siren/horn), menu, bug fix, final Windows build | Bondhu-r PC te exe chole, 10 min crash na |

## 7. Controls (Prototype)

- **WASD** — hata / gari chalano · **Shift** — dour / boost na, sudhu run
- **Space** — jump / handbrake · **Mouse** — camera · **F** — gari te otha/nama
- **Esc** — pause · **M** — boro map (jodi somoy thake) · Gamepad pore

## 8. Project Structure

```
rupsha-city/
  project.godot
  scenes/    (main, player, vehicles, city, ui)
  scripts/   (player, vehicle, traffic, police, wanted, mission, hud)
  assets/    (nijer + CC0 model/sound — prottektar licence note soho)
  builds/    (windows export)
  replica/   (recon, brand scan, diff notes)
```

## 9. Asset Aino (Legal)

- ✅ Kenney.nl, Quaternius, Poly Pizza — **CC0** model; Blender-e banano nijer model
- ✅ Freesound-er **CC0** sound sudhu, licence note file-e rakha hobe
- ❌ GTA ba onno game theke rip kora model/sound/map/character — kokhonoi na
- ❌ Google theke neya random model jar licence jana nai

## 10. Performance Target

- Mid-range PC te 1080p te stable **50-60 fps** (prototype map chhoto bole sombhob)
- Ek sathe max ~25 active vehicle/pedestrian — er beshi spawn na

## 11. Honest Risk

- Driving physics + police chase-i sobcheye kothin 2 ta ongsho — Unit 3 ar 5 e somoy beshi lagte pare
- Ami Godot project + sob code baniye dite parbo, kintu **final khelar moja (game feel) tomar PC te test korei bujhbe** — sekhane tomar feedback-e tuning hobe
- Prototype AAA graphics hobe na — low-poly clean style hobe, setai ekhonkar jonno thik siddhanto

## 12. Prototype-er Porer Roadmap (siddhanto pore)

- **v0.2:** 3 vehicle, bike, din-raat cycle, dokan interior 1 ta
- **v0.3:** 5 mission chain, taka/economy, safehouse save
- **v0.4:** Boro map (2 district), Android export test
- **v1.0:** Nijer brand name final (brand scan pass kore), itch.io / Steam page

## 13. Next Step

Plan approve hole: **Unit 0 + Unit 1** diye shuru — Godot project setup + third-person player, playable test build soho.
