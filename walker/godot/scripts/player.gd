extends CharacterBody3D
## Walker controller: WASD + mouse look, 1st/3rd person toggle, Mixamo anims.

const WALK := 3.3
const RUN := 6.2
const JUMP := 5.4
const GRAVITY := 14.5
const BOUND := 185.0

var yaw := 0.0
var pitch := -0.08
var third := true
var enabled := false

var rig: Node3D = null
var anim: AnimationPlayer = null
var head: Node3D = null
var cam: Camera3D = null
var _cur_anim := ""

func setup(soldier: Node3D) -> void:
	rig = Node3D.new()
	add_child(rig)
	if soldier != null:
		rig.add_child(soldier)
		anim = _find_animation_player(soldier)
	head = Node3D.new()
	head.position = Vector3(0, 1.55, 0)
	add_child(head)
	cam = Camera3D.new()
	cam.fov = 70.0
	add_child(cam)

func _find_animation_player(node: Node) -> AnimationPlayer:
	if node is AnimationPlayer:
		return node
	for c in node.get_children():
		var found := _find_animation_player(c)
		if found != null:
			return found
	return null

func toggle_view() -> void:
	third = not third

func look_input(rel: Vector2) -> void:
	yaw -= rel.x * 0.0024
	pitch = clampf(pitch - rel.y * 0.0024, -1.35, 1.2)

func _physics_process(delta: float) -> void:
	if not enabled:
		return
	var ix := float(Input.is_physical_key_pressed(KEY_D)) - float(Input.is_physical_key_pressed(KEY_A))
	var iz := float(Input.is_physical_key_pressed(KEY_W)) - float(Input.is_physical_key_pressed(KEY_S))
	var running := Input.is_physical_key_pressed(KEY_SHIFT) and iz > 0.0
	var speed := RUN if running else WALK
	# camera looks along (-sin yaw, -cos yaw); forward input follows it
	var fwd := Vector3(-sin(yaw), 0.0, -cos(yaw))
	var right := Vector3(cos(yaw), 0.0, -sin(yaw))
	var dir := right * ix + fwd * iz
	if dir.length() > 0.01:
		dir = dir.normalized()
	velocity.x = dir.x * speed
	velocity.z = dir.z * speed
	if is_on_floor():
		velocity.y = 0.0
		if Input.is_physical_key_pressed(KEY_SPACE):
			velocity.y = JUMP
	else:
		velocity.y -= GRAVITY * delta
	move_and_slide()
	position.x = clampf(position.x, -BOUND, BOUND)
	position.z = clampf(position.z, -BOUND, BOUND)
	# character orientation + animation
	if rig != null:
		if dir.length() > 0.01:
			rig.rotation.y = atan2(-dir.x, -dir.z)
		else:
			rig.rotation.y = yaw
		rig.visible = third
		_play_anim("Run" if (running and dir.length() > 0.01) else ("Walk" if dir.length() > 0.01 else "Idle"))
	_update_camera()

func _play_anim(n: String) -> void:
	if anim == null or n == _cur_anim:
		return
	if anim.has_animation(n):
		anim.play(n, 0.25)
		_cur_anim = n

func _update_camera() -> void:
	if cam == null:
		return
	cam.current = true
	if not third:
		cam.position = head.position
		cam.rotation = Vector3(pitch, yaw, 0.0)
		return
	var cp := cos(pitch)
	var look := Vector3(-sin(yaw) * cp, sin(pitch), -cos(yaw) * cp)
	var target := global_position + Vector3(0.0, 1.45, 0.0)
	var pos := target - look * 3.6
	pos.y = maxf(pos.y, World.height_at(pos.x, pos.z) + 0.35)
	cam.global_position = pos
	cam.look_at(target, Vector3.UP)

func location() -> Vector3:
	return global_position
