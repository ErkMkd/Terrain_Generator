
import harfang as hg
import noise
from random import random
import data_converter as dc

class MapGen:

	def __init__(self, map_size: hg.iVec2, main_noise_size: hg.iVec2, octaves_count, persistance):

		self.main_noise_size = main_noise_size
		self.mapsize = map_size
		self.octaves_count = octaves_count
		self.persistance = persistance

		self.noise_seed = 0.0

		# CPU map
		self.height_datas = []
		self.height_pictures = []

		# GPU map
		self.map_render_frameBuffers = []
		self.map_contrast_frameBuffers = []

		self.fb_aa = 4
		self.pack_RGBA_frameBuffer = hg.CreateFrameBuffer(int(self.mapsize.x), int(self.mapsize.y), hg.TF_RGBA8, hg.TF_D32F, self.fb_aa,  "frameBuffer_packRGBA")

		# Textures
		self.map_textures = []
		self.map_textures_contrast = []

		self.map_contrast_params = []

		self.map_RGBA_pack = None
		self.map_RGBA_pack_ref = None

		# Gui
		self.selected_map_id = 0

		self.flag_display_full_map = False

		#setup_gpu_rendering

		vs_decl = hg.VertexLayout()
		vs_decl.Begin()
		vs_decl.Add(hg.A_Position, 3, hg.AT_Float)
		vs_decl.Add(hg.A_Normal, 3, hg.AT_Uint8, True, True)
		vs_decl.Add(hg.A_TexCoord0, 3, hg.AT_Float)
		vs_decl.End()

		self.uniforms_list = hg.UniformSetValueList()
		self.textures_list = hg.UniformSetTextureList()
		self.quad_size = hg.Vec2(1, self.mapsize.y / self.mapsize.x)
		self.quad_mdl = hg.CreatePlaneModel(vs_decl,self.quad_size.x, self.quad_size.y, 1, 1)
		self.map_render_shader = hg.LoadProgramFromAssets("shaders/noise_render.vsb", "shaders/noise_render.fsb")
		self.RGBA_pack_shader = hg.LoadProgramFromAssets("shaders/pack_Greys_to_RGBA.vsb", "shaders/pack_Greys_to_RGBA.fsb")
		self.contrast_shader = hg.LoadProgramFromAssets("shaders/contrast.vsb", "shaders/contrast.fsb")
		self.threshold_shader = hg.LoadProgramFromAssets("shaders/threshold.vsb", "shaders/threshold.fsb")

		self.random_texture, ti = hg.LoadTextureFromAssets("textures/seed_texture.png", 0)

		self.create_terrain_map()

	def set_state(self, state):
		self.remove_all_maps()
		self.mapsize = dc.list_to_iVec2(state["map_size"])
		self.main_noise_size = dc.list_to_iVec2(state["main_noise_size"])
		self.octaves_count = state["octaves_count"]
		self.persistance = state["persistance"]
		self.noise_seed = state["noise_seed"]
		self.pack_RGBA_frameBuffer = hg.CreateFrameBuffer(int(self.mapsize.x), int(self.mapsize.y), hg.TF_RGBA8, hg.TF_D32F, self.fb_aa, "frameBuffer_packRGBA")
		i = 0
		for map_p in state["maps"]:
			self.add_map()
			self.create_map(i)
			self.map_contrast_params[i]["brightness"] = map_p["brightness"]
			self.map_contrast_params[i]["contrast"] = map_p["contrast"]
			self.map_contrast_params[i]["threshold"] = map_p["threshold"]
			i += 1
		self.update_terrain_map()

	def get_state(self):
		maps_params = []
		for i in range(self.get_maps_count()):
			maps_params.append(self.map_contrast_params[i])
		state = {
			"main_noise_size": dc.iVec2_to_list(self.main_noise_size),
			"map_size": dc.iVec2_to_list(self.mapsize),
			"octaves_count": self.octaves_count,
			"persistance": self.persistance,
			"noise_seed": self.noise_seed,
			"maps": maps_params
		}
		return state

	def destroy(self):
		self.remove_all_maps()

	def remove_all_maps(self):
		self.height_datas = []
		self.height_pictures = []
		self.map_textures = []
		self.map_textures_contrast = []
		for fb in self.map_render_frameBuffers:
			hg.DestroyFrameBuffer(fb)
		self.map_render_frameBuffers = []
		for fb in self.map_contrast_frameBuffers:
			hg.DestroyFrameBuffer(fb)
		self.map_contrast_frameBuffers = []
		self.map_contrast_params = []
		hg.DestroyFrameBuffer(self.pack_RGBA_frameBuffer)
		self.map_RGBA_pack = None
		self.pack_RGBA_frameBuffer = None

	def clear_map(self, map_id):

		self.height_datas[map_id] = None
		self.height_pictures[map_id] = None
		self.map_textures[map_id] = None
		self.map_textures_contrast[map_id] = None

	def create_map(self, map_id, brightness=1, contrast=0.5, threshold=0.5):
		fb_aa = 4
		self.map_render_frameBuffers[map_id] = hg.CreateFrameBuffer(int(self.mapsize.x), int(self.mapsize.y), hg.TF_RGBA8, hg.TF_D32F, fb_aa, "frameBuffer_map_render_" + str(map_id))
		self.map_contrast_frameBuffers[map_id] = hg.CreateFrameBuffer(int(self.mapsize.x), int(self.mapsize.y), hg.TF_RGBA8, hg.TF_D32F, fb_aa, "frameBuffer_map_contrast_" + str(map_id))

		self.height_datas[map_id] = None
		self.height_pictures[map_id] = None
		self.map_textures[map_id] = None
		self.map_textures_contrast[map_id] = None
		self.map_contrast_params[map_id] = {"brightness": brightness, "contrast": contrast, "threshold": threshold}

	def add_map(self, brightness=1, contrast=0.5, threshold=0.5):
		self.map_render_frameBuffers.append(None)
		self.map_contrast_frameBuffers.append(None)
		self.height_datas.append(None)
		self.height_pictures.append(None)
		self.map_textures.append(None)
		self.map_textures_contrast.append(None)
		self.map_contrast_params.append(None)
		self.create_map(len(self.map_render_frameBuffers)-1, brightness, contrast, threshold)

	def get_maps_count(self):
		return len(self.map_render_frameBuffers)

	def update_map(self, vid, map_id):
		self.render_map_GPU(vid, map_id)
		self.pack_to_RGBA_GPU(vid)

	def create_terrain_map(self):
		self.remove_all_maps()
		self.pack_RGBA_frameBuffer = hg.CreateFrameBuffer(int(self.mapsize.x), int(self.mapsize.y), hg.TF_RGBA8, hg.TF_D32F, self.fb_aa, "frameBuffer_packRGBA")
		n = 3
		default_maps_params = [
			{"brightness": 2.273, "contrast": 3.33, "threshold": 0.485},
			{"brightness": 2.424, "contrast": 1.97, "threshold": 0.652},
			{"brightness": 1.818, "contrast": 0.909, "threshold": 0.5}
		]
		for i in range(n):
			mp = default_maps_params[i]
			self.add_map(mp["brightness"], mp["contrast"], mp["threshold"])
		self.update_terrain_map()

	def update_terrain_map(self):
		for i in range(self.get_maps_count()):
			self.render_map_GPU(0, i)
		self.pack_to_RGBA_GPU(0)

	def render_map_GPU(self, vid, map_id):
		self.clear_map(map_id)

		self.uniforms_list.clear()
		self.textures_list.clear()
		self.textures_list.push_back(hg.MakeUniformSetTexture("random_tex", self.random_texture, 0))
		self.uniforms_list.push_back(hg.MakeUniformSetValue("color", hg.Vec4(1, 1, 1, 1)))
		self.uniforms_list.push_back(hg.MakeUniformSetValue("noise_seed", hg.Vec4(self.noise_seed + 1000 * map_id, self.noise_seed + 1000 * map_id, 0, 0)))
		self.uniforms_list.push_back(hg.MakeUniformSetValue("noise_params", hg.Vec4(self.octaves_count, self.persistance, self.main_noise_size.x, self.main_noise_size.y)))

		hg.SetViewFrameBuffer(vid, self.map_render_frameBuffers[map_id].handle)
		hg.SetViewRect(vid, 0, 0, int(self.mapsize.x), int(self.mapsize.y))
		hg.SetViewClear(vid, hg.CF_Depth|hg.CF_Color, 0, 1.0, 0)
		vs = hg.ComputeOrthographicViewState(hg.TranslationMat4(hg.Vec3(0, 0, 0)), 1, 0.1, 100, hg.Vec2(1, self.mapsize.y / self.mapsize.x))
		hg.SetViewTransform(vid, vs.view, vs.proj)
		matrix = hg.TransformationMat4(hg.Vec3(0, 0, 2), hg.Vec3(hg.Deg(90), 0, 0))
		render_state = hg.ComputeRenderState(hg.BM_Opaque, hg.DT_Disabled, hg.FC_Disabled)
		hg.DrawModel(vid, self.quad_mdl, self.map_render_shader, self.uniforms_list, self.textures_list, matrix, render_state)
		hg.Frame()

		self.map_textures[map_id] = hg.GetColorTexture(self.map_render_frameBuffers[map_id])

		self.render_contrast_GPU(vid, map_id)

	def render_contrast_GPU(self, vid, map_id):

		self.uniforms_list.clear()
		self.textures_list.clear()
		params = self.map_contrast_params[map_id]
		self.uniforms_list.push_back(hg.MakeUniformSetValue("params", hg.Vec4(params["brightness"], params["contrast"], params["threshold"], 0)))
		self.textures_list.push_back(hg.MakeUniformSetTexture("u_tex", self.map_textures[map_id], 0))

		hg.SetViewFrameBuffer(vid, self.map_contrast_frameBuffers[map_id].handle)
		hg.SetViewRect(vid, 0, 0, int(self.mapsize.x), int(self.mapsize.y))
		hg.SetViewClear(vid, hg.CF_Depth|hg.CF_Color, 0, 1.0, 0)
		vs = hg.ComputeOrthographicViewState(hg.TranslationMat4(hg.Vec3(0, 0, 0)), 1, 0.1, 100, hg.Vec2(1, self.mapsize.y / self.mapsize.x))
		hg.SetViewTransform(vid, vs.view, vs.proj)
		matrix = hg.TransformationMat4(hg.Vec3(0, 0, 2), hg.Vec3(hg.Deg(90), 0, 0))
		render_state = hg.ComputeRenderState(hg.BM_Opaque, hg.DT_Disabled, hg.FC_Disabled)
		hg.DrawModel(vid, self.quad_mdl, self.contrast_shader, self.uniforms_list, self.textures_list, matrix, render_state)
		hg.Frame()

		self.map_textures_contrast[map_id] = hg.GetColorTexture(self.map_contrast_frameBuffers[map_id])

	def pack_to_RGBA_GPU(self, vid):

		self.uniforms_list.clear()
		self.textures_list.clear()

		for i in range(self.get_maps_count()):
			self.textures_list.push_back(hg.MakeUniformSetTexture("s_tex", self.map_textures_contrast[i], i))

		hg.SetViewFrameBuffer(vid, self.pack_RGBA_frameBuffer.handle)
		hg.SetViewRect(vid, 0, 0, int(self.mapsize.x), int(self.mapsize.y))
		hg.SetViewClear(vid, hg.CF_Depth|hg.CF_Color, 0, 1.0, 0)
		vs = hg.ComputeOrthographicViewState(hg.TranslationMat4(hg.Vec3(0, 0, 0)), 1, 0.1, 100, hg.Vec2(1, self.mapsize.y / self.mapsize.x))
		hg.SetViewTransform(vid, vs.view, vs.proj)
		matrix = hg.TransformationMat4(hg.Vec3(0, 0, 2), hg.Vec3(hg.Deg(90), 0, 0))
		render_state = hg.ComputeRenderState(hg.BM_Opaque, hg.DT_Disabled, hg.FC_Disabled)
		hg.DrawModel(vid, self.quad_mdl, self.RGBA_pack_shader, self.uniforms_list, self.textures_list, matrix, render_state)
		hg.Frame()

		if self.map_RGBA_pack is None:
			self.map_RGBA_pack = hg.GetColorTexture(self.pack_RGBA_frameBuffer)

	def get_output_map(self):
		return self.map_RGBA_pack

	def gui(self, vid):
		if hg.ImGuiBegin("Map generator"):

			hg.ImGuiSetWindowCollapsed("Map generator", True, hg.ImGuiCond_Once)
			hg.ImGuiSetWindowPos("Map generator", hg.Vec2(1920-470, 20), hg.ImGuiCond_Once)
			hg.ImGuiSetWindowSize("Map generator", hg.Vec2(470, 950), hg.ImGuiCond_Once)


			f, d = hg.ImGuiInputFloat("Seed", self.noise_seed, 1, 0.1)
			if f:
				self.noise_seed = d
				self.update_terrain_map()

			images_size = hg.Vec2(200, 200)

			"""
			maps_list = hg.StringList()

			for i in range(self.get_maps_count()):
				nm = "Map.%d" % i
				maps_list.push_back(nm)
			f, d = hg.ImGuiListBox("Maps", self.selected_map_id, maps_list, 5)
			if f:
				self.selected_map_id = d
			"""

			for i in range(self.get_maps_count()):
				hg.ImGuiColumns(2, "Img_%d" % i)
				hg.ImGuiImage(self.map_textures_contrast[i], images_size)
				hg.ImGuiNextColumn()
				params = self.map_contrast_params[i]
				f, d = hg.ImGuiDragFloat("Brightness##%d" % i, params["brightness"], 0.001)
				if f:
					params["brightness"] = min(10, max(-10, d))
					self.update_map(vid, i)
				f, d = hg.ImGuiDragFloat("Contrast##%d" % i, params["contrast"], 0.001)
				if f:
					params["contrast"] = min(10, max(-10, d))
					self.update_map(vid, i)
				f, d = hg.ImGuiDragFloat("Threshold##%d" % i, params["threshold"], 0.001)
				if f:
					params["threshold"] = min(1, max(0, d))
					self.update_map(vid, i)

				hg.ImGuiColumns()

			if self.map_RGBA_pack is not None:
				hg.ImGuiImage(self.map_RGBA_pack, images_size)
				f, d = hg.ImGuiCheckbox("Display full map", self.flag_display_full_map)
				if f:
					self.flag_display_full_map = d

		hg.ImGuiEnd()

		if self.flag_display_full_map:
			if hg.ImGuiBegin("Terrain map"):
				hg.ImGuiSetWindowPos("Terrain map", hg.Vec2(600, 200), hg.ImGuiCond_Once)
				im_size = hg.Vec2(self.mapsize.x, self.mapsize.y)
				hg.ImGuiSetWindowSize("Terrain map", im_size + hg.Vec2(40, 40), hg.ImGuiCond_Once)
				hg.ImGuiImage(self.map_RGBA_pack, im_size)
			hg.ImGuiEnd()

# ------------------- Obsolete, only for documentation

	def render_map_CPU(self, map_id):
		self.clear_map(map_id)
		self.height_datas[map_id] = noise.generate_Perlin_2D(self.main_noise_size.x, self.main_noise_size.y, self.mapsize.x, self.mapsize.y, self.octaves_count, self.persistance)
		self.height_pictures[map_id] = hg.Picture(self.mapsize.x, self.mapsize.y, hg.PF_RGBA32)
		for y in range(self.mapsize.y):
			for x in range(self.mapsize.x):
				i = x + y * self.mapsize.x
				c = self.height_datas[map_id][i]
				self.height_pictures[map_id].SetPixelRGBA(x, y, hg.Color(c, c, c, 1))
		self.textures[map_id] = hg.CreateTextureFromPicture(self.height_pictures[map_id], "height_bm_"+str(map_id), 0, hg.TF_RGBA8)
