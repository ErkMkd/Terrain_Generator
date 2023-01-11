
import harfang as hg
from overlays import *
import data_converter as dc
import grid_generator
from math import pi

class Terrain:
	SHADER_TYPE_FLAT = 0
	SHADER_TYPE_VERTEX = 1
	SHADER_TYPE_FRAGMENT = 2


	@staticmethod
	def compute_vertex_faces_links(vertices_count, faces):
		vertex_faces_links = []
		for v_idx in range(vertices_count):
			vertex_faces_links.append([])
			for f_idx in range(len(faces)):
				face = faces[f_idx]
				for vf_idx in face:
					if vf_idx == v_idx:
						vertex_faces_links[v_idx].append(f_idx)
		return vertex_faces_links

	def __init__(self, scene, resolution, pipeline_resources, x_size, z_size, height, grid_x, grid_z):

		self.scene = scene
		self.resolution = resolution
		self.sun = scene.GetNode("Sun")
		self.pipeline_resources = pipeline_resources

		self.shader_type = Terrain.SHADER_TYPE_FLAT

		self.vs_decl = hg.VertexLayout()
		self.vs_decl.Begin()
		self.vs_decl.Add(hg.A_Position, 3, hg.AT_Float)
		self.vs_decl.Add(hg.A_Normal, 3, hg.AT_Uint8, True, True)
		self.vs_decl.Add(hg.A_TexCoord0, 3, hg.AT_Float)
		self.vs_decl.End()

		self.terrain_fragment_prg_ref = hg.LoadPipelineProgramRefFromAssets('shaders/pbr_height_fragment.hps', self.pipeline_resources, hg.GetForwardPipelineInfo())
		self.terrain_vertex_prg_ref = hg.LoadPipelineProgramRefFromAssets('shaders/pbr_height_vertex.hps', self.pipeline_resources, hg.GetForwardPipelineInfo())
		self.terrain_flat_prg_ref = hg.LoadPipelineProgramRefFromAssets('shaders/pbr_height_flat.hps', self.pipeline_resources, hg.GetForwardPipelineInfo())
		self.terrain_shaders = {
			Terrain.SHADER_TYPE_FLAT: self.terrain_flat_prg_ref,
			Terrain.SHADER_TYPE_VERTEX: self.terrain_vertex_prg_ref,
			Terrain.SHADER_TYPE_FRAGMENT: self.terrain_fragment_prg_ref
				}

		self.water_prg_ref = hg.LoadPipelineProgramRefFromAssets('shaders/water_pbr.hps', self.pipeline_resources, hg.GetForwardPipelineInfo())

		self.size = hg.Vec3(x_size, height, z_size)
		self.grid_size = hg.iVec2(grid_x, grid_z)
		self.triangles_count = (grid_x) * (grid_z) * 2
		self.vertices_count = (grid_x + 1) * (grid_z + 1)
		self.vertices = []
		self.triangles = []
		self.normales_triangles = []
		self.uvs = []
		self.edges = []

		self.optim_triangles_count = 0
		self.optim_vertices_count = 0
		self.optim_vertices = []
		self.optim_triangles = []
		self.optim_normales_triangles = []
		self.optim_uvs = []
		self.optim_edges = []

		self.vertices_flat = []
		self.triangles_flat = []
		self.normales_flat = []
		self.uvs_flat = []

		self.normal_sample_radius = 0.02
		self.grass_value = hg.Vec2(0.95, 1)
		self.model = None
		self.model_ref = None
		self.water_model = None
		self.water_model_ref = None
		self.material = None
		self.material_water = None

		self.grid_geo_file = "assets_compiled/grides/Plane256.geo"

		self.terrain_picture_filename = "assets/textures/texture_terrain_start.png"
		self.terrain_picture = None

		self.terrain_node = None
		self.water_node = None

		self.map_texture = None
		self.map_texture_ref = None

		self.map_1_scale = hg.Vec3(0.3, -0.3, 0.3)
		self.map_2_scale = hg.Vec3(0.4, 1, 0.5)
		self.map_3_scale = hg.Vec3(30, 0.07, 20)

		self.map_1_offset = hg.Vec2(0, 0)
		self.map_2_offset = hg.Vec2(0, 0)
		self.map_3_offset = hg.Vec2(0, 0)

		self.color_grass = hg.Color(58 / 255, 116 / 255, 30 / 255, 1)
		self.color_water = hg.Color(19 / 255, 119 / 255, 232 / 255, 1)
		self.color_mineral1 = hg.Color(105 / 255, 135 / 255, 97 / 255, 1)
		self.color_mineral2 = hg.Color(156 / 255, 131 / 255, 82 / 255, 1)

		self.mineral_fading = hg.Vec2(0.01, 0.3) * 1000
		self.water_altitude = -0.06 * 1000
		self.water_fresnel_near = 0.8
		self.water_fresnel_far = 0.2
		self.water_noises_texture = hg.LoadTextureFromAssets("textures/ocean_noises.png", 0)[0]
		self.water_noises_texture_ref = self.pipeline_resources.AddTexture("water_noises", self.water_noises_texture)
		self.waves_scale = hg.Vec3(1, 10, 1)
		self.waves_speed = 1

		self.terrain_offset = hg.Vec3(0, 0, 0)
		self.global_scale = 1

		self.generate_grid()
		self.generate_materials()

		# Optimization:
		self.map_1_scale_xz = None
		self.map_2_scale_xz = None
		self.map_3_scale_xz = None

	def set_state(self, state):
		self.remove_model()
		self.remove_grid()
		self.size = dc.list_to_vec3(state["size"])
		self.grid_size = dc.list_to_iVec2(state["grid_size"])
		self.normal_sample_radius = state["normal_sample_radius"]
		self.grass_value = dc.list_to_vec2(state["grass_value"])
		self.map_1_scale = dc.list_to_vec3(state["map_1_scale"])
		self.map_2_scale = dc.list_to_vec3(state["map_2_scale"])
		self.map_3_scale = dc.list_to_vec3(state["map_3_scale"])
		self.map_1_offset = dc.list_to_vec2(state["map_1_offset"])
		self.map_2_offset = dc.list_to_vec2(state["map_2_offset"])
		self.map_3_offset = dc.list_to_vec2(state["map_3_offset"])
		self.terrain_offset = dc.list_to_vec3(state["terrain_offset"])
		self.color_water = dc.list_to_color(state["color_water"])
		self.color_grass = dc.list_to_color(state["color_grass"])
		self.color_mineral1 = dc.list_to_color(state["color_mineral1"])
		self.color_mineral2 = dc.list_to_color(state["color_mineral2"])
		self.mineral_fading = dc.list_to_vec2(state["mineral_fading"])
		self.water_altitude = state["water_altitude"]
		if "waves_scale" in state:
			self.waves_scale = dc.list_to_vec3(state["waves_scale"])
		if "waves_speed" in state:
			self.waves_speed = state["waves_speed"]

		if "global_scale" in state:
			self.global_scale = state["global_scale"]
		else:
			self.global_scale = 1
		if "water_fresnel" in state:
			self.water_fresnel_near = state["water_fresnel"][0]
			self.water_fresnel_far = state["water_fresnel"][1]

		self.generate_grid()
		self.generate_materials()
		#self.update_material_values()

	def get_state(self):
		state = {
			"size": dc.vec3_to_list(self.size),
			"grid_size": dc.iVec2_to_list(self.grid_size),
			"normal_sample_radius": self.normal_sample_radius,
			"grass_value": dc.vec2_to_list(self.grass_value),
			"map_1_scale": dc.vec3_to_list(self.map_1_scale),
			"map_2_scale": dc.vec3_to_list(self.map_2_scale),
			"map_3_scale": dc.vec3_to_list(self.map_3_scale),
			"map_1_offset": dc.vec2_to_list(self.map_1_offset),
			"map_2_offset": dc.vec2_to_list(self.map_2_offset),
			"map_3_offset": dc.vec2_to_list(self.map_3_offset),
			"terrain_offset": dc.vec3_to_list(self.terrain_offset),
			"color_water": dc.color_to_list(self.color_water),
			"color_grass": dc.color_to_list(self.color_grass),
			"color_mineral1": dc.color_to_list(self.color_mineral1),
			"color_mineral2": dc.color_to_list(self.color_mineral2),
			"mineral_fading": dc.vec2_to_list(self.mineral_fading),
			"water_altitude": self.water_altitude,
			"water_fresnel": [self.water_fresnel_near, self.water_fresnel_far],
			"global_scale" : self.global_scale,
			"waves_scale": dc.vec3_to_list(self.waves_scale),
			"waves_speed": self.waves_speed
		}
		return state

	def destroy(self):
		self.remove_model()
		self.remove_grid()
		self.remove_height_map()

	def remove_height_map(self):
		if self.map_texture_ref is not None:
			self.pipeline_resources.DestroyTexture(self.map_texture_ref)
			self.map_texture_ref = None

	def remove_model(self):
		if self.terrain_node is not None:
			self.scene.DestroyNode(self.terrain_node)
			hg.SceneGarbageCollectSystems(self.scene)
			self.pipeline_resources.DestroyModel(self.model_ref)
		if self.water_node is not None:
			self.scene.DestroyNode(self.water_node)
			hg.SceneGarbageCollectSystems(self.scene)
			self.pipeline_resources.DestroyModel(self.water_model_ref)

		self.model = None
		self.model_ref = None
		self.water_model = None
		self.water_model_ref = None
		self.material = None
		self.material_water = None

	def remove_grid(self):

		self.triangles_count = 0
		self.vertices_count = 0
		self.vertices = []
		self.triangles = []
		self.normales_triangles = []
		self.uvs = []
		self.edges = []

	def set_grid_size(self, grid_scale: hg.Vec3, grid_size: hg.iVec2):
		self.remove_model()
		self.remove_grid()
		scale_factor = grid_scale.x / self.size.x
		self.grid_size = hg.iVec2(grid_size)
		self.size = hg.Vec3(grid_scale)
		self.generate_grid()
		self.generate_materials()
		self.generate_nodes()

		self.scene.environment.fog_near *= scale_factor
		self.scene.environment.fog_far *= scale_factor
		self.mineral_fading *= scale_factor
		self.water_altitude *= scale_factor
		self.terrain_offset.y *= scale_factor

		self.update_material_values()

	@staticmethod
	def get_data_bilinear(picture, w, h, pos: hg.Vec2):
		x = (pos.x * w - 0.5) % w
		y = (pos.y * h - 0.5) % h
		xi = int(x)
		yi = int(y)
		xf = x - xi
		yf = y - yi
		xi1 = (xi + 1) % w
		yi1 = (yi + 1) % h

		# Picture is a list:
		#c1 = picture[xi + yi * w]
		#c2 = picture[xi1 + yi * w]
		#c3 = picture[xi + yi1 * w]
		#c4 = picture[xi1 + yi1 * w]

		# Harfang Picture:
		c1 = picture.GetPixelRGBA(xi, yi)
		c2 = picture.GetPixelRGBA(xi1, yi)
		c3 = picture.GetPixelRGBA(xi, yi1)
		c4 = picture.GetPixelRGBA(xi1, yi1)

		c12 = c1 * (1 - xf) + c2 * xf
		c34 = c3 * (1 - xf) + c4 * xf
		c = c12 * (1 - yf) + c34 * yf
		return c

	def get_altitude(self, p, height_map: hg.Picture, global_scale, maps_scales_xz, maps_scales_y, maps_offsets_xz, height_amplitude, offset_y):
		s = global_scale
		w, h = height_map.GetWidth(), height_map.GetHeight()
		a = self.get_data_bilinear(height_map, w, h, (p * maps_scales_xz[0] / s + maps_offsets_xz[0])).r
		b = self.get_data_bilinear(height_map, w, h, (p * maps_scales_xz[1] / s + maps_offsets_xz[1])).g
		c = self.get_data_bilinear(height_map, w, h, (p * maps_scales_xz[2] / s + maps_offsets_xz[2])).b
		alt = (pow(a, 5.0) * maps_scales_y[0] + pow(b, 4.0) * maps_scales_y[1] + c * maps_scales_y[2]) * height_amplitude + offset_y
		return alt * global_scale

	def new_grid(self, picture_map: hg.Picture = None):

		triangles_count = self.grid_size.x * self.grid_size.y * 2
		vertices_count = (self.grid_size.x + 1) * (self.grid_size.y + 1)

		vertices, uvs, edges, triangles, normales_triangles = grid_generator.generate_square_grid(self.size, self.grid_size, picture_map, [self.map_1_scale, self.map_2_scale, self.map_3_scale], [self.map_1_offset, self.map_2_offset, self.map_3_offset], self.global_scale, self.terrain_offset)
		return triangles_count, vertices_count, vertices, uvs, edges, triangles, normales_triangles

	def generate_grid(self, picture_map: hg.Picture = None):

		self.triangles_count, self.vertices_count, self.vertices, self.uvs, self.edges, self.triangles, self.normales_triangles = self.new_grid(picture_map)

	def generate_materials(self):

		self.material = hg.CreateMaterial(self.terrain_shaders[self.shader_type], 'uOcclusionRoughnessMetalnessColor', hg.Vec4(1, 0.8, 0.0))
		self.material_water = hg.CreateMaterial(self.water_prg_ref, 'uBaseOpacityColor', hg.Vec4(0, 0, 1, 1), 'uOcclusionRoughnessMetalnessColor', hg.Vec4(1, 0.2, 0.5))
		hg.SetMaterialTexture(self.material_water, "water_noises", self.water_noises_texture_ref, 0)
		hg.SetMaterialFaceCulling(self.material_water, hg.FC_Disabled)
		hg.SetMaterialBlendMode(self.material_water, hg.BM_Alpha)
		self.update_material_values()

	def set_height_texture(self, map_texture):
		if self.map_texture_ref is not None:
			self.pipeline_resources.DestroyTexture(self.map_texture_ref)
		self.map_texture = map_texture
		self.map_texture_ref = self.pipeline_resources.AddTexture("height_map", map_texture)

	def generate_nodes(self):

		self.generate_smooth_model()

		# Create object:

		self.terrain_node = hg.CreateObject(self.scene, hg.TransformationMat4(hg.Vec3(0, 0, 0), hg.Vec3(hg.Deg(0), hg.Deg(0), 0), hg.Vec3(1, 1, 1)), self.model_ref, [self.material])
		self.water_model = hg.CreatePlaneModel(self.vs_decl, self.size.x, self.size.z, 1, 1)
		self.water_model_ref = self.pipeline_resources.AddModel('water', self.water_model)

		self.water_node = hg.CreateObject(self.scene, hg.TransformationMat4(hg.Vec3(0, self.water_altitude, 0), hg.Vec3(hg.Deg(0), hg.Deg(0), 0), hg.Vec3(1, 1, 1)), self.water_model_ref, [self.material_water])

		if self.terrain_node is not None:
			self.material = self.terrain_node.GetObject().GetMaterial(0)

		if self.water_node is not None:
			self.material_water = self.water_node.GetObject().GetMaterial(0)

		self.update_material_values()

	def generate_smooth_model(self):

		model_bld = hg.ModelBuilder()
		model_bld.Clear()
		# Generate model
		vertex = hg.Vertex()
		remap_vertices = {}
		for v_idx in range(len(self.vertices)):
			vertex.pos = self.vertices[v_idx]
			vertex.normal = hg.Vec3(0, 1, 0)
			vertex.uv0 = self.uvs[v_idx]
			nv_idx = model_bld.AddVertex(vertex)
			if nv_idx != v_idx:
				remap_vertices[v_idx] = nv_idx

		for triangle_o in self.triangles:
			triangle = triangle_o["vertices"]
			for ri in range(3):
				if triangle[ri] in remap_vertices:
					triangle[ri] = remap_vertices[triangle[ri]]  # !!! Remove unused vertices at export !!!
			model_bld.AddTriangle(triangle[0], triangle[1], triangle[2])

		model_bld.EndList(0)
		self.model = model_bld.MakeModel(self.vs_decl)
		self.model_ref = self.pipeline_resources.AddModel('terrain', self.model)

	def gui(self):
		step_factor = self.size.x / 10

		if hg.ImGuiBegin("Terrain gride"):

			hg.ImGuiSetWindowCollapsed("Terrain gride", True, hg.ImGuiCond_Once)
			hg.ImGuiSetWindowPos("Terrain gride", hg.Vec2(0, 405), hg.ImGuiCond_Once)
			hg.ImGuiSetWindowSize("Terrain gride", hg.Vec2(460, 650), hg.ImGuiCond_Once)

			f, d = hg.ImGuiRadioButton("Flat", int(self.shader_type), int(Terrain.SHADER_TYPE_FLAT))
			if f:
				self.set_shader_type(d)
			hg.ImGuiSameLine()

			f, d = hg.ImGuiRadioButton("Vertex", int(self.shader_type), int(Terrain.SHADER_TYPE_VERTEX))
			if f:
				self.set_shader_type(d)
			hg.ImGuiSameLine()

			f, d = hg.ImGuiRadioButton("Fragment", int(self.shader_type), int(Terrain.SHADER_TYPE_FRAGMENT))
			if f:
				self.set_shader_type(d)

			f, d = hg.ImGuiInputFloat("Normal sample radius", self.normal_sample_radius, 0.0001, 0.01)
			if f:
				self.set_normal_sample_radius(max(d, 0.0001))

			f, d = hg.ImGuiDragFloat("Global scale", self.global_scale, self.global_scale / 100, 0.0001, 1000)
			if f:
				self.set_global_scale(d)

			f, d = hg.ImGuiDragFloat("Height amplitude", self.size.y, 1)
			if f:
				self.set_height_amplitude(d)

			f, d = hg.ImGuiDragVec2("Grass value", self.grass_value, 0.001)
			if f:
				self.set_grass_value(hg.Vec2(min(1, max(d.x, 0)), min(1, max(d.y, 0))))

			f, d = hg.ImGuiDragFloat("Water altitude", self.water_altitude, 0.001 * step_factor)
			if f:
				self.set_water_altitude(d)

			f, d = hg.ImGuiDragVec3("Waves scale", self.waves_scale, 0.001)
			if f:
				self.set_waves_scale(d)

			f, d = hg.ImGuiDragFloat("Waves speed", self.waves_speed, 0.001)
			if f:
				self.set_waves_speed(d)

			f, d = hg.ImGuiDragVec2("Water transparency fresnel", hg.Vec2(self.water_fresnel_near, self.water_fresnel_far), 0.01)
			if f:
				self.set_water_fresnel(d)

			f, d = hg.ImGuiDragVec2("Mineral fading", self.mineral_fading, 0.01 * step_factor)
			if f:
				self.set_mineral_fading(d)

			f, d = hg.ImGuiDragVec3("Map 1 scale", self.map_1_scale, 0.01)
			if f:
				self.set_map_1_scale(d)
			f, d = hg.ImGuiDragVec2("Map 1 offset", self.map_1_offset, 0.01)
			if f:
				self.set_map_1_offset(d)

			f, d = hg.ImGuiDragVec3("Map 2 scale", self.map_2_scale, 0.01)
			if f:
				self.set_map_2_scale(d)
			f, d = hg.ImGuiDragVec2("Map 2 offset", self.map_2_offset, 0.01)
			if f:
				self.set_map_2_offset(d)

			f, d = hg.ImGuiDragVec3("Map 3 scale", self.map_3_scale, 0.001)
			if f:
				self.set_map_3_scale(d)
			f, d = hg.ImGuiDragVec2("Map 3 offset", self.map_3_offset, 0.01)
			if f:
				self.set_map_3_offset(d)

			f, d = hg.ImGuiDragVec3("Terrain offset", self.terrain_offset, 0.01)
			if f:
				self.set_terrain_offset(d)

			f, c = hg.ImGuiColorEdit("Water color", self.color_water)
			if f:
				self.set_water_color(c)

			f, c = hg.ImGuiColorEdit("Grass color", self.color_grass)
			if f:
				self.set_grass_color(c)

			f, c = hg.ImGuiColorEdit("Mineral 1 color", self.color_mineral1)
			if f:
				self.set_mineral1_color(c)

			f, c = hg.ImGuiColorEdit("Mineral 2 color", self.color_mineral2)
			if f:
				self.set_mineral2_color(c)

			if hg.ImGuiButton("Load terrain picture"):
				self.load_terrain_picture_browser()
			hg.ImGuiSameLine()
			hg.ImGuiText(self.terrain_picture_filename)

			if hg.ImGuiButton("Display wire"):
				Overlays.lines = []
				self.display_wire()
			hg.ImGuiSameLine()
			if hg.ImGuiButton("Display normals"):
				Overlays.lines = []
				self.display_wire()
				self.display_normales_triangles()
			hg.ImGuiSameLine()
			if hg.ImGuiButton("Hide lines"):
				Overlays.lines = []

			if hg.ImGuiButton("Test"):
				self.optim_vertices, self.optim_uvs, self.optim_edges, self.optim_triangles, self.optim_normales_triangles = grid_generator.generate_worley_grid(self.size, self.grid_size)
				for i in range(len(self.optim_vertices)):
					self.optim_vertices[i].x += -15
				self.display_optim_grid()
		hg.ImGuiEnd()

	def set_water_fresnel(self, value: hg.Vec2):
		self.water_fresnel_near = value.x
		self.water_fresnel_far = value.y
		self.update_material_values()

	def set_shader_type(self, shader_id):
		self.shader_type = shader_id
		hg.SetMaterialProgram(self.material, self.terrain_shaders[self.shader_type])
		hg.UpdateMaterialPipelineProgramVariant(self.material, self.pipeline_resources)

	def set_global_scale(self, value):
		value_prec = self.global_scale
		to_prec = self.terrain_offset / value_prec
		to_curr = self.terrain_offset / value
		v = (to_curr - to_prec) * value
		self.terrain_offset.x -= v.x
		self.terrain_offset.z -= v.z
		self.global_scale = value
		self.update_material_values()

	def set_water_color(self, color):
		self.color_water = color
		self.update_material_values()


	def set_grass_color(self, color):
		self.color_grass = color
		self.update_material_values()


	def set_mineral1_color(self, color):
		self.color_mineral1 = color
		self.update_material_values()

	def set_mineral2_color(self, color):
		self.color_mineral2 = color
		self.update_material_values()

	def set_sky_color(self, color):
		self.scene.canvas.color = color
		self.color_sky = color

	def set_water_altitude(self, value):
		self.water_altitude = value
		self.update_material_values()

	def set_waves_scale(self, value):
		self.waves_scale = value
		self.update_material_values()

	def set_waves_speed(self, value):
		self.waves_speed = value
		self.update_material_values()

	def set_mineral_fading(self, value):
		self.mineral_fading = value
		self.update_material_values()

	def set_height_amplitude(self, value):
		self.size.y = value
		self.update_material_values()

	def set_map_1_scale(self, value):
		self.map_1_scale = value
		self.update_material_values()

	def set_map_1_offset(self, value):
		self.map_1_offset = value
		self.update_material_values()

	def set_map_2_scale(self, value):
		self.map_2_scale = value
		self.update_material_values()

	def set_map_2_offset(self, value):
		self.map_2_offset = value
		self.update_material_values()

	def set_map_3_scale(self, value):
		self.map_3_scale = value
		self.update_material_values()

	def set_map_3_offset(self, value):
		self.map_3_offset = value
		self.update_material_values()

	def set_terrain_offset(self, value):
		self.terrain_offset = value
		self.update_material_values()

	def set_normal_sample_radius(self, value):
		self.normal_sample_radius = value
		self.update_material_values()

	def set_grass_value(self, value):
		self.grass_value = value
		self.update_material_values()

	def update_material_values(self):
		if self.map_texture_ref is None:
			if self.map_texture is not None:
				self.map_texture_ref = self.pipeline_resources.AddTexture("height_map", self.map_texture)
		if self.map_texture_ref is not None:
			hg.SetMaterialTexture(self.material, "heightMap", self.map_texture_ref, 0)
		hg.SetMaterialValue(self.material, "grid_size", hg.Vec4(self.grid_size.x, self.grid_size.y, 0, 0))
		hg.SetMaterialValue(self.material, "terrain_scale", hg.Vec4(self.size.x, self.size.y, self.size.z, self.global_scale))
		hg.SetMaterialValue(self.material, "map_1_scale", hg.Vec4(self.map_1_scale.x, self.map_1_scale.y, self.map_1_scale.z, 0))
		hg.SetMaterialValue(self.material, "map_2_scale", hg.Vec4(self.map_2_scale.x, self.map_2_scale.y, self.map_2_scale.z, 0))
		hg.SetMaterialValue(self.material, "map_3_scale", hg.Vec4(self.map_3_scale.x, self.map_3_scale.y, self.map_3_scale.z, 0))
		hg.SetMaterialValue(self.material, "map_1_offset", hg.Vec4(self.map_1_offset.x, self.map_1_offset.y, 0, 0))
		hg.SetMaterialValue(self.material, "map_2_offset", hg.Vec4(self.map_2_offset.x, self.map_2_offset.y, 0, 0))
		hg.SetMaterialValue(self.material, "map_3_offset", hg.Vec4(self.map_3_offset.x, self.map_3_offset.y, 0, 0))
		hg.SetMaterialValue(self.material, "offset_terrain", hg.Vec4(self.terrain_offset.x, self.terrain_offset.y, self.terrain_offset.z, 0))
		hg.SetMaterialValue(self.material, "normal_params", hg.Vec4(self.normal_sample_radius, self.grass_value.x, self.grass_value.y, 0))
		hg.SetMaterialValue(self.material, "water_altitude", hg.Vec4(self.water_altitude, 0, 0, 0))
		hg.SetMaterialValue(self.material, "color_grass", hg.Vec4(self.color_grass.r, self.color_grass.g, self.color_grass.b, 1))
		hg.SetMaterialValue(self.material, "color_water", hg.Vec4(self.color_water.r, self.color_water.g, self.color_water.b, 1))
		hg.SetMaterialValue(self.material, "color_mineral1", hg.Vec4(self.color_mineral1.r, self.color_mineral1.g, self.color_mineral1.b, 1))
		hg.SetMaterialValue(self.material, "color_mineral2", hg.Vec4(self.color_mineral2.r, self.color_mineral2.g, self.color_mineral2.b, 1))
		hg.SetMaterialValue(self.material, "mineral_fading", hg.Vec4(self.mineral_fading.x, self.mineral_fading.y, 0, 0))
		hg.UpdateMaterialPipelineProgramVariant(self.material, self.pipeline_resources)

		hg.SetMaterialValue(self.material_water, "uBaseOpacityColor", hg.Vec4(self.color_water.r, self.color_water.g, self.color_water.b, self.color_water.a))
		hg.SetMaterialValue(self.material_water, "transparency_fresnel", hg.Vec4(self.water_fresnel_near, self.water_fresnel_far, 0, 0))
		hg.SetMaterialValue(self.material_water, "waves_scale", hg.Vec4(self.waves_scale.x, self.waves_scale.y, self.waves_scale.z, self.waves_speed))
		hg.SetMaterialValue(self.material_water, "plane_scale", hg.Vec4(self.size.x, 0, 0, 0))
		hg.UpdateMaterialPipelineProgramVariant(self.material_water, self.pipeline_resources)

		if self.water_node is not None:
			pos = self.water_node.GetTransform().GetPos()
			pos.y = self.water_altitude * self.global_scale
			self.water_node.GetTransform().SetPos(pos)

	def display_normales(self):
		for v_idx in range(len(self.vertices)):
			n = self.normales[v_idx]
			p0 = self.vertices[v_idx]
			Overlays.add_line(p0, p0 + n, hg.Color.Red, hg.Color.Yellow)

	def display_normales_triangles(self):
		if self.flat_terrain_node is not None:
			p = self.flat_terrain_node.GetTransform().GetPos()
			for i in range(len(self.freeze_triangles)):
				triangle = self.freeze_triangles[i]["vertices"]
				p0 = (self.freeze_vertices[triangle[0]] + self.freeze_vertices[triangle[1]] + self.freeze_vertices[triangle[2]]) / 3 + p
				Overlays.add_line(p0, p0 + self.freeze_normales_triangles[i]/10, hg.Color.Red, hg.Color.Yellow)

	def display_wire(self):
		if self.flat_terrain_node is not None:
			p = self.flat_terrain_node.GetTransform().GetPos()
			for edge in self.freeze_edges:
				Overlays.add_line(self.freeze_vertices[edge[0]] + p, self.freeze_vertices[edge[1]] + p, hg.Color.Orange, hg.Color.Orange)
			for v in self.vertices_flat:
				Overlays.display_point(v + p, 0.02, hg.Color.White)
		else:
			p = self.terrain_node.GetTransform().GetPos()
			for edge in self.edges:
				Overlays.add_line(self.vertices[edge[0]] + p, self.vertices[edge[1]] + p, hg.Color.Orange, hg.Color.Orange)

		if len(self.optim_vertices) > 0:
			for edge in self.optim_edges:
				Overlays.add_line(self.optim_vertices[edge[0]], self.optim_vertices[edge[1]], hg.Color.Green, hg.Color.Green)
			for v in self.optim_vertices:
				Overlays.display_point(v, 0.02, hg.Color.White)

	def display_optim_grid(self):
		Overlays.lines = []
		if len(self.optim_vertices) > 0:
			for edge in self.optim_edges:
				Overlays.add_line(self.optim_vertices[edge[0]], self.optim_vertices[edge[1]], edge[2], edge[2])
			for v in self.optim_vertices:
				Overlays.display_point(v, 0.02, hg.Color.White)
