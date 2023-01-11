
import harfang as hg
from random import uniform
import math


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
	# c1 = picture[xi + yi * w]
	# c2 = picture[xi1 + yi * w]
	# c3 = picture[xi + yi1 * w]
	# c4 = picture[xi1 + yi1 * w]

	# Harfang Picture:
	c1 = picture.GetPixelRGBA(xi, yi)
	c2 = picture.GetPixelRGBA(xi1, yi)
	c3 = picture.GetPixelRGBA(xi, yi1)
	c4 = picture.GetPixelRGBA(xi1, yi1)

	c12 = c1 * (1 - xf) + c2 * xf
	c34 = c3 * (1 - xf) + c4 * xf
	c = c12 * (1 - yf) + c34 * yf
	return c


def get_altitude(p, height_map: hg.Picture, global_scale, maps_scales_xz, maps_scales_y, maps_offsets_xz, height_amplitude, offset_y):
	s = global_scale
	w, h = height_map.GetWidth(), height_map.GetHeight()
	a = get_data_bilinear(height_map, w, h, (p * maps_scales_xz[0] / s + maps_offsets_xz[0])).r
	b = get_data_bilinear(height_map, w, h, (p * maps_scales_xz[1] / s + maps_offsets_xz[1])).g
	c = get_data_bilinear(height_map, w, h, (p * maps_scales_xz[2] / s + maps_offsets_xz[2])).b
	alt = (pow(a, 5.0) * maps_scales_y[0] + pow(b, 4.0) * maps_scales_y[1] + c * maps_scales_y[2]) * height_amplitude + offset_y
	return alt * global_scale


def generate_worley_grid(size: hg.Vec3, grid_size: hg.iVec2, picture_map: hg.Picture = None, maps_scales=None, maps_offsets=None, global_scale=1, terrain_offset: hg.Vec3 = None):

	vertices = []
	uvs = []
	edges = []
	triangles = []
	normales_triangles = []

	if picture_map is not None:
		maps_scales_xz = [hg.Vec2(maps_scales[0].x, maps_scales[0].z), hg.Vec2(maps_scales[1].x, maps_scales[1].z), hg.Vec2(maps_scales[2].x, maps_scales[2].z)]
		maps_scales_y = [maps_scales[0].y, maps_scales[1].y, maps_scales[2].y]
		p = hg.Vec2()

	cell_size = hg.Vec2(size.x / grid_size.x, size.z / grid_size.y) * 0.5

	for iz in range(grid_size.y + 1):
		z = -size.z / 2 + (size.z / grid_size.y) * iz
		for ix in range(grid_size.x + 1):
			x = -size.x / 2 + (size.x / grid_size.x) * ix
			x_voronoi = x + uniform(-cell_size.x, cell_size.x)
			z_voronoi = z + uniform(-cell_size.y, cell_size.y)
			if picture_map is None:
				y = 0
			else:
				p.x = ix / (grid_size.x + 1)
				p.y = iz / (grid_size.y + 1)
				pos_terrain = p - hg.Vec2(0.5 + terrain_offset.x, 0.5 + terrain_offset.z)
				y = get_altitude(pos_terrain, picture_map, global_scale, maps_scales_xz, maps_scales_y, maps_offsets, size.y, terrain_offset.y)
			vertices.append(hg.Vec3(x_voronoi, y, z_voronoi))
			uvs.append(hg.Vec2((x_voronoi + size.x / 2) / size.x, (z_voronoi + size.z / 2) / size.z))

	# Triangle, edges, flat normales
	for iz in range(grid_size.y):
		for ix in range(grid_size.x):
			i0 = ix + iz * (grid_size.x + 1)
			i1 = i0 + 1
			i2 = i1 + grid_size.x + 1
			i3 = i0 + grid_size.x + 1

			edges.append([i0, i1, hg.Color.Green])
			edges.append([i0, i3, hg.Color.Green])

			if ix == grid_size.x - 1:
				edges.append([i1, i2, hg.Color.Green])
			if iz == grid_size.y - 1:
				edges.append([i2, i3, hg.Color.Green])

			#triangulate irregulare square:
			quad = [vertices[i0], vertices[i1], vertices[i2], vertices[i3]]
			i_concave = 0
			zmin = math.inf
			for i in range(4):
				v0 = quad[(i+1) % 4] - quad[i]
				v1 = quad[(i-1) % 4] - quad[i]
				z = v0.x * v1.z - v0.z * v1.x
				if z < zmin:
					i_concave = i
					zmin = z
			ix = [i0, i1, i2, i3]

			ic0 = ix[i_concave]
			ic1 = ix[(i_concave + 1) % 4]
			ic2 = ix[(i_concave + 2) % 4]
			ic3 = ix[(i_concave + 3) % 4]

			edges.append([ic0, ic2, hg.Color.Red])

			triangles.append({"vertices": [ic0, ic1, ic2], "edges": []})
			triangles.append({"vertices": [ic0, ic2, ic3], "edges": []})

			# Normales flat
			v0 = vertices[ic0] - vertices[ic1]
			v1 = vertices[ic2] - vertices[ic1]
			n0 = hg.Normalize(hg.Cross(v0, v1))

			v2 = vertices[ic2] - vertices[ic3]
			v3 = vertices[ic0] - vertices[ic3]
			n1 = hg.Normalize(hg.Cross(v2, v3))

			normales_triangles.append(n0)
			normales_triangles.append(n1)

	return vertices, uvs, edges, triangles, normales_triangles


def compute_center_circumscribed_circle_of_triangle(vertices, triangle):
	pass


def generate_voronoi_grid(size: hg.Vec3, grid_size: hg.iVec2, picture_map: hg.Picture = None, maps_scales=None, maps_offsets=None, global_scale=1, terrain_offset: hg.Vec3 = None):

	vertices = []
	uvs = []
	edges = []
	triangles = []
	normales_triangles = []

	if picture_map is not None:
		maps_scales_xz = [hg.Vec2(maps_scales[0].x, maps_scales[0].z), hg.Vec2(maps_scales[1].x, maps_scales[1].z), hg.Vec2(maps_scales[2].x, maps_scales[2].z)]
		maps_scales_y = [maps_scales[0].y, maps_scales[1].y, maps_scales[2].y]
		p = hg.Vec2()

	cell_size = hg.Vec2(size.x / grid_size.x, size.z / grid_size.y) * 0.5

	main_points = []

	for iz in range(grid_size.y + 1):
		z = -size.z / 2 + (size.z / grid_size.y) * iz
		for ix in range(grid_size.x + 1):
			x = -size.x / 2 + (size.x / grid_size.x) * ix
			x_main = x + uniform(-cell_size.x, cell_size.x)
			z_main = z + uniform(-cell_size.y, cell_size.y)
			main_points.append([x_main, z_main])



	# Triangle, edges, flat normales
	for iz in range(grid_size.y):
		for ix in range(grid_size.x):
			i0 = ix + iz * (grid_size.x + 1)
			i1 = i0 + 1
			i2 = i1 + grid_size.x + 1
			i3 = i0 + grid_size.x + 1

			edges.append([i0, i1, hg.Color.Green])
			edges.append([i0, i3, hg.Color.Green])

			if ix == grid_size.x - 1:
				edges.append([i1, i2, hg.Color.Green])
			if iz == grid_size.y - 1:
				edges.append([i2, i3, hg.Color.Green])

			#triangulate irregulare square:
			quad = [vertices[i0], vertices[i1], vertices[i2], vertices[i3]]
			i_concave = 0
			zmin = math.inf
			for i in range(4):
				v0 = quad[(i+1) % 4] - quad[i]
				v1 = quad[(i-1) % 4] - quad[i]
				z = v0.x * v1.z - v0.z * v1.x
				if z < zmin:
					i_concave = i
					zmin = z
			ix = [i0, i1, i2, i3]

			ic0 = ix[i_concave]
			ic1 = ix[(i_concave + 1) % 4]
			ic2 = ix[(i_concave + 2) % 4]
			ic3 = ix[(i_concave + 3) % 4]

			edges.append([ic0, ic2, hg.Color.Red])

			triangles.append({"vertices": [ic0, ic1, ic2], "edges": []})
			triangles.append({"vertices": [ic0, ic2, ic3], "edges": []})

			# Normales flat
			v0 = vertices[ic0] - vertices[ic1]
			v1 = vertices[ic2] - vertices[ic1]
			n0 = hg.Normalize(hg.Cross(v0, v1))

			v2 = vertices[ic2] - vertices[ic3]
			v3 = vertices[ic0] - vertices[ic3]
			n1 = hg.Normalize(hg.Cross(v2, v3))

			normales_triangles.append(n0)
			normales_triangles.append(n1)

	return vertices, uvs, edges, triangles, normales_triangles


def generate_square_grid(size: hg.Vec3, grid_size: hg.iVec2, picture_map: hg.Picture = None, maps_scales=None, maps_offsets=None, global_scale=1, terrain_offset: hg.Vec3 = None):

	vertices = []
	uvs = []

	if picture_map is not None:
		maps_scales_xz = [hg.Vec2(maps_scales[0].x, maps_scales[0].z), hg.Vec2(maps_scales[1].x, maps_scales[1].z), hg.Vec2(maps_scales[2].x, maps_scales[2].z)]
		maps_scales_y = [maps_scales[0].y, maps_scales[1].y, maps_scales[2].y]
		p = hg.Vec2()
	# Vertices
	for iz in range(grid_size.y + 1):
		z = -size.z / 2 + (size.z / grid_size.y) * iz
		for ix in range(grid_size.x + 1):
			x = -size.x / 2 + (size.x / grid_size.x) * ix
			if picture_map is None:
				y = 0
			else:
				p.x = ix / (grid_size.x + 1)
				p.y = iz / (grid_size.y + 1)
				pos_terrain = p - hg.Vec2(0.5 + terrain_offset.x, 0.5 + terrain_offset.z)
				y = get_altitude(pos_terrain, picture_map, global_scale, maps_scales_xz, maps_scales_y, maps_offsets, size.y, terrain_offset.y)
			vertices.append(hg.Vec3(x, y, z))
			uvs.append(hg.Vec2((x + size.x / 2) / size.x, (z + size.z / 2) / size.z))

	edges, triangles, normales_triangles = link_vertices(grid_size, vertices)

	return vertices, uvs, edges, triangles, normales_triangles

def link_vertices(grid_size, vertices):
	edges = []
	triangles = []
	normales_triangles = []

	# Triangle, edges, flat normales
	for iz in range(grid_size.y):
		for ix in range(grid_size.x):
			i0 = ix + iz * (grid_size.x + 1)
			i1 = i0 + 1
			i2 = i1 + grid_size.x + 1
			i3 = i0 + grid_size.x + 1

			edge_idx0 = len(edges)
			edge_idx1 = edge_idx0 + 5
			edge_idx2 = edge_idx0 + 1
			if iz == grid_size.y - 2:
				edge_idx3 = edge_idx0 + (grid_size.x * 3) + 1 + ix
			else:
				edge_idx3 = edge_idx0 + (grid_size.x * 3) + 1
			edge_idx4 = edge_idx0 + 2

			edges.append([i0, i1])
			edges.append([i0, i2])
			edges.append([i0, i3])
			ebound = 0
			if ix == grid_size.x - 1:
				edge_idx1 = edge_idx0 + 3
				edges.append([i1, i2])
				ebound = 1
			if iz == grid_size.y - 1:
				edges.append([i2, i3])
				edge_idx1 = edge_idx0 + 6 - ebound * 3
				edge_idx3 = edge_idx0 + 3 + ebound

			triangles.append({"vertices": [i0, i1, i2], "edges": [edge_idx0, edge_idx1, edge_idx2]})
			triangles.append({"vertices": [i0, i2, i3], "edges": [edge_idx2, edge_idx3, edge_idx4]})

			# Normales flat
			v0 = vertices[i0] - vertices[i1]
			v1 = vertices[i2] - vertices[i1]
			n0 = hg.Normalize(hg.Cross(v0, v1))

			v2 = vertices[i2] - vertices[i3]
			v3 = vertices[i0] - vertices[i3]
			n1 = hg.Normalize(hg.Cross(v2, v3))

			normales_triangles.append(n0)
			normales_triangles.append(n1)

	return edges, triangles, normales_triangles
