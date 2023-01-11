# Instantiating scenes

import harfang as hg
from overlays import *
from sprite import *
from terrain import *
from map_generator import *
import data_converter as dc
import json
from Animations import *
from math import pow
import sys
from atmosphere_render import *
import maths_tools
from math import atan2

# --------------- Compile assets:
print("Compiling assets...")
dc.run_command("bin\\assetc.exe assets -quiet -progress")

hg.InputInit()
hg.WindowSystemInit()


class Main:

	flag_exit = False

	flag_display_gui = True
	flag_vr_enable = False # False to disable VR

	assets_folder = "assets_compiled"
	scene = None
	sun = None
	shadow_map_resolution = 2048
	shadow_map_16bit = True
	pipeline = None
	pipeline_aaa = None
	pipeline_aaa_config = None
	resources = None
	win = None

	flag_AAA = False
	flag_fullscreen = False
	flag_vr = False

	flag_lock_view_to_terrain_center = False

	resolution = hg.Vec2(1920, 1080)

	camera = None
	cam_pos = None
	cam_rot = None

	keyboard = None
	mouse = None

	heigth_map = None
	terrain = None

	input_grid_size = hg.iVec2(32, 32)
	input_grid_scale = hg.Vec3(10000, 1000, 10000)
	anim_cam_scale_translation = None
	anim_vr_cam_scale_translation = None
	anim_t = 0

	dt = 0
	dts = 0

	imgui_prg = None
	imgui_img_prg = None
	flag_hovering_gui = False
	flag_popup_opened = False

	output_file_name = ""

	frame = 0

	render_data = None

	vr_left_fb = None
	vr_right_fb = None

	# Setup 2D rendering to display eyes textures
	vr_camera = None
	vr_fps_pos = None
	vr_quad_layout = None

	vr_quad_model = None
	vr_quad_render_state = None

	vr_eye_t_size = None
	vr_eye_t_x = None
	vr_quad_matrix = None

	head_matrix = hg.TranslationMat4(hg.Vec3(0,0,0))

	vr_display_program = None
	vr_quad_uniform_set_value_list = None
	vr_quad_uniform_set_texture_list = None

	vr_speed = 0.1

	gamepad = None

	@classmethod
	def get_monitor_mode(cls, width, height):
		monitors = hg.GetMonitors()
		for i in range(monitors.size()):
			monitor = monitors.at(i)
			f, monitorModes = hg.GetMonitorModes(monitor)
			if f:
				for j in range(monitorModes.size()):
					mode = monitorModes.at(j)
					if mode.rect.ex == width and mode.rect.ey == height:
						print("get_monitor_mode() : Width %d Height %d" % (mode.rect.ex, mode.rect.ey))
						return monitor, j
		return None, 0


	@classmethod
	def init(cls):
		

		if cls.flag_fullscreen:
			monitor, mode_id = cls.get_monitor_mode(int(cls.resolution.x), int(cls.resolution.y))
			if monitor is not None:
				cls.win = hg.NewFullscreenWindow(monitor, mode_id)
				hg.RenderInit(cls.win, hg.RF_VSync | hg.RF_MSAA8X)
			else:
				print ("ERROR - Unable to setup fullscreen mode")
				cls.flag_fullscreen = False
				cls.win = hg.RenderInit('Terrain generator', int(cls.resolution.x), int(cls.resolution.y), hg.RF_None)

		else:
			cls.win = hg.RenderInit('Terrain generator', int(cls.resolution.x), int(cls.resolution.y), hg.RF_None)
		
		hg.AddAssetsFolder(cls.assets_folder)

		cls.pipeline_aaa_config = hg.ForwardPipelineAAAConfig()
		cls.pipeline_aaa = hg.CreateForwardPipelineAAAFromAssets("core", cls.pipeline_aaa_config, hg.BR_Equal, hg.BR_Equal)

		cls.pipeline = hg.CreateForwardPipeline(cls.shadow_map_resolution, cls.shadow_map_16bit)

		cls.resources = hg.PipelineResources()

		cls.scene = hg.Scene()
		hg.LoadSceneFromAssets('main.scn', cls.scene, cls.resources, hg.GetForwardPipelineInfo())

		cls.sun = cls.scene.GetNode("Sun")

		cls.camera = cls.scene.GetCurrentCamera()
		cls.z_near = cls.camera.GetCamera().GetZNear()
		cls.cam_pos = cls.camera.GetTransform().GetPos()
		cls.cam_rot = cls.camera.GetTransform().GetRot()

		cls.keyboard = hg.Keyboard()
		cls.mouse = hg.Mouse()

		cls.imgui_prg = hg.LoadProgramFromAssets('core/shader/imgui')
		cls.imgui_img_prg = hg.LoadProgramFromAssets('core/shader/imgui_image')

		hg.ImGuiInit(10, cls.imgui_prg, cls.imgui_img_prg)

		cls.logo = Sprite(221, 190, "textures/logo.png")

		# OpenVR initialization
		if cls.flag_vr_enable:
			if not hg.OpenVRInit():
				cls.flag_vr_enable = False
			else:
				cls.setup_vr()

		cls.default_color_sky = cls.scene.canvas.color
		cls.default_ambient_color = hg.Color.Black
		cls.default_color_sun = cls.sun.GetLight().GetDiffuseColor()
		cls.default_sun_intensity = cls.sun.GetLight().GetDiffuseIntensity()
		cls.default_color_fog = cls.scene.environment.fog_color
		cls.default_fog_distance = hg.Vec2(cls.scene.environment.fog_near, cls.scene.environment.fog_far)
		rot = cls.sun.GetTransform().GetRot()
		cls.default_sun_orientation = hg.Vec2(rot.x, rot.y)

	@classmethod
	def destroy_terrain(cls):
		cls.terrain.destroy()
		cls.heigth_map.destroy()

	@classmethod
	def setup_vr(cls):
		cls.render_data = hg.SceneForwardPipelineRenderData()  # this object is used by the low-level scene rendering API to share view-independent data with both eyes

		cls.vr_left_fb = hg.OpenVRCreateEyeFrameBuffer(hg.OVRAA_MSAA4x)
		cls.vr_right_fb = hg.OpenVRCreateEyeFrameBuffer(hg.OVRAA_MSAA4x)

		# Setup 2D rendering to display eyes textures
		cls.vr_quad_layout = hg.VertexLayout()
		cls.vr_quad_layout.Begin().Add(hg.A_Position, 3, hg.AT_Float).Add(hg.A_TexCoord0, 3, hg.AT_Float).End()

		cls.vr_quad_model = hg.CreatePlaneModel(cls.vr_quad_layout, 1, 1, 1, 1)
		cls.vr_quad_render_state = hg.ComputeRenderState(hg.BM_Alpha, hg.DT_Disabled, hg.FC_Disabled)

		cls.vr_eye_t_size = cls.resolution.x / 10
		cls.vr_quad_matrix = hg.TransformationMat4(hg.Vec3(0, 0, 0), hg.Vec3(hg.Deg(90), hg.Deg(0), hg.Deg(0)), hg.Vec3(cls.vr_eye_t_size, 1, cls.vr_eye_t_size))

		cls.vr_display_program = hg.LoadProgramFromAssets("shaders/vr_display")

		cls.vr_quad_uniform_set_value_list = hg.UniformSetValueList()
		cls.vr_quad_uniform_set_value_list.clear()
		cls.vr_quad_uniform_set_value_list.push_back(hg.MakeUniformSetValue("color", hg.Vec4(1, 1, 1, 1)))

		cls.vr_quad_uniform_set_texture_list = hg.UniformSetTextureList()

		cls.vr_camera = hg.CreateCamera(cls.scene, hg.TranslationMat4(hg.Vec3(0, 0, 0)), 1, 10000)

		#cls.vr_state = VRState()
		#cls.vr_view_state = VRViewState(cls.vr_camera, cls.vr_state)

		cls.gamepad = hg.Gamepad()

	@classmethod
	def update_window(cls):
		_, cls.resolution.x, cls.resolution.y = hg.RenderResetToWindow(Main.win, int(cls.resolution.x), int(cls.resolution.y), hg.RF_VSync | hg.RF_MSAA4X | hg.RF_MaxAnisotropy)

	@classmethod
	def update_inputs(cls):
		cls.keyboard.Update()
		cls.mouse.Update()
		if cls.flag_vr:
			cls.gamepad.Update()
		cls.dt = hg.TickClock()
		cls.dts = hg.time_to_sec_f(cls.dt)
		if cls.keyboard.Pressed(hg.K_F12):
			cls.flag_display_gui = not cls.flag_display_gui

	@classmethod
	def update_fps(cls):
		step_scale = cls.terrain.size.x / 10
		if not cls.flag_hovering_gui:
			s = cls.terrain.global_scale
			hg.FpsController(cls.keyboard, cls.mouse, cls.cam_pos, cls.cam_rot, 1 * step_scale if cls.keyboard.Down(hg.K_LShift) else 0.1 * step_scale, cls.dt)
			cls.camera.GetTransform().SetPos(cls.cam_pos)
			cls.camera.GetTransform().SetRot(cls.cam_rot)
		if cls.flag_vr:
			#cls.update_fps_vr(cls.vr_camera, cls.vr_view_state.head_matrix, cls.dts)
			cls.update_fps_vr(cls.vr_camera, cls.head_matrix, cls.dts)

		if cls.flag_lock_view_to_terrain_center:
			pos = cls.terrain.terrain_node.GetTransform().GetPos()
			center = hg.Vec3(pos.x, 0, pos.z)
			campos = hg.Vec3(cls.cam_pos.x, 0, cls.cam_pos.z)
			center_dir = hg.Normalize(center - campos)
			cam_mat_rot = hg.RotationMat3(cls.cam_rot)
			camZ = hg.GetZ(cam_mat_rot)
			cam_dir = hg.Normalize(hg.Vec3(camZ.x, 0, camZ.z))
			axis = hg.Cross(cam_dir, center_dir)
			angle = hg.Len(axis)
			axis = hg.Normalize(axis)
			mat = maths_tools.rotate_matrix(cam_mat_rot, axis, angle)
			cls.cam_rot = hg.ToEuler(mat)
			cls.camera.GetTransform().SetRot(cls.cam_rot)

	@classmethod
	def update_fps_vr(cls, camera, head_mtx, dts):

		step_scale = cls.terrain.size.x / 10

		if cls.keyboard.Pressed(hg.K_F11):
			#cls.vr_state.update_initial_head_matrix()
			cls.vr_fps_pos = hg.Vec3(cls.camera.GetTransform().GetPos())
			#cls.vr_camera.GetTransform().SetPos(cls.vr_fps_pos)

		if cls.gamepad.IsConnected():
			vx = cls.gamepad.Axes(hg.GA_RightX)
			vz_front = (cls.gamepad.Axes(5) + 1)/2
			vz_back = (cls.gamepad.Axes(4) + 1)/2
			#if abs(vz) < 0.01: vz = 0
			vz_front = pow(vz_front, 3)
			vz_back = pow(vz_back, 3)
			if abs(vx) < 0.1: vx = 0

			aX = hg.GetX(head_mtx)
			aY = hg.GetY(head_mtx)
			aZ = hg.GetZ(head_mtx)

			speed = step_scale * (vz_front - vz_back)
			"""
			if cls.keyboard.Down(hg.K_LShift):
				speed = 100
			elif cls.keyboard.Down(hg.K_LCtrl):
				speed = 1000
			elif cls.keyboard.Down(hg.K_RCtrl):
				speed = 50000

			


			if cls.keyboard.Down(hg.K_Up) or cls.keyboard.Down(hg.K_W):
				cls.vr_fps_pos += aZ * speed * dts
			if cls.keyboard.Down(hg.K_Down) or cls.keyboard.Down(hg.K_S):
				cls.vr_fps_pos -= aZ * speed * dts
			if cls.keyboard.Down(hg.K_Left) or cls.keyboard.Down(hg.K_A):
				cls.vr_fps_pos += aX * speed * dts
			if cls.keyboard.Down(hg.K_Right) or cls.keyboard.Down(hg.K_D):
				cls.vr_fps_pos += aX * speed * dts
	
			if cls.keyboard.Down(hg.K_R):
				cls.vr_fps_pos += aY * speed * dts
			if cls.keyboard.Down(hg.K_F):
				cls.vr_fps_pos -= aZ * speed * dts
			"""

			cls.vr_fps_pos += aZ * speed * dts
			#cls.vr_fps_pos += aX * speed * vx * dts

			inertia = 0.1
			speed_rot = 45 / 180 * pi
			cam_rot = camera.GetTransform().GetRot()
			cam_rot.y += vx * speed_rot * dts
			camera.GetTransform().SetRot(cam_rot)
			cam_pos0 = camera.GetTransform().GetPos()
			camera.GetTransform().SetPos(cam_pos0 + (cls.vr_fps_pos - cam_pos0) * inertia)

	@classmethod
	def setup_terrain(cls):
		# Generate heightmap
		cls.heigth_map = MapGen(hg.iVec2(512, 512), hg.iVec2(8, 8), 8, 0.7)

		# Generate terrain
		cls.terrain = Terrain(cls.scene, cls.resolution, cls.resources, cls.input_grid_scale.x, cls.input_grid_scale.z, cls.input_grid_scale.y, cls.input_grid_size.x, cls.input_grid_size.y)
		cls.terrain.set_height_texture(cls.heigth_map.get_output_map())
		cls.terrain.generate_nodes()

		# Atmosphere:
		cls.atmosphere = AtmosphereRenderer(cls.scene, cls.resources, cls.resolution)

	@classmethod
	def exit_program(cls):
		cls.destroy_terrain()
		hg.RenderShutdown()
		hg.DestroyWindow(cls.win)

	@classmethod
	def update_hovering_ImGui(cls):
		cls.flag_hovering_gui = False
		if cls.flag_popup_opened:
			cls.flag_hovering_gui = True
		else:
			if hg.ImGuiWantCaptureMouse() and hg.ReadMouse().Button(hg.MB_0):
				cls.flag_hovering_gui = True
			if Main.flag_hovering_gui and not hg.ReadMouse().Button(hg.MB_0):
				cls.flag_hovering_gui = False

	@classmethod
	def gui(cls):
		step_factor = cls.terrain.size.x / 10

		flag_set_grid = False
		flag_exit_popup = False
		cls.flag_popup_opened = False
		if hg.ImGuiBeginMainMenuBar():
			if hg.ImGuiBeginMenu("Project"):
				cls.flag_hovering_gui = True  # True when menu opened
				if hg.ImGuiMenuItem("Load terrain"):
					cls.load_terrain()
				if hg.ImGuiMenuItem("Save terrain"):
					cls.save_terrain(cls.output_file_name)
				if hg.ImGuiMenuItem("Save terrain as"):
					cls.save_terrain()
				hg.ImGuiSeparator()
				hg.ImGuiSpacing()
				if hg.ImGuiMenuItem("Exit"):
					flag_exit_popup = True
				hg.ImGuiEndMenu()
			if hg.ImGuiBeginMenu("Grid"):
				if hg.ImGuiMenuItem("Set grid"):
					flag_set_grid = True
				hg.ImGuiEndMenu()
			hg.ImGuiEndMainMenuBar()

		if flag_exit_popup:
			hg.ImGuiOpenPopup("Confirm exit")
		if flag_set_grid:
			hg.ImGuiOpenPopup("Set grid")

		wn = "Set grid"
		if hg.ImGuiBeginPopup(wn):
			cls.flag_popup_opened = True
			hg.ImGuiSetWindowPos(wn, hg.Vec2(100, 100), hg.ImGuiCond_Once)
			hg.ImGuiSetWindowSize(wn, hg.Vec2(300, 150), hg.ImGuiCond_Always)

			f, d = hg.ImGuiInputIntVec2("Grid divisions", cls.input_grid_size)
			if f:
				cls.input_grid_size = d

			f, d = hg.ImGuiInputFloat("Grid scale", cls.input_grid_scale.x, 1, 10, 2, hg.ImGuiInputTextFlags_EnterReturnsTrue)
			if f:
				s = d / cls.terrain.size.x
				cls.input_grid_scale.z = cls.input_grid_scale.x = d
				cls.input_grid_scale.y = cls.terrain.size.y * s

			if hg.ImGuiButton("OK"):
				s = cls.input_grid_scale.x / cls.terrain.size.x
				cls.terrain.set_grid_size(cls.input_grid_scale, cls.input_grid_size)

				strt = cls.camera.GetTransform().GetPos()
				endp = strt * s
				cls.anim_cam_scale_translation = Animation(0, 1, strt, endp)

				if cls.flag_vr:
					strt_vr = cls.vr_camera.GetTransform().GetPos()
					endp_vr = strt_vr * s
					cls.anim_vr_cam_scale_translation = Animation(0, 1, strt_vr, endp_vr)
				cls.anim_t = 0

				cls.flag_popup_opened = False
				hg.ImGuiCloseCurrentPopup()

			hg.ImGuiSameLine()

			if hg.ImGuiButton("Cancel"):
				cls.flag_popup_opened = False
				hg.ImGuiCloseCurrentPopup()

			hg.ImGuiEndPopup()

		wn = "Confirm exit"
		if hg.ImGuiBeginPopup(wn):
			cls.flag_popup_opened = True
			hg.ImGuiSetWindowPos(wn, hg.Vec2(100, 100), hg.ImGuiCond_Once)
			hg.ImGuiSetWindowSize(wn, hg.Vec2(300, 150), hg.ImGuiCond_Always)
			hg.ImGuiText("Are you sure you want to exit ?")
			if hg.ImGuiButton("YES"):
				cls.flag_exit = True
			hg.ImGuiSameLine()

			if hg.ImGuiButton("NO"):
				hg.ImGuiCloseCurrentPopup()

			hg.ImGuiEndPopup()

		# --- Renderer panel ---

		if hg.ImGuiBegin("Renderer"):
			hg.ImGuiSetWindowCollapsed("Renderer", True, hg.ImGuiCond_Once)
			hg.ImGuiSetWindowPos("Renderer", hg.Vec2(0, 21), hg.ImGuiCond_Once)
			hg.ImGuiSetWindowSize("Renderer", hg.Vec2(460, 380), hg.ImGuiCond_Once)

			f, d = hg.ImGuiCheckbox("AAA", cls.flag_AAA)
			if f:
				cls.flag_AAA = d

			if cls.flag_vr_enable:
				f, d = hg.ImGuiCheckbox("VR", cls.flag_vr)
				if f:
					cls.flag_vr = d
					if d:
						cls.vr_fps_pos = hg.Vec3(cls.camera.GetTransform().GetPos())
						cls.vr_camera.GetTransform().SetPos(hg.Vec3(cls.vr_fps_pos))
						#cls.vr_state.update_initial_head_matrix()
			else:
				hg.ImGuiText("! Unable to start VR !")

			f, d = hg.ImGuiDragFloat("Camera Fov", cls.camera.GetCamera().GetFov() / pi * 180, 0.1)
			if f:
				cls.camera.GetCamera().SetFov(min(max(2, d), 160) / 180 * pi)

			f, cls.flag_lock_view_to_terrain_center = hg.ImGuiCheckbox("Lock view to terrain center", cls.flag_lock_view_to_terrain_center)

			f, c = hg.ImGuiColorEdit("Sun color", cls.sun.GetLight().GetDiffuseColor())
			if f:
				cls.sun.GetLight().SetDiffuseColor(c)

			f, c = hg.ImGuiColorEdit("Sun specular color", cls.sun.GetLight().GetSpecularColor())
			if f:
				cls.sun.GetLight().SetSpecularColor(c)

			f, d = hg.ImGuiDragFloat("Sun Intensity", cls.sun.GetLight().GetDiffuseIntensity(), 0.01)
			if f:
				cls.sun.GetLight().SetDiffuseIntensity(max(0, d))

			f, d = hg.ImGuiDragFloat("Sun specular intensity", cls.sun.GetLight().GetSpecularIntensity(), 0.01)
			if f:
				cls.sun.GetLight().SetSpecularIntensity(max(0, d))

			rot = cls.sun.GetTransform().GetRot()
			f, v = hg.ImGuiDragVec2("Sun orientation", hg.Vec2(rot.x, rot.y) / pi * 180, 0.1)
			if f:
				cls.set_sun_orientation(v / 180 * pi)

			fd = hg.Vec2(cls.scene.environment.fog_near, cls.scene.environment.fog_far)
			f, v = hg.ImGuiDragVec2("Fog distance", fd, 0.01 * step_factor)
			if f:
				cls.scene.environment.fog_near = v.x
				cls.scene.environment.fog_far = v.y

			f, c = hg.ImGuiColorEdit("Fog color", cls.scene.environment.fog_color)
			if f:
				cls.scene.environment.fog_color = c

			f, c = hg.ImGuiColorEdit("Sky color", cls.scene.canvas.color)
			if f:
				cls.scene.canvas.color = c

			f, c = hg.ImGuiColorEdit("Ambient color", cls.scene.environment.ambient)
			if f:
				cls.scene.environment.ambient = c

		hg.ImGuiEnd()

	@classmethod
	def set_sun_orientation(cls, value):
		cls.sun_orientation = value
		cls.sun.GetTransform().SetRot(hg.Vec3(value.x, value.y, 0))

	@classmethod
	def load_terrain(cls, file_name=""):
		if file_name == "":
			f, cls.output_file_name = hg.OpenFileDialog("Select a file", "*.json", "")
		else:
			f = True
			cls.output_file_name = file_name
		if f:
			print("Load project : " + cls.output_file_name)
			project_path = cls.output_file_name.replace(cls.output_file_name.split("/")[-1], "")
			file = open(cls.output_file_name, "r")
			json_script = file.read()
			file.close()
			if json_script != "":
				script_parameters = json.loads(json_script)
				cls.heigth_map.set_state(script_parameters["maps"])
				cls.terrain.set_state(script_parameters["terrain"])
				cls.set_environment_state(script_parameters["environment"])
				cls.terrain.set_height_texture(cls.heigth_map.get_output_map())
				cls.terrain.generate_nodes()
				cls.input_grid_size.x = cls.terrain.grid_size.x
				cls.input_grid_size.y = cls.terrain.grid_size.y
				cls.input_grid_scale.x = cls.terrain.size.x
				cls.input_grid_scale.y = cls.terrain.size.y
				cls.input_grid_scale.z = cls.terrain.size.z
				if "camera" in script_parameters:
					cls.set_camera_state(script_parameters["camera"])
				if "atmosphere" in script_parameters:
					cls.atmosphere.set_state(script_parameters["atmosphere"])


	@classmethod
	def save_terrain(cls, output_filename=""):
		if output_filename == "":
			f, export_path, export_name, output_filename = cls.input_save_file_name("Save terrain", "json")
		else:
			f = True
		if f:
			print("Save terrain : " + output_filename)
			cls.output_file_name = output_filename

			script_parameters = {
				"terrain": cls.terrain.get_state(),
				"maps": cls.heigth_map.get_state(),
				"camera": cls.get_camera_state(),
				"environment": cls.get_environment_state(),
				"atmosphere": cls.atmosphere.get_state()
			}

			json_script = json.dumps(script_parameters, indent=4)

			file = open(cls.output_file_name, "w")
			file.write(json_script)
			file.close()


	@classmethod
	def set_environment_state(cls, state):
		if "sun_orientation" in state:
			cls.set_sun_orientation(dc.list_to_vec2(state["sun_orientation"]))
		else:
			cls.set_sun_orientation(cls.default_sun_orientation)

		if "sun_color" in state:
			c = dc.list_to_color(state["sun_color"])
		else:
			c = cls.default_color_sun
		cls.sun.GetLight().SetDiffuseColor(c)

		if "sun_specular_color" in state:
			c = dc.list_to_color(state["sun_specular_color"])
		else:
			c = cls.default_color_sun
		cls.sun.GetLight().SetSpecularColor(c)

		if "sun_intensity" in state:
			sun_i = state["sun_intensity"]
		else:
			sun_i = cls.default_sun_intensity
		cls.sun.GetLight().SetDiffuseIntensity(sun_i)

		if "sun_specular_intensity" in state:
			sun_i = state["sun_specular_intensity"]
		else:
			sun_i = cls.default_sun_intensity
		cls.sun.GetLight().SetSpecularIntensity(sun_i)

		if "color_sky" in state:
			c = dc.list_to_color(state["color_sky"])
		else:
			c = cls.default_color_sky
		cls.scene.canvas.color = c

		if "fog_distance" in state:
			fd = dc.list_to_vec2(state["fog_distance"])
		else:
			fd = cls.default_fog_distance
		cls.scene.environment.fog_near = fd.x
		cls.scene.environment.fog_far = fd.y

		if "fog_color" in state:
			cls.scene.environment.fog_color = dc.list_to_color(state["fog_color"])
		else:
			cls.scene.environment.fog_color = cls.default_color_fog

		if "ambient_color" in state:
			cls.scene.environment.ambient = dc.list_to_color(state["ambient_color"])
		else:
			cls.scene.environment.ambient = cls.default_ambient_color

	@classmethod
	def get_environment_state(cls):
		rot = cls.sun.GetTransform().GetRot()
		state = {
			"sun_orientation": dc.vec2_to_list(hg.Vec2(rot.x, rot.y)),
			"sun_color": dc.color_to_list(cls.sun.GetLight().GetDiffuseColor()),
			"sun_specular_color": dc.color_to_list(cls.sun.GetLight().GetSpecularColor()),
			"sun_intensity": cls.sun.GetLight().GetDiffuseIntensity(),
			"sun_specular_intensity": cls.sun.GetLight().GetSpecularIntensity(),
			"fog_distance": dc.vec2_to_list(hg.Vec2(cls.scene.environment.fog_near, cls.scene.environment.fog_far)),
			"fog_color": dc.color_to_list(cls.scene.environment.fog_color),
			"color_sky": dc.color_to_list(cls.scene.canvas.color),
			"ambient_color": dc.color_to_list(cls.scene.environment.ambient)
		}
		return state

	@classmethod
	def get_camera_state(cls):
		state = {
			"position": dc.vec3_to_list(cls.camera.GetTransform().GetPos()),
			"rotation": dc.vec3_to_list(cls.camera.GetTransform().GetRot()),
			"fov": cls.camera.GetCamera().GetFov(),
			"zBounds": dc.vec2_to_list(hg.Vec2(cls.camera.GetCamera().GetZNear(), cls.camera.GetCamera().GetZFar()))
		}
		return state

	@classmethod
	def set_camera_state(cls, state):
		cls.cam_pos, cls.cam_rot = dc.list_to_vec3(state["position"]), dc.list_to_vec3(state["rotation"])
		cls.camera.GetTransform().SetPos(cls.cam_pos)
		cls.camera.GetTransform().SetRot(cls.cam_rot)
		cls.camera.GetCamera().SetFov(state["fov"])
		cls.camera.GetCamera().SetZNear(state["zBounds"][0])
		cls.camera.GetCamera().SetZFar(state["zBounds"][1])

	@classmethod
	def input_save_file_name(cls, title, extension):
		f, export_file_name = hg.SaveFileDialog(title, "*." + extension, "")
		if f:
			export_name = export_file_name.split("/")[-1]
			export_path = export_file_name.replace(export_name, "")
			ext = export_file_name.split(".")[-1].lower()
			if ext != extension.lower():
				export_file_name += "." + extension
			else:
				export_name = export_name.replace("." + export_name.split(".")[-1], "")
			print("Export path: " + export_path + " - Export name: " + export_name + " - Export filename: " + export_file_name)
			return True, export_path, export_name, export_file_name
		return False, "", "", ""


	@classmethod
	def update_frame(cls):

		hg.ImGuiBeginFrame(int(cls.resolution.x), int(cls.resolution.y), cls.dt, hg.ReadMouse(), hg.ReadKeyboard())
		cls.update_hovering_ImGui()

		if cls.anim_cam_scale_translation is None:
			if cls.flag_display_gui:
				cls.gui()
				cls.terrain.gui()
				cls.heigth_map.gui(0)
				cls.atmosphere.gui()
		else:
			cls.anim_cam_scale_translation.update(cls.anim_t)
			cls.cam_pos = cls.anim_cam_scale_translation.v
			if cls.flag_vr:
				cls.anim_vr_cam_scale_translation.update(cls.anim_t)
				cls.vr_fps_pos = cls.anim_vr_cam_scale_translation.v
			if cls.anim_cam_scale_translation.flag_end:
				cls.anim_cam_scale_translation = None
				cls.anim_vr_cam_scale_translation = None
			cls.anim_t += cls.dts

		cam = cls.camera.GetCamera()
		s = cls.terrain.size.x
		cam.SetZFar(s)
		cam.SetZNear(s/10000)

		cls.scene.Update(cls.dt)

		vid = 0


		if cls.flag_vr:

			#cls.vr_state.update()
			#cls.vr_view_state.update(cls.vr_camera, cls.vr_state)
			actor_body_mtx = hg.TransformationMat4(cls.vr_camera.GetTransform().GetPos(), cls.vr_camera.GetTransform().GetRot())
			s = cls.terrain.size.x
			vr_state = hg.OpenVRGetState(actor_body_mtx, s/10000, s)
			cls.head_matrix = vr_state.head
			left, right = hg.OpenVRStateToViewState(vr_state)

			passId = hg.SceneForwardPipelinePassViewId()

			# Prepare view-independent render data once
			vid, passId = hg.PrepareSceneForwardPipelineCommonRenderData(vid, cls.scene, cls.render_data, cls.pipeline, cls.resources, passId)
			vr_eye_rect = hg.IntRect(0, 0, vr_state.width, vr_state.height)

			# Prepare the left eye render data then draw to its framebuffer
			cls.atmosphere.update_sky_vr_left(vr_state, left)
			vid, passId = hg.PrepareSceneForwardPipelineViewDependentRenderData(vid, left, cls.scene, cls.render_data, cls.pipeline, cls.resources, passId)
			vid, passId = hg.SubmitSceneToForwardPipeline(vid, cls.scene, vr_eye_rect, left, cls.pipeline, cls.render_data, cls.resources, cls.vr_left_fb.GetHandle())

			# Prepare the right eye render data then draw to its framebuffer
			cls.atmosphere.update_sky_vr_right(vr_state, right)
			vid, passId = hg.PrepareSceneForwardPipelineViewDependentRenderData(vid, right, cls.scene, cls.render_data, cls.pipeline, cls.resources, passId)
			vid, passId = hg.SubmitSceneToForwardPipeline(vid, cls.scene, vr_eye_rect, right, cls.pipeline, cls.render_data, cls.resources, cls.vr_right_fb.GetHandle())

			#cls.scene.Update(0)
		hg.SetViewFrameBuffer(vid, hg.InvalidFrameBufferHandle)

		cls.atmosphere.update_sky(cls.camera)

		if cls.flag_AAA:
			vid, passId = hg.SubmitSceneToPipeline(vid, cls.scene, hg.IntRect(0, 0, int(cls.resolution.x), int(cls.resolution.y)), True, cls.pipeline, cls.resources, cls.pipeline_aaa, cls.pipeline_aaa_config, cls.frame)
		else:
			vid, passId = hg.SubmitSceneToPipeline(vid, cls.scene, hg.IntRect(0, 0, int(cls.resolution.x), int(cls.resolution.y)), True, cls.pipeline, cls.resources)


		# display overlays

		if cls.flag_vr:
			# Display the VR eyes texture to the backbuffer
			hg.SetViewRect(vid, 0, 0, int(cls.resolution.x), int(cls.resolution.y))
			vs = hg.ComputeOrthographicViewState(hg.TranslationMat4(hg.Vec3(0, 0, 0)), cls.resolution.y, 0.1, 100, hg.ComputeAspectRatioX(cls.resolution.x, cls.resolution.y))
			hg.SetViewTransform(vid, vs.view, vs.proj)

			cls.vr_quad_uniform_set_texture_list.clear()
			cls.vr_quad_uniform_set_texture_list.push_back(hg.MakeUniformSetTexture("s_tex", hg.OpenVRGetColorTexture(cls.vr_left_fb), 0))
			hg.SetT(cls.vr_quad_matrix, hg.Vec3(cls.resolution.x / 2 - cls.vr_eye_t_size * 3.2, -cls.resolution.y / 2 + cls.vr_eye_t_size / 1.8, 1))
			hg.DrawModel(vid, cls.vr_quad_model, cls.vr_display_program, cls.vr_quad_uniform_set_value_list, cls.vr_quad_uniform_set_texture_list, cls.vr_quad_matrix, cls.vr_quad_render_state)

			cls.vr_quad_uniform_set_texture_list.clear()
			cls.vr_quad_uniform_set_texture_list.push_back(hg.MakeUniformSetTexture("s_tex", hg.OpenVRGetColorTexture(cls.vr_right_fb), 0))
			hg.SetT(cls.vr_quad_matrix, hg.Vec3(cls.resolution.x / 2 - cls.vr_eye_t_size * 2, -cls.resolution.y / 2 + cls.vr_eye_t_size / 1.8, 1))
			hg.DrawModel(vid, cls.vr_quad_model, cls.vr_display_program, cls.vr_quad_uniform_set_value_list, cls.vr_quad_uniform_set_texture_list, cls.vr_quad_matrix, cls.vr_quad_render_state)
			vid += 1


		hg.SetViewRect(vid, 0, 0, int(cls.resolution.x), int(cls.resolution.y))
		cam = cls.scene.GetCurrentCamera()

		hg.SetViewClear(vid, hg.CF_Depth, 0, 1.0, 0)
		cam_mat = cam.GetTransform().GetWorld()
		view_matrix = hg.InverseFast(cam_mat)
		c = cam.GetCamera()
		projection_matrix = hg.ComputePerspectiveProjectionMatrix(c.GetZNear(), c.GetZFar(), hg.FovToZoomFactor(c.GetFov()), hg.Vec2(cls.resolution.x / cls.resolution.y, 1))
		hg.SetViewTransform(vid, view_matrix, projection_matrix)

		Overlays.display_texts3D(vid, cls.scene.GetCurrentCamera().GetTransform().GetWorld())
		Overlays.draw_lines(vid)

		vid += 1


		# display sprites

		hg.SetViewRect(vid, 0, 0, int(cls.resolution.x), int(cls.resolution.y))
		#Sprite.setup_matrix_sprites2D(vid, cls.resolution)
		#cls.logo.set_position(1920-140, 110)
		#cls.logo.draw(vid)



		hg.ImGuiEndFrame(255)
		cls.frame = hg.Frame()
		if cls.flag_vr:
			hg.OpenVRSubmitFrame(cls.vr_left_fb, cls.vr_right_fb)
		hg.UpdateWindow(cls.win)


#inits

Main.init()
Overlays.init()
Sprite.init_system()

Main.setup_terrain()
Main.load_terrain("terrains_works/terrain_parameters_default.json")

# main loop
while not Main.flag_exit:
	if not Main.flag_fullscreen:
		Main.update_window()
	Main.update_inputs()
	Main.update_fps()
	Main.update_frame()

Main.exit_program()
