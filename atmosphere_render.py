import harfang as hg
from math import pi
import data_converter as dc

class AtmosphereRenderer:

	def __init__(self, scene, pipeline_resources, resolution):
		self.scene = scene
		self.resolution = resolution
		self.pipeline_resources = pipeline_resources
		self.sun = scene.GetNode("Sun")

		vs_decl = hg.VertexLayout()
		vs_decl.Begin()
		vs_decl.Add(hg.A_Position, 3, hg.AT_Float)
		vs_decl.Add(hg.A_Normal, 3, hg.AT_Uint8, True, True)
		vs_decl.Add(hg.A_TexCoord0, 3, hg.AT_Float)
		vs_decl.End()

		# ===== Background sky quad:
		self.sky_quad_size = hg.Vec2(5, 5)
		self.sky_prg_ref = hg.LoadPipelineProgramRefFromAssets('shaders/sky_render.hps', self.pipeline_resources, hg.GetForwardPipelineInfo())
		c = self.scene.canvas.color
		self.material_sky = hg.CreateMaterial(self.sky_prg_ref, 'sky_color', hg.Vec4(c.r, c.g, c.b, c.a))
		#hg.SetMaterialTexture(self.material_sky, "self_map", self.texture_test_ref, 0)
		hg.SetMaterialDepthTest(self.material_sky, hg.DT_Disabled)

		self.sky_model = hg.CreatePlaneModel(vs_decl, self.sky_quad_size.x, self.sky_quad_size.y, 1, 1)
		self.sky_model_ref = self.pipeline_resources.AddModel('sky', self.sky_model)

		self.sky_node = hg.CreateObject(self.scene, hg.TransformationMat4(hg.Vec3(0, 0, 0), hg.Vec3(hg.Deg(90), hg.Deg(0), 0), hg.Vec3(1, 1, 1)), self.sky_model_ref, [self.material_sky])

		self.material_sky = self.sky_node.GetObject().GetMaterial(0)

		self.horizon_color = hg.Color(1, 1, 1, 1)
		self.horizon_sky_size = 0.1
		self.horizon_sky_falloff_size = 5
		self.horizon_ground_size = 0.1
		self.horizon_ground_falloff_size = 5
		self.ground_color = hg.Color(80/255, 117/255, 159/255, 1)
		self.light_intensity = 1
		self.sky_horizon_smooth = 0.5
		self.ground_horizon_smooth = 0.5

		self.sun_size = 0.5
		self.sun_smooth = 0.25
		self.sun_glow_intensity = 0.8

		self.vr_mat_sky_left = None
		self.vr_mat_sky_right = None

		# ===== Post process rendering
		# setup_gpu_rendering

		"""
		self.uniforms_list = hg.UniformSetValueList()
		self.textures_list = hg.UniformSetTextureList()
		self.quad_size = hg.Vec2(1, self.resolution.y / self.resolution.x)
		self.quad_mdl = hg.CreatePlaneModel(vs_decl, self.quad_size.x, self.quad_size.y, 1, 1)
		self.frameBuffer = hg.CreateFrameBuffer(int(self.resolution.x), int(self.resolution.y), hg.TF_RGBA8, hg.TF_D32F, 4, self.pipeline_resources, "frameBuffer_post_process_atmosphere")
		"""

	def update_sky(self, camera):
		focal_distance = hg.FovToZoomFactor(camera.GetCamera().GetFov())
		mat = hg.TransformationMat4(hg.Vec3(0, 0, focal_distance), hg.Vec3(hg.Deg(-90), hg.Deg(0), 0))
		cam_mat = camera.GetTransform().GetWorld()
		mat_sky = cam_mat * mat
		self.sky_node.GetTransform().SetWorld(mat_sky)
		self.update_material_values()

	def update_sky_vr_left(self, vr_state: hg.OpenVRState, vs_left: hg.ViewState):
		#vr_focal_distance_left = hg.ExtractZoomFactorFromProjectionMatrix(vs_left.proj)
		znear, zfar = hg.ExtractZRangeFromProjectionMatrix(vr_state.left.projection)
		mat_left = hg.TransformationMat4(hg.Vec3(0, 0, znear * 2), hg.Vec3(hg.Deg(-90), hg.Deg(0), 0))
		vr_mat_sky_left = vr_state.head * vr_state.left.offset * mat_left
		self.sky_node.GetTransform().SetWorld(vr_mat_sky_left)

	def update_sky_vr_right(self, vr_state: hg.OpenVRState, vs_right: hg.ViewState):
		#vr_focal_distance_right = hg.ExtractZoomFactorFromProjectionMatrix(vs_right.proj)
		znear, zfar = hg.ExtractZRangeFromProjectionMatrix(vr_state.right.projection)
		mat_right = hg.TransformationMat4(hg.Vec3(0, 0, znear * 2), hg.Vec3(hg.Deg(-90), hg.Deg(0), 0))
		vr_mat_sky_right = vr_state.head * vr_state.right.offset * mat_right
		self.sky_node.GetTransform().SetWorld(vr_mat_sky_right)

	def update_material_values(self):
		hg.SetMaterialValue(self.material_sky, "light_intensity", hg.Vec4(self.light_intensity, 0, 0, 0))
		c = self.scene.canvas.color
		hg.SetMaterialValue(self.material_sky, "sky_color", hg.Vec4(c.r, c.g, c.b, c.a))
		hg.SetMaterialValue(self.material_sky, "horizon_color", hg.Vec4(self.horizon_color.r, self.horizon_color.g, self.horizon_color.b, self.horizon_color.a))
		hg.SetMaterialValue(self.material_sky, "ground_color", hg.Vec4(self.ground_color.r, self.ground_color.g, self.ground_color.b, self.ground_color.a))
		hg.SetMaterialValue(self.material_sky, "horizon_size", hg.Vec4(self.horizon_sky_size / 180 * pi, self.horizon_sky_falloff_size / 180 * pi, self.horizon_ground_size / 180 * pi, self.horizon_ground_falloff_size / 180 * pi))
		hg.SetMaterialValue(self.material_sky, "horizon_smooth", hg.Vec4(self.sky_horizon_smooth , self.ground_horizon_smooth, 0, 0))
		sun_color = self.sun.GetLight().GetDiffuseColor()
		sun_dir = hg.GetZ(self.sun.GetTransform().GetWorld())
		hg.SetMaterialValue(self.material_sky, "sun_color", hg.Vec4(sun_color.r, sun_color.g, sun_color.b, sun_color.a))
		hg.SetMaterialValue(self.material_sky, "sun_dir", hg.Vec4(sun_dir.x, sun_dir.y, sun_dir.z, 0))
		hg.SetMaterialValue(self.material_sky, "sun_params", hg.Vec4(self.sun_size / 180 * pi, self.sun_smooth / 180 * pi, self.sun_glow_intensity, 0))

		hg.UpdateMaterialPipelineProgramVariant(self.material_sky, self.pipeline_resources)

	def get_state(self):
		state = {
			"horizon_color": dc.color_to_list(self.horizon_color),
			"ground_color": dc.color_to_list(self.ground_color),
			"horizon_sky_size": self.horizon_sky_size,
			"horizon_sky_falloff_size": self.horizon_sky_falloff_size,
			"horizon_ground_size": self.horizon_ground_size,
			"horizon_ground_falloff_size": self.horizon_ground_falloff_size,
			"light_intensity": self.light_intensity,
			"sky_horizon_smooth": self.sky_horizon_smooth,
			"ground_horizon_smooth": self.ground_horizon_smooth,
			"sun_size": self.sun_size,
			"sun_smooth": self.sun_smooth,
			"sun_glow_intensity": self.sun_glow_intensity
		}
		return state

	def set_state(self, state):
		if "ground_color" in state:
			self.ground_color = dc.list_to_color(state["ground_color"])
		self.horizon_color = dc.list_to_color(state["horizon_color"])
		if "horizon_sky_size" in state:
			self.horizon_sky_size = state["horizon_sky_size"]
		if "horizon_sky_falloff_size" in state:
			self.horizon_sky_falloff_size = state["horizon_sky_falloff_size"]
		if "horizon_ground_size" in state:
			self.horizon_ground_size = state["horizon_ground_size"]
		if "horizon_ground_falloff_size" in state:
			self.horizon_ground_falloff_size = state["horizon_ground_falloff_size"]
		if "light_intensity" in state:
			self.light_intensity = state["light_intensity"]
		if "sky_horizon_smooth" in state:
			self.sky_horizon_smooth = state["sky_horizon_smooth"]
		if "ground_horizon_smooth" in state:
			self.ground_horizon_smooth = state["ground_horizon_smooth"]
		if "sun_size" in state:
			self.sun_size = state["sun_size"]
		if "sun_smooth" in state:
			self.sun_smooth = state["sun_smooth"]
		if "sun_glow_intensity" in state:
			self.sun_glow_intensity = state["sun_glow_intensity"]

	def gui(self):
		if hg.ImGuiBegin("Atmosphere"):

			hg.ImGuiSetWindowPos("Atmosphere", hg.Vec2(460, 21), hg.ImGuiCond_Once)
			hg.ImGuiSetWindowSize("Atmosphere", hg.Vec2(610, 300), hg.ImGuiCond_Once)

			f, c = hg.ImGuiColorEdit("Horizon color", self.horizon_color)
			if f:
				self.horizon_color = c

			f, d = hg.ImGuiDragFloat("Horizon sky size", self.horizon_sky_size, 0.01)
			if f:
				self.horizon_sky_size = min(90, max(0, d))

			f, d = hg.ImGuiDragFloat("Horizon sky falloff size", self.horizon_sky_falloff_size, 0.01)
			if f:
				self.horizon_sky_falloff_size = min(90, max(0, d))

			f, d = hg.ImGuiDragFloat("Horizon ground size", self.horizon_ground_size, 0.01)
			if f:
				self.horizon_ground_size = min(90, max(0, d))

			f, d = hg.ImGuiDragFloat("Horizon ground falloff size", self.horizon_ground_falloff_size, 0.01)
			if f:
				self.horizon_ground_falloff_size = min(90, max(0, d))

			f, d = hg.ImGuiDragFloat("Horizon sky smooth", self.sky_horizon_smooth, 0.01)
			if f:
				self.sky_horizon_smooth = d

			f, d = hg.ImGuiDragFloat("Horizon ground smooth", self.ground_horizon_smooth, 0.01)
			if f:
				self.ground_horizon_smooth = d

			f, c = hg.ImGuiColorEdit("Ground color", self.ground_color)
			if f:
				self.ground_color = c

			f, d = hg.ImGuiDragFloat("Sky light intensity", self.light_intensity, 0.01)
			if f:
				self.light_intensity = d

			f, d = hg.ImGuiDragFloat("Sun size", self.sun_size, 0.01)
			if f:
				self.sun_size = min(180, max(0, d))

			f, d = hg.ImGuiDragFloat("Sun smooth", self.sun_smooth, 0.01)
			if f:
				self.sun_smooth = min(180, max(0, d))

			f, d = hg.ImGuiDragFloat("Sun glow intensity", self.sun_glow_intensity, 0.01)
			if f:
				self.sun_glow_intensity = min(10, max(0, d))




		hg.ImGuiEnd()
