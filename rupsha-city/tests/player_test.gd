extends Node3D
## Automated Unit 1 test — run headless:
##   godot --headless res://tests/player_test.tscn
## Builds a flat ground, spawns the Player with simulated input, and checks:
##   1. player lands and stays on the floor
##   2. walking forward moves the player a sane distance
##   3. running is faster than walking
##   4. jumping raises the player and it lands again
##   5. camera spring arm shortens near a wall (no wall clipping)
## Prints PLAYER_TEST_PASS and quits 0, or PLAYER_TEST_FAIL and quits 1.

var _player: Player
var _failures: Array[String] = []


func _check(condition: bool, label: String) -> void:
	if condition:
		print("  ok: ", label)
	else:
		_failures.append(label)
		printerr("  FAIL: ", label)


func _ready() -> void:
	_run.call_deferred()


func _make_ground() -> void:
	var body := StaticBody3D.new()
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(80, 1, 80)
	shape.shape = box
	shape.position = Vector3(0, -0.5, 0)
	body.add_child(shape)
	add_child(body)


func _make_wall_behind(pos: Vector3) -> void:
	var body := StaticBody3D.new()
	body.position = pos
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(10, 4, 0.6)
	shape.shape = box
	shape.position = Vector3(0, 2, 0)
	body.add_child(shape)
	add_child(body)


func _frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func _run() -> void:
	_make_ground()
	var packed := load("res://scenes/player.tscn") as PackedScene
	_player = packed.instantiate() as Player
	_player.use_simulated_input = true
	_player.position = Vector3(0, 0.1, 0)
	_player.set_camera_yaw(0.0)
	add_child(_player)

	# 1. settle on floor
	await _frames(20)
	_check(_player.is_on_floor(), "player lands on floor")
	_check(absf(_player.position.y) < 0.2, "player rests near ground level")

	# 2. walk forward (-Z in camera space) for 1 second of physics
	var start := _player.position
	_player.simulated_move = Vector2(0, -1)
	await _frames(60)
	_player.simulated_move = Vector2.ZERO
	await _frames(10)
	var walk_dist := start.distance_to(_player.position)
	_check(walk_dist > 2.5 and walk_dist < 7.0, "walk moves player (dist=%.2f)" % walk_dist)
	_check(_player.position.z < start.z - 2.0, "walk goes camera-forward")

	# 3. run for 1 second — must cover more ground than walking
	start = _player.position
	_player.simulated_run = true
	_player.simulated_move = Vector2(0, -1)
	await _frames(60)
	_player.simulated_move = Vector2.ZERO
	_player.simulated_run = false
	await _frames(10)
	var run_dist := start.distance_to(_player.position)
	_check(run_dist > walk_dist * 1.3, "run faster than walk (walk=%.2f run=%.2f)" % [walk_dist, run_dist])

	# 4. jump — rises, then lands
	_player.simulated_jump = true
	var max_y := _player.position.y
	for i in 70:
		await get_tree().physics_frame
		max_y = maxf(max_y, _player.position.y)
	_check(max_y > 0.5, "jump rises (max_y=%.2f)" % max_y)
	_check(_player.is_on_floor(), "player lands after jump")

	# 5. camera spring arm: wall 2m behind the camera side (+Z of player)
	_make_wall_behind(_player.position + Vector3(0, 0, 3.2))
	await _frames(15)
	var cam := _player.get_node("CameraRig/SpringArm3D/Camera3D") as Camera3D
	var cam_dist := cam.global_position.distance_to(_player.global_position + Vector3(0, 1.6, 0))
	_check(cam_dist < 4.4, "spring arm shortens near wall (cam_dist=%.2f)" % cam_dist)

	if _failures.is_empty():
		print("PLAYER_TEST_PASS")
		get_tree().quit(0)
	else:
		printerr("PLAYER_TEST_FAIL: ", _failures)
		get_tree().quit(1)
