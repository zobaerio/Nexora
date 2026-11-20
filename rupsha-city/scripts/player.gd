extends CharacterBody3D
class_name Player
## Third-person player for Rupsha City prototype (Unit 1).
## Walk / run / jump, mouse-orbit camera on a SpringArm3D so the camera
## pulls in instead of clipping through walls.
## Tests can drive the player by setting use_simulated_input = true
## before adding it to the tree, then feeding simulated_move / _run / _jump.

@export var walk_speed: float = 5.0
@export var run_speed: float = 9.0
@export var acceleration: float = 30.0
@export var jump_velocity: float = 5.5
@export var mouse_sensitivity: float = 0.003
@export var pitch_min_deg: float = -65.0
@export var pitch_max_deg: float = 30.0

var gravity: float = float(ProjectSettings.get_setting("physics/3d/default_gravity", 9.8))

# Simulated-input hooks (used by tests/player_test.gd, ignored in normal play)
var use_simulated_input: bool = false
var simulated_move: Vector2 = Vector2.ZERO
var simulated_run: bool = false
var simulated_jump: bool = false

var _yaw: float = 0.0
var _pitch: float = -0.32

@onready var _rig: Node3D = $CameraRig
@onready var _spring: SpringArm3D = $CameraRig/SpringArm3D
@onready var _body_pivot: Node3D = $BodyPivot


func _ready() -> void:
	_yaw = rotation.y
	if not use_simulated_input:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	_apply_camera_rotation()


func set_camera_yaw(yaw_rad: float) -> void:
	_yaw = yaw_rad
	_apply_camera_rotation()


func get_camera_yaw() -> float:
	return _yaw


func _unhandled_input(event: InputEvent) -> void:
	if use_simulated_input:
		return
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		var motion := event as InputEventMouseMotion
		_yaw -= motion.relative.x * mouse_sensitivity
		_pitch = clampf(
			_pitch - motion.relative.y * mouse_sensitivity,
			deg_to_rad(pitch_min_deg),
			deg_to_rad(pitch_max_deg)
		)
		_apply_camera_rotation()
	if event.is_action_pressed("ui_cancel"):
		# Esc releases / recaptures the mouse so the player can pause.
		if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
			Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		else:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _apply_camera_rotation() -> void:
	if is_inside_tree() and _rig != null:
		_rig.rotation = Vector3(_pitch, _yaw, 0.0)


func _physics_process(delta: float) -> void:
	var input_dir: Vector2 = Vector2.ZERO
	var running: bool = false
	var jump_pressed: bool = false

	if use_simulated_input:
		input_dir = simulated_move
		running = simulated_run
		jump_pressed = simulated_jump
		simulated_jump = false
	else:
		input_dir = Input.get_vector("move_left", "move_right", "move_forward", "move_back")
		running = Input.is_action_pressed("run")
		jump_pressed = Input.is_action_just_pressed("jump")

	# Gravity + jump
	if is_on_floor():
		if jump_pressed:
			velocity.y = jump_velocity
	else:
		velocity.y -= gravity * delta

	# Movement direction is relative to the camera yaw.
	var cam_basis := Basis(Vector3.UP, _yaw)
	var direction := cam_basis * Vector3(input_dir.x, 0.0, input_dir.y)
	direction.y = 0.0
	if direction.length() > 0.001:
		direction = direction.normalized()

	var target_speed: float = run_speed if running else walk_speed
	var target := direction * target_speed
	velocity.x = move_toward(velocity.x, target.x, acceleration * delta)
	velocity.z = move_toward(velocity.z, target.z, acceleration * delta)

	# Face the movement direction (mesh only; the capsule is symmetric).
	if direction.length() > 0.05 and _body_pivot != null:
		var target_yaw := atan2(direction.x, direction.z)
		_body_pivot.rotation.y = lerp_angle(_body_pivot.rotation.y, target_yaw, 12.0 * delta)

	move_and_slide()
