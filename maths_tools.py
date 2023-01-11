# Copyright (C) 2018-2021 Eric Kernin, NWNC HARFANG.

import harfang as hg
from math import sin, cos


def smoothstep(edge0, edge1, x):
	t = max(0, min((x - edge0) / (edge1 - edge0), 1.0))
	return t * t * (3.0 - 2.0 * t)


def rotate_vector(point: hg.Vec3, axe: hg.Vec3, angle):
	axe = hg.Normalize(axe)
	dot_prod = point.x * axe.x + point.y * axe.y + point.z * axe.z
	cos_angle = cos(angle)
	sin_angle = sin(angle)

	return hg.Vec3(
		cos_angle * point.x + sin_angle * (axe.y * point.z - axe.z * point.y) + (1 - cos_angle) * dot_prod * axe.x, \
		cos_angle * point.y + sin_angle * (axe.z * point.x - axe.x * point.z) + (1 - cos_angle) * dot_prod * axe.y, \
		cos_angle * point.z + sin_angle * (axe.x * point.y - axe.y * point.x) + (1 - cos_angle) * dot_prod * axe.z)


def rotate_matrix(mat, axe: hg.Vec3, angle):
	axeX = hg.GetX(mat)
	axeY = hg.GetY(mat)
	# axeZ=hg.GetZ(mat)
	axeXr = rotate_vector(axeX, axe, angle)
	axeYr = rotate_vector(axeY, axe, angle)
	axeZr = hg.Cross(axeXr, axeYr)  # rotate_vector(axeZ,axe,angle)
	return hg.Mat3(axeXr, axeYr, axeZr)
