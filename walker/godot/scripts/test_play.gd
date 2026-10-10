extends Node
## Headless playthrough: instantiates the real main scene, presses "Play",
## walks the character across the map and validates the LOD/collision system.

var main: Node
var player: CharacterBody3D
var frame := 0

func _ready() -> void:
	var ms: PackedScene = load("res://scenes/main.tscn")
	main = ms.instantiate()
	add_child(main)

func _process(_delta: float) -> void:
	frame += 1
	if frame == 2:
		player = main.player
		print("CHECK player=", player != null)
		print("CHECK rig=", player.rig != null, " anim=", player.anim != null)
		if player.anim != null:
			print("CHECK anims=", player.anim.get_animation_list())
		print("CHECK solids=", main.registry["solids"].size(), " signs=", main.registry["signs"].size())
		main._resume()
	elif frame > 10 and frame % 5 == 0 and frame <= 200:
		var t := float(frame) / 200.0
		var x := lerpf(2.0, -60.0, t)
		var z := lerpf(10.0, -60.0, t)
		player.global_position = Vector3(x, World.height_at(x, z) + 1.0, z)
	elif frame == 205:
		var near_on := 0
		var far_off := 0
		for s in main.registry["solids"]:
			if not is_instance_valid(s["shape"]):
				continue
			var d: float = (s["pos"] - player.global_position).length()
			if d <= 6.5 and not s["shape"].disabled:
				near_on += 1
			if d > 6.5 and s["shape"].disabled:
				far_off += 1
		print("CHECK near_on=", near_on, " far_off=", far_off)
		var trees: Dictionary = main.registry["trees"]
		print("CHECK tree_near=", trees["near"][0].multimesh.instance_count, " tree_far=", trees["far"][0].multimesh.instance_count)
		print("CHECK loc=", main._location_key())
		player.toggle_view()
		player.look_input(Vector2(120, 30))
		player.global_position = Vector3(4.0, World.height_at(4.0, 2.0) + 1.0, 2.0)
		main._update_hud()
		print("CHECK sign_found=", not main.nearest_sign.is_empty())
		main._try_read_sign()
		print("CHECK read_panel_visible=", main.read_panel.visible)
	elif frame == 230:
		main._on_read_close()
		print("CHECK after_close_in_game=", main.in_game)
		print("TEST_OK")
		get_tree().quit(0)
