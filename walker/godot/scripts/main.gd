extends Node
## Entry point: builds the valley, the walker and the whole UI in code.

const SETTINGS_PATH := "user://settings.cfg"

var settings := {"lang": "ru", "gfx": "high"}
var font: Font = null
var registry: Dictionary = {"solids": []}

var world_root: Node3D = null
var player: CharacterBody3D = null
var sun: DirectionalLight3D = null
var env_node: WorldEnvironment = null
var menu_cam: Camera3D = null

var in_game := false
var paused_from_game := false
var settings_return := "menu"
var menu_time := 0.0
var lod_timer := 0.0
var hud_timer := 0.0
var nearest_sign: Dictionary = {}

# UI references
var ui: Control
var menu: Control
var settings_panel: Control
var bye_panel: Control
var read_panel: Control
var hud: Control
var btn_play: Button
var btn_settings: Button
var btn_quit: Button
var btn_back: Button
var btn_bye_back: Button
var btn_read_close: Button
var lang_opt: OptionButton
var gfx_opt: OptionButton
var lbl_title: Label
var lbl_sub: Label
var lbl_settings_title: Label
var lbl_lang: Label
var lbl_gfx: Label
var lbl_bye_title: Label
var lbl_bye: Label
var lbl_read_title: Label
var lbl_read_body: Label
var lbl_location: Label
var lbl_compass: Label
var lbl_hint: Label
var lbl_prompt: Label

func _ready() -> void:
	_load_settings()
	font = _load_font()
	_build_environment()
	world_root = Node3D.new()
	add_child(world_root)
	World.build_terrain(world_root, registry)
	World.build_water(world_root, registry)
	World.build_village(world_root, registry)
	World.build_forest(world_root, registry, _tree_count())
	World.build_falls(world_root, registry)
	World.build_props(world_root, registry)
	World.build_signs(world_root, registry, settings["lang"], font)
	_spawn_player()
	_build_ui()
	_apply_gfx()
	_apply_lang()
	_show_menu()

func _lang() -> String:
	return settings["lang"]

# ================================================================ environment

func _build_environment() -> void:
	env_node = WorldEnvironment.new()
	var env := Environment.new()
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.36, 0.55, 0.77)
	sky_mat.sky_horizon_color = Color(0.91, 0.81, 0.62)
	sky_mat.ground_horizon_color = Color(0.62, 0.60, 0.55)
	sky_mat.ground_bottom_color = Color(0.30, 0.28, 0.25)
	var sky := Sky.new()
	sky.sky_material = sky_mat
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.9
	env.tonemap_mode = Environment.TONE_MAPPER_ACES
	env.fog_enabled = true
	env.fog_light_color = Color(0.85, 0.79, 0.65)
	env.fog_density = 0.008
	env_node.environment = env
	add_child(env_node)
	sun = DirectionalLight3D.new()
	sun.light_color = Color(1.0, 0.85, 0.63)
	sun.light_energy = 1.4
	sun.shadow_enabled = true
	sun.rotation_degrees = Vector3(-50, -35, 0)
	add_child(sun)
	menu_cam = Camera3D.new()
	menu_cam.fov = 58.0
	add_child(menu_cam)

# ================================================================ player

func _spawn_player() -> void:
	player = CharacterBody3D.new()
	player.set_script(load("res://scripts/player.gd"))
	var cap := CapsuleShape3D.new()
	cap.radius = 0.35
	cap.height = 1.7
	var cs := CollisionShape3D.new()
	cs.shape = cap
	cs.position = Vector3(0, 0.85, 0)
	player.add_child(cs)
	add_child(player)
	player.setup(_load_soldier())
	var sx := 2.0
	var sz := 10.0
	player.position = Vector3(sx, World.height_at(sx, sz) + 0.2, sz)

func _load_soldier() -> Node3D:
	var doc := GLTFDocument.new()
	var st := GLTFState.new()
	var err := doc.append_from_file("res://assets/Soldier.glb", st)
	if err != OK:
		push_warning("Soldier.glb failed to load: %d" % err)
		return null
	var scene := doc.generate_scene(st)
	if scene is Node3D:
		var root: Node3D = scene
		_set_shadow_recursive(root)
		return root
	return null

func _set_shadow_recursive(n: Node) -> void:
	if n is GeometryInstance3D:
		var gi: GeometryInstance3D = n
		gi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	for c in n.get_children():
		_set_shadow_recursive(c)

# ================================================================ settings

func _load_settings() -> void:
	var cf := ConfigFile.new()
	if cf.load(SETTINGS_PATH) == OK:
		var l := str(cf.get_value("game", "lang", "ru"))
		var g := str(cf.get_value("game", "gfx", "high"))
		if l == "ru" or l == "en":
			settings["lang"] = l
		if g == "low" or g == "medium" or g == "high" or g == "ultra":
			settings["gfx"] = g

func _save_settings() -> void:
	var cf := ConfigFile.new()
	cf.set_value("game", "lang", settings["lang"])
	cf.set_value("game", "gfx", settings["gfx"])
	cf.save(SETTINGS_PATH)

func _tree_count() -> int:
	match settings["gfx"]:
		"low":
			return 70
		"medium":
			return 120
		"ultra":
			return 260
	return 190

func _apply_gfx() -> void:
	var g: String = settings["gfx"]
	if sun != null:
		sun.shadow_enabled = g != "low"
	var shadow_size := 2048
	match g:
		"low":
			shadow_size = 1024
		"medium":
			shadow_size = 1024
		"ultra":
			shadow_size = 4096
	RenderingServer.directional_shadow_atlas_set_size(shadow_size, false)
	var msaa := Viewport.MSAA_DISABLED
	if g == "high":
		msaa = Viewport.MSAA_2X
	elif g == "ultra":
		msaa = Viewport.MSAA_4X
	get_viewport().msaa_3d = msaa
	if env_node != null and env_node.environment != null:
		match g:
			"low":
				env_node.environment.fog_density = 0.02
			"medium":
				env_node.environment.fog_density = 0.012
			_:
				env_node.environment.fog_density = 0.006
	if world_root != null:
		World.build_forest(world_root, registry, _tree_count())

# ================================================================ UI

func _panel_style() -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.09, 0.11, 0.09, 0.94)
	sb.border_color = Color(0.91, 0.77, 0.48, 0.35)
	sb.set_border_width_all(1)
	sb.set_corner_radius_all(18)
	sb.set_content_margin_all(30)
	return sb

func _outline(l: Label) -> void:
	l.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.75))
	l.add_theme_constant_override("outline_size", 6)

func _center(cc_parent: Control, panel: Control) -> void:
	var cc := CenterContainer.new()
	cc.set_anchors_preset(Control.PRESET_FULL_RECT)
	cc.mouse_filter = Control.MOUSE_FILTER_IGNORE
	cc.add_child(panel)
	cc_parent.add_child(cc)

func _build_ui() -> void:
	ui = Control.new()
	ui.set_anchors_preset(Control.PRESET_FULL_RECT)
	ui.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(ui)
	var theme := Theme.new()
	if font != null:
		theme.default_font = font
	theme.default_font_size = 18
	ui.theme = theme
	# ---------- main / pause menu
	menu = PanelContainer.new()
	menu.add_theme_stylebox_override("panel", _panel_style())
	var mv := VBoxContainer.new()
	mv.add_theme_constant_override("separation", 10)
	menu.add_child(mv)
	lbl_title = Label.new()
	lbl_title.add_theme_font_size_override("font_size", 38)
	lbl_title.add_theme_color_override("font_color", Color(0.91, 0.77, 0.48))
	lbl_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	mv.add_child(lbl_title)
	lbl_sub = Label.new()
	lbl_sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	lbl_sub.modulate = Color(1, 1, 1, 0.7)
	mv.add_child(lbl_sub)
	var sp := Control.new()
	sp.custom_minimum_size = Vector2(0, 12)
	mv.add_child(sp)
	btn_play = Button.new()
	btn_play.custom_minimum_size = Vector2(280, 46)
	mv.add_child(btn_play)
	btn_settings = Button.new()
	btn_settings.custom_minimum_size = Vector2(280, 46)
	mv.add_child(btn_settings)
	btn_quit = Button.new()
	btn_quit.custom_minimum_size = Vector2(280, 46)
	mv.add_child(btn_quit)
	_center(ui, menu)
	# ---------- settings
	settings_panel = PanelContainer.new()
	settings_panel.add_theme_stylebox_override("panel", _panel_style())
	var sv := VBoxContainer.new()
	sv.add_theme_constant_override("separation", 8)
	settings_panel.add_child(sv)
	lbl_settings_title = Label.new()
	lbl_settings_title.add_theme_font_size_override("font_size", 26)
	lbl_settings_title.add_theme_color_override("font_color", Color(0.91, 0.77, 0.48))
	lbl_settings_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	sv.add_child(lbl_settings_title)
	lbl_lang = Label.new()
	sv.add_child(lbl_lang)
	lang_opt = OptionButton.new()
	lang_opt.custom_minimum_size = Vector2(280, 40)
	sv.add_child(lang_opt)
	lbl_gfx = Label.new()
	sv.add_child(lbl_gfx)
	gfx_opt = OptionButton.new()
	gfx_opt.custom_minimum_size = Vector2(280, 40)
	sv.add_child(gfx_opt)
	var sp2 := Control.new()
	sp2.custom_minimum_size = Vector2(0, 8)
	sv.add_child(sp2)
	btn_back = Button.new()
	btn_back.custom_minimum_size = Vector2(280, 46)
	sv.add_child(btn_back)
	_center(ui, settings_panel)
	# ---------- farewell
	bye_panel = PanelContainer.new()
	bye_panel.add_theme_stylebox_override("panel", _panel_style())
	var bv := VBoxContainer.new()
	bv.add_theme_constant_override("separation", 10)
	bye_panel.add_child(bv)
	lbl_bye_title = Label.new()
	lbl_bye_title.add_theme_font_size_override("font_size", 26)
	lbl_bye_title.add_theme_color_override("font_color", Color(0.91, 0.77, 0.48))
	lbl_bye_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	bv.add_child(lbl_bye_title)
	lbl_bye = Label.new()
	lbl_bye.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	bv.add_child(lbl_bye)
	btn_bye_back = Button.new()
	btn_bye_back.custom_minimum_size = Vector2(280, 46)
	bv.add_child(btn_bye_back)
	_center(ui, bye_panel)
	# ---------- sign reader
	read_panel = PanelContainer.new()
	read_panel.add_theme_stylebox_override("panel", _panel_style())
	var rv := VBoxContainer.new()
	rv.add_theme_constant_override("separation", 10)
	read_panel.add_child(rv)
	lbl_read_title = Label.new()
	lbl_read_title.add_theme_font_size_override("font_size", 24)
	lbl_read_title.add_theme_color_override("font_color", Color(0.91, 0.77, 0.48))
	rv.add_child(lbl_read_title)
	lbl_read_body = Label.new()
	lbl_read_body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	lbl_read_body.custom_minimum_size = Vector2(420, 0)
	rv.add_child(lbl_read_body)
	btn_read_close = Button.new()
	btn_read_close.custom_minimum_size = Vector2(280, 44)
	rv.add_child(btn_read_close)
	_center(ui, read_panel)
	# ---------- HUD
	hud = Control.new()
	hud.set_anchors_preset(Control.PRESET_FULL_RECT)
	hud.mouse_filter = Control.MOUSE_FILTER_IGNORE
	ui.add_child(hud)
	lbl_location = Label.new()
	_outline(lbl_location)
	lbl_location.position = Vector2(16, 14)
	hud.add_child(lbl_location)
	lbl_compass = Label.new()
	_outline(lbl_compass)
	lbl_compass.anchor_left = 0.5
	lbl_compass.anchor_right = 0.5
	lbl_compass.offset_left = -120
	lbl_compass.offset_right = 120
	lbl_compass.offset_top = 14
	lbl_compass.offset_bottom = 44
	lbl_compass.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hud.add_child(lbl_compass)
	lbl_hint = Label.new()
	_outline(lbl_hint)
	lbl_hint.anchor_top = 1.0
	lbl_hint.anchor_bottom = 1.0
	lbl_hint.offset_left = 16
	lbl_hint.offset_top = -70
	lbl_hint.offset_right = 560
	lbl_hint.offset_bottom = -14
	lbl_hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	hud.add_child(lbl_hint)
	lbl_prompt = Label.new()
	_outline(lbl_prompt)
	lbl_prompt.anchor_left = 0.5
	lbl_prompt.anchor_right = 0.5
	lbl_prompt.anchor_top = 1.0
	lbl_prompt.anchor_bottom = 1.0
	lbl_prompt.offset_left = -140
	lbl_prompt.offset_right = 140
	lbl_prompt.offset_top = -110
	lbl_prompt.offset_bottom = -80
	lbl_prompt.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	lbl_prompt.visible = false
	hud.add_child(lbl_prompt)
	# ---------- signals
	btn_play.pressed.connect(_on_play)
	btn_settings.pressed.connect(_on_open_settings)
	btn_quit.pressed.connect(_on_quit)
	btn_back.pressed.connect(_on_settings_back)
	btn_bye_back.pressed.connect(_on_bye_back)
	btn_read_close.pressed.connect(_on_read_close)
	lang_opt.item_selected.connect(_on_lang_selected)
	gfx_opt.item_selected.connect(_on_gfx_selected)

func _hide_panels() -> void:
	for p in [menu, settings_panel, bye_panel, read_panel]:
		if p != null:
			p.visible = false
	if hud != null:
		hud.visible = false

# ================================================================ modes

func _show_menu() -> void:
	in_game = false
	paused_from_game = false
	if player != null:
		player.enabled = false
	_hide_panels()
	menu.visible = true
	Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
	_apply_lang()

func _pause() -> void:
	in_game = false
	paused_from_game = true
	if player != null:
		player.enabled = false
	_hide_panels()
	menu.visible = true
	Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
	_apply_lang()

func _resume() -> void:
	in_game = true
	paused_from_game = false
	if player != null:
		player.enabled = true
		if player.cam != null:
			player.cam.current = true
	_hide_panels()
	hud.visible = true
	Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)

func _on_play() -> void:
	_resume()

func _on_open_settings() -> void:
	settings_return = "pause" if paused_from_game else "menu"
	_hide_panels()
	settings_panel.visible = true

func _on_settings_back() -> void:
	_hide_panels()
	menu.visible = true

func _on_quit() -> void:
	_hide_panels()
	bye_panel.visible = true
	Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)

func _on_bye_back() -> void:
	_show_menu()

func _on_read_close() -> void:
	_resume()

func _on_lang_selected(idx: int) -> void:
	settings["lang"] = "ru" if idx == 0 else "en"
	_save_settings()
	_apply_lang()

func _on_gfx_selected(idx: int) -> void:
	var keys := ["low", "medium", "high", "ultra"]
	if idx >= 0 and idx < keys.size():
		settings["gfx"] = keys[idx]
		_save_settings()
		_apply_gfx()

# ================================================================ language

func _apply_lang() -> void:
	var lang := _lang()
	lbl_title.text = Locale.t("title", lang)
	lbl_sub.text = Locale.t("sub", lang)
	btn_play.text = Locale.t("resume" if paused_from_game else "play", lang)
	btn_settings.text = Locale.t("settings", lang)
	btn_quit.text = Locale.t("quit", lang)
	btn_back.text = Locale.t("back", lang)
	btn_bye_back.text = Locale.t("back", lang)
	btn_read_close.text = Locale.t("close", lang)
	lbl_settings_title.text = Locale.t("settings_title", lang)
	lbl_lang.text = Locale.t("lang", lang)
	lbl_gfx.text = Locale.t("gfx", lang)
	lbl_bye_title.text = Locale.t("bye_title", lang)
	lbl_bye.text = Locale.t("bye", lang)
	lbl_hint.text = Locale.t("hint", lang)
	lang_opt.clear()
	lang_opt.add_item("Русский")
	lang_opt.add_item("English")
	lang_opt.selected = 0 if lang == "ru" else 1
	gfx_opt.clear()
	for k in ["low", "medium", "high", "ultra"]:
		gfx_opt.add_item(Locale.t("gfx_" + k, lang))
	var order := ["low", "medium", "high", "ultra"]
	gfx_opt.selected = order.find(settings["gfx"])
	World.refresh_signs(registry, lang)

# ================================================================ input

func _unhandled_input(event: InputEvent) -> void:
	if in_game and player != null and event is InputEventMouseMotion:
		if Input.get_mouse_mode() == Input.MOUSE_MODE_CAPTURED:
			player.look_input(event.relative)
	if event.is_action_pressed("ui_cancel"):
		if read_panel.visible:
			_on_read_close()
		elif settings_panel.visible:
			_on_settings_back()
		elif in_game:
			_pause()
		elif menu.visible and paused_from_game:
			_resume()
		return
	if not in_game or player == null:
		return
	if event is InputEventKey and event.pressed and not event.echo:
		var k: InputEventKey = event
		if k.physical_keycode == KEY_V:
			player.toggle_view()
		elif k.physical_keycode == KEY_E:
			_try_read_sign()

func _try_read_sign() -> void:
	if nearest_sign.is_empty():
		return
	var arr := Locale.t_arr(nearest_sign["key"], _lang())
	lbl_read_title.text = str(arr[0])
	lbl_read_body.text = str(arr[1])
	in_game = false
	if player != null:
		player.enabled = false
	_hide_panels()
	read_panel.visible = true
	hud.visible = false
	Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)

# ================================================================ frame loop

func _process(delta: float) -> void:
	menu_time += delta
	# ambient animation runs always (cheap)
	var wm = registry.get("water_mat")
	if wm != null:
		wm.uv1_offset += Vector3(0, delta * 0.03, 0)
	var fall_mats = registry.get("fall_mats")
	if fall_mats != null:
		for m in fall_mats:
			m.uv1_offset += Vector3(0, -delta * 0.6, 0)
	var fire = registry.get("fire_light")
	if fire != null:
		fire.light_energy = 2.2 + sin(menu_time * 13.0) * 0.9
	var flame = registry.get("flame")
	if flame != null and is_instance_valid(flame):
		flame.scale.y = 0.85 + sin(menu_time * 14.0) * 0.25
	if not in_game and not read_panel.visible:
		var a := menu_time * 0.08
		var x := sin(a) * 26.0
		var z := -30.0 + cos(a) * 18.0
		menu_cam.global_position = Vector3(x, World.height_at(x, z) + 8.0, z)
		menu_cam.look_at(Vector3(0, World.height_at(0.0, -24.0) + 2.0, -24.0), Vector3.UP)
		menu_cam.current = true
		return
	if not in_game or player == null:
		return
	lod_timer -= delta
	if lod_timer <= 0.0:
		lod_timer = 0.3
		var ppos := player.global_position
		World.update_lod_collisions(registry, ppos)
		World.update_tree_lod(registry, ppos)
	hud_timer -= delta
	if hud_timer <= 0.0:
		hud_timer = 0.2
		_update_hud()

func _update_hud() -> void:
	var lx := -sin(player.yaw)
	var lz := -cos(player.yaw)
	var ang := fmod(atan2(lx, -lz) + TAU, TAU)
	var idx := int(round(ang / (PI / 4.0))) % 8
	var compass_arr = Locale.t_arr("compass", _lang())
	if idx < compass_arr.size():
		lbl_compass.text = str(compass_arr[idx])
	lbl_location.text = Locale.t(_location_key(), _lang())
	# nearest sign
	nearest_sign = {}
	var best := 3.5
	for s in registry["signs"]:
		var d := Vector2(player.global_position.x - s["x"], player.global_position.z - s["z"]).length()
		if d < best:
			best = d
			nearest_sign = s
	lbl_prompt.visible = not nearest_sign.is_empty()
	if lbl_prompt.visible:
		lbl_prompt.text = Locale.t("press_e", _lang())

func _location_key() -> String:
	var p := player.global_position
	var h := World.height_at(p.x, p.z)
	if Vector2(p.x - 87.0, p.z - 14.0).length() < 26.0:
		return "loc_falls"
	if Vector2(p.x + 58.0, p.z + 92.0).length() < 42.0:
		return "loc_lake"
	if Vector2(p.x, p.z + 22.0).length() < 24.0:
		return "loc_village"
	if p.x < -18.0 and p.x > -105.0 and p.z > -82.0 and p.z < 42.0:
		return "loc_forest"
	if h > 13.0:
		return "loc_mountain"
	return "loc_valley"
