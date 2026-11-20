# Rupsha City — Prototype v0.1

GTA-style **original** open-world game prototype. Nijer code, nijer map, nijer brand —
Rockstar / GTA theke kono asset, map, name ba code use hoy na (Replica skill rule).

## Cholche emon (Unit 0 + Unit 1)

- Godot **4.7.2 stable** project
- Third-person player: **WASD** move, **Shift** run, **Space** jump, **mouse** camera
- Camera SpringArm diye deyale dhoke na
- Test ground: flat ground + 2 wall block (Unit 2 te asol city district ashbe)
- **Esc** — mouse release / recapture

## Chalate

1. Godot 4.7.2 diye project ta kholo (`project.godot`)
2. F6 / Play — main scene cholbe

## Test (headless)

```bash
godot --headless --path . res://tests/player_test.tscn
# PLAYER_TEST_PASS ele Unit 1 er movement/jump/camera test pass
godot --headless --path . --quit-after 90   # main scene smoke run
```

## Build order

Unit 0 Setup ✅ · Unit 1 Player ✅ (test pending on first run) ·
Unit 2 City district · Unit 3 Vehicle · Unit 4 Traffic + Pedestrian ·
Unit 5 Police + Wanted · Unit 6 HUD + Mission · Unit 7 Polish + Windows export

Full plan: `../PROTOTYPE-PLAN.md`

> Local history note: Godot prototype-er prothom local commit chilo `24352cd`, tag `v0.1-godot-prototype` — NEXORA repo-te ekীভূত koray sei history ekhon ei repo-r commit-e preserve.
