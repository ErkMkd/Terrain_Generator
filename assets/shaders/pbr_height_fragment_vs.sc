$input a_position, a_normal, a_texcoord0, a_texcoord1, a_tangent, a_bitangent, a_indices, a_weight
$output vWorldPos, vNormal, vTexCoord0, vTexCoord1, vLinearShadowCoord0, vLinearShadowCoord1, vLinearShadowCoord2, vLinearShadowCoord3, vSpotShadowCoord, vProjPos, vPrevProjPos

#include <forward_pipeline.sh>

// Surface attributes
uniform vec4 terrain_scale; //xsize, height_amplitude, zsize, global_scale
uniform vec4 map_1_scale;
uniform vec4 map_2_scale;
uniform vec4 map_3_scale;
uniform vec4 map_1_offset;
uniform vec4 map_2_offset;
uniform vec4 map_3_offset;
uniform vec4 offset_terrain;

SAMPLER2D(heightMap, 0);

mat3 normal_mat(mat4 m) {
#if BGFX_SHADER_LANGUAGE_GLSL
	vec3 u = normalize(vec3(m[0].x, m[1].x, m[2].x));
	vec3 v = normalize(vec3(m[0].y, m[1].y, m[2].y));
	vec3 w = normalize(vec3(m[0].z, m[1].z, m[2].z));
#else
	vec3 u = normalize(m[0].xyz);
	vec3 v = normalize(m[1].xyz);
	vec3 w = normalize(m[2].xyz);
#endif

	return mtxFromRows(u, v, w);
}


float get_altitude(vec2 p, float amplitude)
{
	float s = terrain_scale.w;
	float a=texture2DLod(heightMap, (p * map_1_scale.xz / s + map_1_offset.xy), 0).r;
	float b=texture2DLod(heightMap, (p * map_2_scale.xz / s + map_2_offset.xy), 0).g;
	float c=texture2DLod(heightMap, (p * map_3_scale.xz / s + map_3_offset.xy), 0).b;

	float alt = (pow(a, 5.0) * map_1_scale.y + pow(b, 4.0) * map_2_scale.y + c * map_3_scale.y) * amplitude + offset_terrain.y;
	return alt * terrain_scale.w;
}

void main() {
	// position
	vec2 pos_terrain = a_texcoord0 - vec2(0.5, 0.5) - offset_terrain.xz;
    float alt = get_altitude(pos_terrain, terrain_scale.y);
	vec4 vtx = vec4(a_position , 1.0);
    vtx.y += alt;

	vec4 world_pos = mul(u_model[0], vtx);

#if FORWARD_PIPELINE_AAA_PREPASS
	vec4 prv_world_pos = mul(uPreviousModel[0], vtx);
#endif

	// normal
	vec4 normal = vec4(a_normal * 2. - 1., 0.);

	vNormal = mul(normal_mat(u_model[0]), normal.xyz);

	// shadow data
#if (SLOT0_SHADOWS || SLOT1_SHADOWS)
	float shadowMapShrinkOffset = 0.01;
	vec3 shadowVertexShrinkOffset = vNormal * shadowMapShrinkOffset;
#endif

#if (SLOT0_SHADOWS)
	vLinearShadowCoord0 = mul(uLinearShadowMatrix[0], vec4(world_pos.xyz + shadowVertexShrinkOffset, 1.0));
	vLinearShadowCoord1 = mul(uLinearShadowMatrix[1], vec4(world_pos.xyz + shadowVertexShrinkOffset, 1.0));
	vLinearShadowCoord2 = mul(uLinearShadowMatrix[2], vec4(world_pos.xyz + shadowVertexShrinkOffset, 1.0));
	vLinearShadowCoord3 = mul(uLinearShadowMatrix[3], vec4(world_pos.xyz + shadowVertexShrinkOffset, 1.0));
#endif

#if (SLOT1_SHADOWS)
	vSpotShadowCoord = mul(uSpotShadowMatrix, vec4(world_pos.xyz + shadowVertexShrinkOffset, 1.0));
#endif

	//
	vWorldPos = world_pos.xyz;

//#if (USE_BASE_COLOR_OPACITY_MAP || USE_OCCLUSION_ROUGHNESS_METALNESS_MAP || USE_DIFFUSE_MAP || USE_SPECULAR_MAP|| USE_NORMAL_MAP || USE_SELF_MAP || USE_OPACITY_MAP)
	vTexCoord0 = a_texcoord0;
//#endif

#if (USE_LIGHT_MAP || USE_AMBIENT_MAP)
	vTexCoord1 = a_texcoord1;
#endif

	//
	vec4 proj_pos = mul(uViewProjUnjittered, world_pos);
#if FORWARD_PIPELINE_AAA_PREPASS
	vProjPos = proj_pos;
	vPrevProjPos = mul(uPreviousViewProjection, prv_world_pos);
#endif

	//
	gl_Position = mul(u_viewProj, world_pos);
}
