class_name World
extends RefCounted
## Valley terrain math + world construction.
## Optimization model (per the design brief):
##  * solids closer than REAL_RADIUS to the player are "real" (collision enabled),
##    everything farther away is visual only (collision disabled);
##  * trees use two visual LOD tiers: detailed near, simplified far.

const WATER := -1.35
const SIZE := 380.0
const GRID := 128

const REAL_RADIUS := 5.0
const TREE_LOD_NEAR := 35.0
const TREE_LOD_FAR := 210.0

# ------------------------------------------------------------------ math

static func hashv(x: float, y: float) -> float:
	var h := sin(x * 127.1 + y * 311.7) * 43758.5453
	return h - floor(h)

static func smooth(a: float, b: float, t: float) -> float:
	var u := clampf((t - a) / (b - a), 0.0, 1.0)
	return u * u * (3.0 - 2.0 * u)

static func gauss(d: float, r: float) -> float:
	return exp(-(d * d) / (r * r))

const RIVER: Array = [
	Vector2(88, 14), Vector2(46, -6), Vector2(6, -34), Vector2(-30, -62), Vector2(-58, -92),
]

static func _seg_dist(p: Vector2, a: Vector2, b: Vector2) -> float:
	var ab := b - a
	var len2 := ab.length_squared()
	var t := 0.0
	if len2 > 0.0:
		t = clampf((p - a).dot(ab) / len2, 0.0, 1.0)
	return p.distance_to(a + ab * t)

static func river_dist(x: float, z: float) -> float:
	var p := Vector2(x, z)
	var d := 1e9
	for i in range(RIVER.size() - 1):
		d = minf(d, _seg_dist(p, RIVER[i], RIVER[i + 1]))
	return d

static func height_at(x: float, z: float) -> float:
	var h := 1.1 * sin(x * 0.05) * cos(z * 0.042) \
			+ 0.7 * sin(x * 0.11 + 1.7) * sin(z * 0.093 + 0.4) \
			+ 0.3 * sin(x * 0.23 + z * 0.19)
	h += pow(smooth(62.0, 155.0, z), 1.6) * (24.0 + 15.0 * hashv(floorf(x * 0.05), 7.0))
	h += pow(smooth(72.0, 165.0, x), 1.6) * (20.0 + 13.0 * hashv(3.0, floorf(z * 0.05)))
	h += pow(smooth(-95.0, -185.0, x), 1.5) * 13.0
	h += pow(smooth(-105.0, -185.0, z), 1.5) * 11.0
	# village plateau
	var vd := Vector2(x, z - (-22.0)).length()
	h *= 1.0 - 0.82 * gauss(vd, 42.0)
	h += 0.25 * gauss(vd, 42.0)
	# lake basin
	h -= 9.5 * gauss(Vector2(x + 58.0, z + 92.0).length(), 36.0)
	# river channel
	h -= 3.4 * gauss(river_dist(x, z), 6.5)
	# waterfall pool + cliff
	h -= 4.5 * gauss(Vector2(x - 87.0, z - 14.0).length(), 9.0)
	h += 13.0 * smooth(82.0, 95.0, x) * gauss(z - 14.0, 13.0)
	return h

static func slope_at(x: float, z: float) -> float:
	var e := 0.6
	var dx := height_at(x + e, z) - height_at(x - e, z)
	var dz := height_at(x, z + e) - height_at(x, z - e)
	return Vector2(dx, dz).length() / (2.0 * e)

# ------------------------------------------------------------------ helpers

static func _mat(color: Color, rough: float = 0.9) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = rough
	return m

static func _mesh_box(parent: Node3D, mesh_size: Vector3, color: Color, pos: Vector3) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = mesh_size
	mi.mesh = bm
	mi.material_override = _mat(color)
	mi.position = pos
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	parent.add_child(mi)
	return mi

static func _solid(parent: Node3D, registry: Dictionary, pos: Vector3, shape: Shape3D) -> void:
	var body := StaticBody3D.new()
	body.position = pos
	var cs := CollisionShape3D.new()
	cs.shape = shape
	cs.disabled = true  # enabled only while the player is within REAL_RADIUS
	body.add_child(cs)
	parent.add_child(body)
	registry["solids"].append({"pos": pos, "shape": cs})

static func _box_shape(w: float, h: float, d: float) -> BoxShape3D:
	var s := BoxShape3D.new()
	s.size = Vector3(w, h, d)
	return s

static func _cyl_shape(r: float, h: float) -> CylinderShape3D:
	var s := CylinderShape3D.new()
	s.radius = r
	s.height = h
	return s

static func _cone(bottom_r: float, h: float, segs: int) -> CylinderMesh:
	var m := CylinderMesh.new()
	m.top_radius = 0.0
	m.bottom_radius = bottom_r
	m.height = h
	m.radial_segments = segs
	return m

# ------------------------------------------------------------------ terrain

static func _terrain_color(h: float, s: float, x: float, z: float) -> Color:
	var c := Color()
	if h < WATER + 0.35:
		c = Color(0.46, 0.42, 0.32)
	elif h < 2.2:
		c = Color(0.30, 0.42, 0.20).lerp(Color(0.42, 0.50, 0.24), hashv(x * 3.0, z * 3.0))
	elif h < 9.0:
		c = Color(0.28, 0.38, 0.20).lerp(Color(0.36, 0.40, 0.24), hashv(x, z))
	elif h < 18.0:
		c = Color(0.42, 0.40, 0.34).lerp(Color(0.52, 0.50, 0.46), s * 0.6)
	else:
		c = Color(0.75, 0.77, 0.80).lerp(Color(0.93, 0.94, 0.96), smooth(18.0, 30.0, h))
	if s > 0.75 and h > 3.0:
		c = c.lerp(Color(0.45, 0.42, 0.38), minf(1.0, (s - 0.75) * 1.2))
	return c

static func build_terrain(parent: Node3D, registry: Dictionary) -> void:
	var step := SIZE / float(GRID)
	var verts := GRID + 1
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for j in range(verts):
		for i in range(verts):
			var x := -SIZE / 2.0 + i * step
			var z := -SIZE / 2.0 + j * step
			var h := height_at(x, z)
			st.set_color(_terrain_color(h, slope_at(x, z), x, z))
			st.add_vertex(Vector3(x, h, z))
	for j in range(GRID):
		for i in range(GRID):
			var a := j * verts + i
			var b := a + 1
			var c := a + verts
			var d := c + 1
			st.add_index(a)
			st.add_index(c)
			st.add_index(b)
			st.add_index(b)
			st.add_index(c)
			st.add_index(d)
	st.generate_normals()
	var mesh := st.commit()
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.roughness = 0.92
	mi.material_override = mat
	parent.add_child(mi)
	# collision: heightmap, z-major row layout matching vertex grid
	var data := PackedFloat32Array()
	data.resize(verts * verts)
	for j in range(verts):
		for i in range(verts):
			var x := -SIZE / 2.0 + i * step
			var z := -SIZE / 2.0 + j * step
			data[j * verts + i] = height_at(x, z)
	var hs := HeightMapShape3D.new()
	hs.map_width = verts
	hs.map_depth = verts
	hs.map_data = data
	var body := StaticBody3D.new()
	var cs := CollisionShape3D.new()
	cs.shape = hs
	cs.scale = Vector3(step, 1.0, step)
	body.add_child(cs)
	parent.add_child(body)

# ------------------------------------------------------------------ water

static func build_water(parent: Node3D, registry: Dictionary) -> void:
	var pm := PlaneMesh.new()
	pm.size = Vector2(SIZE * 1.2, SIZE * 1.2)
	var mi := MeshInstance3D.new()
	mi.mesh = pm
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.16, 0.36, 0.42, 0.86)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.roughness = 0.22
	mat.metallic = 0.35
	mat.uv1_scale = Vector3(24, 24, 1)
	mi.material_override = mat
	mi.position = Vector3(0, WATER, 0)
	parent.add_child(mi)
	registry["water_mat"] = mat

static func _fall_texture() -> ImageTexture:
	var img := Image.create(64, 256, false, Image.FORMAT_RGBA8)
	img.fill(Color(1, 1, 1, 0))
	var rng := RandomNumberGenerator.new()
	rng.seed = 77
	for i in range(42):
		var x := rng.randi_range(0, 61)
		var a := rng.randf_range(0.2, 0.7)
		for y in range(256):
			img.set_pixel(x, y, Color(1, 1, 1, a))
			img.set_pixel(x + 1, y, Color(1, 1, 1, a * 0.6))
	return ImageTexture.create_from_image(img)

static func build_falls(parent: Node3D, registry: Dictionary) -> void:
	var top_y := height_at(97.0, 14.0)
	var base_y := height_at(87.0, 14.0)
	var tex := _fall_texture()
	var mats: Array = []
	for off in [0.0, 0.35]:
		var qm := QuadMesh.new()
		qm.size = Vector2(7.0, top_y - base_y + 1.0)
		var mi := MeshInstance3D.new()
		mi.mesh = qm
		var mat := StandardMaterial3D.new()
		mat.albedo_texture = tex
		mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		mat.uv1_scale = Vector3(1, 2, 1)
		mat.cull_mode = BaseMaterial3D.CULL_DISABLED
		mi.material_override = mat
		mi.position = Vector3(90.0 - off, (top_y + base_y) / 2.0, 14.0)
		mi.rotation_degrees.y = -90.0
		parent.add_child(mi)
		mats.append(mat)
	registry["fall_mats"] = mats
	_mesh_box(parent, Vector3(2.4, 0.5, 7.0), Color(0.43, 0.40, 0.37), Vector3(95.5, top_y + 0.1, 14.0))
	# mist
	var p := GPUParticles3D.new()
	p.amount = 96
	p.lifetime = 2.2
	var pm := ParticleProcessMaterial.new()
	pm.direction = Vector3(-0.3, 0.6, 0)
	pm.spread = 35.0
	pm.initial_velocity_min = 1.2
	pm.initial_velocity_max = 2.6
	pm.gravity = Vector3(0, -2.0, 0)
	pm.scale_min = 0.8
	pm.scale_max = 2.2
	var sm := SphereMesh.new()
	sm.radius = 0.3
	sm.height = 0.6
	var mat2 := StandardMaterial3D.new()
	mat2.albedo_color = Color(0.93, 0.96, 0.98, 0.35)
	mat2.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat2.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	sm.material = mat2
	p.process_material = pm
	p.draw_pass_1 = sm
	p.position = Vector3(88.5, base_y + 0.6, 14.0)
	parent.add_child(p)

# ------------------------------------------------------------------ village

const HOUSES: Array = [
	{"x": -8.0, "z": -16.0, "r": 0.3, "w": 4.2, "d": 3.4, "c": Color(0.81, 0.76, 0.66), "roof": Color(0.54, 0.29, 0.20)},
	{"x": 2.0, "z": -26.0, "r": -0.4, "w": 4.8, "d": 3.8, "c": Color(0.85, 0.80, 0.69), "roof": Color(0.46, 0.25, 0.17)},
	{"x": 11.0, "z": -18.0, "r": 0.9, "w": 3.8, "d": 3.2, "c": Color(0.77, 0.70, 0.58), "roof": Color(0.56, 0.35, 0.23)},
	{"x": -14.0, "z": -28.0, "r": -1.1, "w": 4.4, "d": 3.6, "c": Color(0.82, 0.75, 0.63), "roof": Color(0.43, 0.24, 0.16)},
	{"x": 8.0, "z": -34.0, "r": 2.2, "w": 4.0, "d": 3.4, "c": Color(0.80, 0.72, 0.60), "roof": Color(0.52, 0.28, 0.18)},
	{"x": -2.0, "z": -8.0, "r": 1.7, "w": 3.6, "d": 3.0, "c": Color(0.86, 0.81, 0.71), "roof": Color(0.49, 0.27, 0.19)},
]

static func build_village(parent: Node3D, registry: Dictionary) -> void:
	for H in HOUSES:
		var g := Node3D.new()
		var gh := height_at(H["x"], H["z"])
		g.position = Vector3(H["x"], gh, H["z"])
		g.rotation.y = H["r"]
		parent.add_child(g)
		var w: float = H["w"]
		var d: float = H["d"]
		var body_h := 2.3
		_mesh_box(g, Vector3(w, body_h, d), H["c"], Vector3(0, body_h / 2.0, 0))
		var roof := MeshInstance3D.new()
		var prm := PrismMesh.new()
		prm.size = Vector3(w + 0.7, 1.6, d + 0.7)
		roof.mesh = prm
		roof.material_override = _mat(H["roof"], 0.8)
		roof.position = Vector3(0, body_h + 0.8, 0)
		roof.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		g.add_child(roof)
		_mesh_box(g, Vector3(0.9, 1.5, 0.14), Color(0.29, 0.20, 0.13), Vector3(0, 0.75, d / 2.0 + 0.05))
		var win := MeshInstance3D.new()
		var qm := QuadMesh.new()
		qm.size = Vector2(0.55, 0.55)
		win.mesh = qm
		var wm := StandardMaterial3D.new()
		wm.albedo_color = Color(1.0, 0.79, 0.42)
		wm.emission_enabled = true
		wm.emission = Color(1.0, 0.62, 0.23)
		wm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		win.material_override = wm
		win.position = Vector3(w / 3.0, 1.45, d / 2.0 + 0.06)
		g.add_child(win)
		_mesh_box(g, Vector3(0.45, 1.1, 0.45), Color(0.47, 0.42, 0.35), Vector3(-w / 4.0, body_h + 0.9, -d / 5.0))
		var pos := Vector3(H["x"], gh, H["z"])
		_solid(parent, registry, pos + Vector3(0, body_h / 2.0, 0), _box_shape(w + 0.5, body_h + 1.5, d + 0.5))
	# well
	var wy := height_at(1.0, -19.0)
	var well := Node3D.new()
	well.position = Vector3(1.0, wy, -19.0)
	parent.add_child(well)
	var ring := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = 0.95
	cm.bottom_radius = 1.05
	cm.height = 0.9
	ring.mesh = cm
	ring.material_override = _mat(Color(0.55, 0.52, 0.48), 0.95)
	ring.position = Vector3(0, 0.45, 0)
	ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	well.add_child(ring)
	_mesh_box(well, Vector3(0.12, 1.7, 0.12), Color(0.42, 0.29, 0.18), Vector3(-0.85, 0.85, 0))
	_mesh_box(well, Vector3(0.12, 1.7, 0.12), Color(0.42, 0.29, 0.18), Vector3(0.85, 0.85, 0))
	var wroof := MeshInstance3D.new()
	var prm2 := PrismMesh.new()
	prm2.size = Vector3(2.4, 0.7, 2.4)
	wroof.mesh = prm2
	wroof.material_override = _mat(Color(0.46, 0.25, 0.17), 0.8)
	wroof.position = Vector3(0, 2.0, 0)
	well.add_child(wroof)
	_solid(parent, registry, Vector3(1.0, wy + 0.6, -19.0), _cyl_shape(1.15, 1.6))
	# fences (visual only, decor)
	var fm := _mat(Color(0.48, 0.36, 0.24), 0.9)
	var bm := BoxMesh.new()
	bm.size = Vector3(0.12, 0.9, 0.12)
	var mmi := MultiMeshInstance3D.new()
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = bm
	var spots: Array = []
	for i in range(26):
		if hashv(float(i), 11.0) < 0.25:
			continue
		var a := float(i) / 26.0 * TAU
		var x := cos(a) * 17.0
		var z := -20.0 + sin(a) * 14.0
		spots.append(Transform3D(Basis(), Vector3(x, height_at(x, z) + 0.45, z)))
	mm.instance_count = spots.size()
	for i in range(spots.size()):
		mm.set_instance_transform(i, spots[i])
	mmi.multimesh = mm
	mmi.material_override = fm
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	parent.add_child(mmi)
	# lamps
	for pos in [Vector2(-5, -12), Vector2(7, -24)]:
		var gy := height_at(pos.x, pos.y)
		_mesh_box(parent, Vector3(0.14, 2.6, 0.14), Color(0.25, 0.20, 0.16), Vector3(pos.x, gy + 1.3, pos.y))
		var bulb := MeshInstance3D.new()
		var sm := SphereMesh.new()
		sm.radius = 0.16
		sm.height = 0.32
		bulb.mesh = sm
		var lm := StandardMaterial3D.new()
		lm.albedo_color = Color(1.0, 0.82, 0.48)
		lm.emission_enabled = true
		lm.emission = Color(1.0, 0.7, 0.28)
		lm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		bulb.material_override = lm
		bulb.position = Vector3(pos.x, gy + 2.65, pos.y)
		parent.add_child(bulb)
		var omni := OmniLight3D.new()
		omni.light_color = Color(1.0, 0.72, 0.36)
		omni.light_energy = 1.6
		omni.omni_range = 14.0
		omni.omni_attenuation = 1.4
		omni.position = Vector3(pos.x, gy + 2.5, pos.y)
		parent.add_child(omni)

# ------------------------------------------------------------------ forest (two-tier LOD)

static func tree_spots(count: int) -> Array:
	var rng := RandomNumberGenerator.new()
	rng.seed = 1234
	var spots: Array = []
	var guard := 0
	while spots.size() < count and guard < count * 12:
		guard += 1
		var x := rng.randf_range(-100.0, -18.0)
		var z := rng.randf_range(-78.0, 38.0)
		var h := height_at(x, z)
		if h < 0.4 or h > 15.0 or slope_at(x, z) > 0.9:
			continue
		if Vector2(x, z + 22.0).length() < 24.0:
			continue
		if river_dist(x, z) < 7.0:
			continue
		var ok := true
		for p in spots:
			var t: Transform3D = p
			if Vector2(t.origin.x - x, t.origin.z - z).length_squared() < 14.0:
				ok = false
				break
		if not ok:
			continue
		var s := rng.randf_range(0.75, 1.6)
		var basis := Basis(Vector3.UP, rng.randf_range(0.0, TAU)).scaled(Vector3(s, s * rng.randf_range(0.9, 1.25), s))
		spots.append(Transform3D(basis, Vector3(x, h - 0.1, z)))
	return spots

static func build_forest(parent: Node3D, registry: Dictionary, count: int) -> void:
	var forest_root: Node3D = registry.get("forest_root")
	if forest_root != null and is_instance_valid(forest_root):
		forest_root.queue_free()
	forest_root = Node3D.new()
	parent.add_child(forest_root)
	var spots := tree_spots(count)
	# near LOD meshes
	var trunk_mesh := CylinderMesh.new()
	trunk_mesh.top_radius = 0.13
	trunk_mesh.bottom_radius = 0.24
	trunk_mesh.height = 2.4
	trunk_mesh.radial_segments = 7
	var cone_mesh := _cone(1.25, 2.6, 8)
	var cone_mesh2 := _cone(0.9, 2.0, 8)
	# far LOD mesh: single cone
	var far_mesh := _cone(1.35, 4.6, 5)
	var near: Array = []
	near.append(_make_mmi(forest_root, trunk_mesh, _mat(Color(0.42, 0.29, 0.19), 0.95), Vector3(0, 1.2, 0)))
	near.append(_make_mmi(forest_root, cone_mesh, _mat(Color(0.18, 0.29, 0.16), 0.9), Vector3(0, 3.2, 0)))
	near.append(_make_mmi(forest_root, cone_mesh2, _mat(Color(0.22, 0.38, 0.18), 0.9), Vector3(0, 4.6, 0)))
	var far: Array = []
	far.append(_make_mmi(forest_root, far_mesh, _mat(Color(0.16, 0.27, 0.15), 0.95), Vector3(0, 2.3, 0)))
	registry["forest_root"] = forest_root
	registry["trees"] = {"transforms": spots, "near": near, "far": far}
	update_tree_lod(registry, Vector3.ZERO)
	# colliders for trunks ("real" only within REAL_RADIUS); they live under
	# forest_root so they are freed together with the visuals on rebuild
	for t in spots:
		var tr: Transform3D = t
		_solid(forest_root, registry, tr.origin + Vector3(0, 1.1, 0), _cyl_shape(0.42, 2.4))

static func _make_mmi(parent: Node3D, mesh: Mesh, mat: StandardMaterial3D, offset: Vector3) -> MultiMeshInstance3D:
	var mmi := MultiMeshInstance3D.new()
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = mesh
	mmi.multimesh = mm
	mmi.material_override = mat
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	mmi.set_meta("lod_offset", offset)
	parent.add_child(mmi)
	return mmi

static func _fill_tier(instances: Array, transforms: Array) -> void:
	for mmi in instances:
		var inst: MultiMeshInstance3D = mmi
		var mm := inst.multimesh
		var off: Vector3 = inst.get_meta("lod_offset")
		mm.instance_count = transforms.size()
		for i in range(transforms.size()):
			var t: Transform3D = transforms[i]
			t.origin += off
			mm.set_instance_transform(i, t)

static func update_tree_lod(registry: Dictionary, player_pos: Vector3) -> void:
	var t: Dictionary = registry.get("trees", {})
	if t.is_empty():
		return
	var near_list: Array = []
	var far_list: Array = []
	for tr in t["transforms"]:
		var xf: Transform3D = tr
		var d := player_pos.distance_to(xf.origin)
		if d < TREE_LOD_NEAR:
			near_list.append(tr)
		elif d < TREE_LOD_FAR:
			far_list.append(tr)
	_fill_tier(t["near"], near_list)
	_fill_tier(t["far"], far_list)

static func update_lod_collisions(registry: Dictionary, player_pos: Vector3) -> void:
	var solids: Array = registry["solids"]
	# drop entries whose shape was freed (e.g. forest rebuilt on gfx change)
	for i in range(solids.size() - 1, -1, -1):
		if not is_instance_valid(solids[i]["shape"]):
			solids.remove_at(i)
	for s in solids:
		var shape: CollisionShape3D = s["shape"]
		var pos: Vector3 = s["pos"]
		shape.disabled = player_pos.distance_to(pos) > REAL_RADIUS + 1.5

# ------------------------------------------------------------------ props

static func build_props(parent: Node3D, registry: Dictionary) -> void:
	# bridge
	var bridge := Node3D.new()
	bridge.position = Vector3(40.0, height_at(40.0, -12.0) + 0.25, -12.0)
	bridge.rotation.y = 0.7
	parent.add_child(bridge)
	_mesh_box(bridge, Vector3(1.7, 0.14, 8.2), Color(0.55, 0.42, 0.27), Vector3(0, 0.55, 0))
	_mesh_box(bridge, Vector3(0.1, 0.7, 8.2), Color(0.42, 0.29, 0.18), Vector3(-0.8, 0.95, 0))
	_mesh_box(bridge, Vector3(0.1, 0.7, 8.2), Color(0.42, 0.29, 0.18), Vector3(0.8, 0.95, 0))
	# dock
	var dock := Node3D.new()
	dock.position = Vector3(-46.0, maxf(WATER + 0.12, height_at(-46.0, -72.0)), -72.0)
	dock.rotation.y = 0.5
	parent.add_child(dock)
	_mesh_box(dock, Vector3(1.5, 0.12, 6.4), Color(0.60, 0.45, 0.30), Vector3(0, 0.25, 0))
	_mesh_box(dock, Vector3(0.12, 1.4, 0.12), Color(0.42, 0.29, 0.17), Vector3(-0.6, -0.35, -2.8))
	_mesh_box(dock, Vector3(0.12, 1.4, 0.12), Color(0.42, 0.29, 0.17), Vector3(0.6, -0.35, -2.8))
	# campfire
	var fx := -16.0
	var fz := -8.0
	var fy := height_at(fx, fz)
	_mesh_box(parent, Vector3(0.95, 0.16, 0.95), Color(0.24, 0.22, 0.20), Vector3(fx, fy + 0.08, fz))
	var logs := MeshInstance3D.new()
	var lcm := CylinderMesh.new()
	lcm.top_radius = 0.07
	lcm.bottom_radius = 0.07
	lcm.height = 0.75
	logs.mesh = lcm
	logs.material_override = _mat(Color(0.42, 0.29, 0.17))
	logs.position = Vector3(fx, fy + 0.24, fz)
	logs.rotation_degrees = Vector3(0, 23, 90)
	parent.add_child(logs)
	var flame := MeshInstance3D.new()
	flame.mesh = _cone(0.17, 0.55, 6)
	var fmat := StandardMaterial3D.new()
	fmat.albedo_color = Color(1.0, 0.69, 0.35)
	fmat.emission_enabled = true
	fmat.emission = Color(1.0, 0.55, 0.18)
	fmat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	flame.material_override = fmat
	flame.position = Vector3(fx, fy + 0.44, fz)
	flame.name = "Flame"
	parent.add_child(flame)
	var fire := OmniLight3D.new()
	fire.light_color = Color(1.0, 0.48, 0.23)
	fire.light_energy = 2.2
	fire.omni_range = 13.0
	fire.position = Vector3(fx, fy + 0.8, fz)
	parent.add_child(fire)
	registry["fire_light"] = fire
	registry["flame"] = flame
	# boulders
	for b in [
		Vector3(-18, 108, 1.6), Vector3(28, 128, 2.2), Vector3(6, 152, 2.6),
		Vector3(48, 96, 1.3), Vector3(-40, 140, 1.8), Vector3(112, 40, 2.4),
	]:
		var y := height_at(b.x, b.y)
		var rock := MeshInstance3D.new()
		rock.mesh = _dodeca(b.z)
		var col := Color(0.84, 0.86, 0.88) if y > 16.0 else Color(0.54, 0.52, 0.49)
		rock.material_override = _mat(col, 0.94)
		rock.position = Vector3(b.x, y + b.z * 0.35, b.y)
		rock.rotation = Vector3(0.2, b.z, 0.4)
		rock.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		parent.add_child(rock)
		var sh := SphereShape3D.new()
		sh.radius = b.z * 0.8
		_solid(parent, registry, Vector3(b.x, y + b.z * 0.35, b.y), sh)

static func _dodeca(r: float) -> Mesh:
	var sm := SphereMesh.new()
	sm.radius = r
	sm.height = r * 2.0
	sm.radial_segments = 6
	sm.rings = 4
	return sm

# ------------------------------------------------------------------ signs

const SIGN_SPOTS: Array = [
	{"key": "sign_village", "x": 4.0, "z": 2.0},
	{"key": "sign_forest", "x": -26.0, "z": -12.0},
	{"key": "sign_mountain", "x": 30.0, "z": 44.0},
	{"key": "sign_falls", "x": 74.0, "z": 6.0},
	{"key": "sign_lake", "x": -38.0, "z": -64.0},
]

static func build_signs(parent: Node3D, registry: Dictionary, lang: String, font: Font) -> void:
	var old: Node3D = registry.get("sign_root")
	if old != null and is_instance_valid(old):
		old.queue_free()
	var root := Node3D.new()
	parent.add_child(root)
	var list: Array = []
	for spot in SIGN_SPOTS:
		var g := Node3D.new()
		var y := height_at(spot["x"], spot["z"])
		g.position = Vector3(spot["x"], y, spot["z"])
		g.rotation.y = atan2(2.0 - spot["x"], 8.0 - spot["z"])
		root.add_child(g)
		_mesh_box(g, Vector3(0.14, 1.9, 0.14), Color(0.35, 0.26, 0.17), Vector3(0, 0.95, 0))
		var board := MeshInstance3D.new()
		var bm := BoxMesh.new()
		bm.size = Vector3(1.7, 0.85, 0.08)
		board.mesh = bm
		board.material_override = _mat(Color(0.48, 0.36, 0.24), 0.85)
		board.position = Vector3(0, 1.75, 0)
		board.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		g.add_child(board)
		var label := Label3D.new()
		label.text = str(Locale.t_arr(spot["key"], lang)[0])
		if font != null:
			label.font = font
		label.font_size = 64
		label.pixel_size = 0.005
		label.modulate = Color(0.95, 0.89, 0.76)
		label.position = Vector3(0, 1.75, 0.06)
		g.add_child(label)
		list.append({"x": spot["x"], "z": spot["z"], "key": spot["key"], "label": label})
	registry["sign_root"] = root
	registry["signs"] = list

static func refresh_signs(registry: Dictionary, lang: String) -> void:
	for s in registry["signs"]:
		var label: Label3D = s["label"]
		var arr := Locale.t_arr(s["key"], lang)
		label.text = str(arr[0])
