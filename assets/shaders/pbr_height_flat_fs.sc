$input vWorldPos, vNormal, vTexCoord0, vTexCoord1, vLinearShadowCoord0, vLinearShadowCoord1, vLinearShadowCoord2, vLinearShadowCoord3, vSpotShadowCoord, vProjPos, vPrevProjPos

#include <forward_pipeline.sh>

// Surface attributes
uniform vec4 grid_size;
uniform vec4 terrain_scale; //xsize, height_amplitude, zsize, global_scale
uniform vec4 map_1_scale;
uniform vec4 map_2_scale;
uniform vec4 map_3_scale;
uniform vec4 map_1_offset;
uniform vec4 map_2_offset;
uniform vec4 map_3_offset;
uniform vec4 offset_terrain;
uniform vec4 normal_params; //x: sample radius, y:grass value min, z: grass value max
uniform vec4 water_altitude;
uniform vec4 color_grass;
uniform vec4 color_water;
uniform vec4 color_mineral1;
uniform vec4 color_mineral2;
uniform vec4 mineral_fading;

uniform vec4 uOcclusionRoughnessMetalnessColor;

// Texture slots
SAMPLER2D(heightMap, 0);

//

float get_altitude(vec2 p, float amplitude)
{
	float s = terrain_scale.w;
	float a=texture2DLod(heightMap, (p * map_1_scale.xz / s + map_1_offset.xy), 0).r;
	float b=texture2DLod(heightMap, (p * map_2_scale.xz / s + map_2_offset.xy), 0).g;
	float c=texture2DLod(heightMap, (p * map_3_scale.xz / s + map_3_offset.xy), 0).b;

	float alt = (pow(a, 5.0) * map_1_scale.y + pow(b, 4.0) * map_2_scale.y + c * map_3_scale.y) * amplitude + offset_terrain.y;
	return alt * terrain_scale.w;
}


vec3 compute_normal(vec2 pos, float d)
{
    vec2 xd=vec2(d,0);
    vec2 zd=vec2(0,d);
	float height_ratio = terrain_scale.y / terrain_scale.x;
    return normalize(vec3(get_altitude(pos-xd, height_ratio) - get_altitude(pos+xd, height_ratio), 2.0 * d, get_altitude(pos-zd, height_ratio) - get_altitude(pos+zd, height_ratio)));
}


vec3 compute_normal_flat(int primitive_id)
{
	int grid_x = int(grid_size.x);
	int grid_z = int(grid_size.y);

	vec2 quad_size = vec2(1.0, 1.0) / grid_size.xy;
	int quad_id = primitive_id / 2;
	int quad_x = mod(quad_id, grid_x);
	int quad_z = 0;
	if (grid_x != 0)
	{
		quad_z = (quad_id - quad_x) / grid_x;
	}
	vec3 v0 = vec3(float(quad_x) / grid_size.x, 0.0, float(quad_z) / grid_size.y);
	vec3 v1, v2;
	
	if (primitive_id & 0x1 > 0)
	{
		v1 = v0 + vec3(quad_size.x, 0.0, quad_size.y);
		v2 = v0 + vec3(0.0, 0.0, quad_size.y);
	}
	else
	{
		v1 = v0 + vec3(quad_size.x, 0.0, 0.0);
		v2 = v0 + vec3(quad_size.x, 0.0, quad_size.y);
	}
	
	float amplitude = terrain_scale.y / terrain_scale.x;
	v0.y = get_altitude(v0.xz - vec2(0.5, 0.5) - offset_terrain.xz, amplitude);
	v1.y = get_altitude(v1.xz - vec2(0.5, 0.5) - offset_terrain.xz, amplitude);
	v2.y = get_altitude(v2.xz - vec2(0.5, 0.5) - offset_terrain.xz, amplitude);
	vec3 ve0 = v0 - v1;
	vec3 ve1 = v2 - v1;
	vec3 normal_primitive = normalize(cross(ve0, ve1));
	return normal_primitive;
}


vec4 compute_terrain_color(float altitude, vec3 normal)
{
	
	vec2 mf = mineral_fading * terrain_scale.w;
	vec4 color_mineral = mix(color_mineral1, color_mineral2, smoothstep(mf.x, mf.y, altitude));

	vec4 color_terrain = mix(color_mineral, color_grass, smoothstep(normal_params.y, normal_params.z, normal.y));
	
	
	if (altitude < water_altitude.x * terrain_scale.w)
	{
		color_terrain *= color_water;
	}

	return color_terrain;
}


float LightAttenuation(vec3 L, vec3 D, float dist, float attn, float inner_rim, float outer_rim) {
	float k = 1.0;
	if (attn > 0.0)
		k = max(1.0 - dist * attn, 0.0); // distance attenuation

	if (outer_rim > 0.0) {
		float c = dot(L, D);
		k *= clamp(1.0 - (c - inner_rim) / (outer_rim - inner_rim), 0.0, 1.0); // spot attenuation
	}
	return k;
}

float SampleHardShadow(sampler2DShadow map, vec4 coord, float bias) {
	vec3 uv = coord.xyz / coord.w;
	return shadow2D(map, vec3(uv.xy, uv.z - bias));
}

float SampleShadowPCF(sampler2DShadow map, vec4 coord, float inv_pixel_size, float bias, vec4 jitter) {
	float k_pixel_size = inv_pixel_size * coord.w;

	float k = 0.0;

#if FORWARD_PIPELINE_AAA
	#define PCF_SAMPLE_COUNT 2.0 // 3x3

	for (float j = 0.0; j <= PCF_SAMPLE_COUNT; ++j) {
		float v = (j + jitter.y) / PCF_SAMPLE_COUNT * 2.0 - 1.0;
		for (float i = 0.0; i <= PCF_SAMPLE_COUNT; ++i) {
			float u = (i + jitter.x) / PCF_SAMPLE_COUNT * 2.0 - 1.0;
			k += SampleHardShadow(map, coord + vec4(vec2(u, v) * k_pixel_size, 0.0, 0.0), bias);
		}
	}

	k /= (PCF_SAMPLE_COUNT + 1) * (PCF_SAMPLE_COUNT + 1);
#else
	// 2x2
	k += SampleHardShadow(map, coord + vec4(vec2(-0.5, -0.5) * k_pixel_size, 0.0, 0.0), bias);
	k += SampleHardShadow(map, coord + vec4(vec2( 0.5, -0.5) * k_pixel_size, 0.0, 0.0), bias);
	k += SampleHardShadow(map, coord + vec4(vec2(-0.5,  0.5) * k_pixel_size, 0.0, 0.0), bias);
	k += SampleHardShadow(map, coord + vec4(vec2( 0.5,  0.5) * k_pixel_size, 0.0, 0.0), bias);

	k /= 4.0;
#endif

	return k;
}

// Forward PBR GGX
float DistributionGGX(float NdotH, float roughness) {
	float a = roughness * roughness;
	float a2 = a * a;

	float divisor = NdotH * NdotH * (a2 - 1.0) + 1.0;
	return a2 / max(PI * divisor * divisor, 1e-8); 
}

float GeometrySchlickGGX(float NdotW, float k) {
	float div = NdotW * (1.0 - k) + k;
	return NdotW / ((abs(div) > 1e-8) ? div : 1e-8);
}

float GeometrySmith(float NdotV, float NdotL, float roughness) {
	float r = roughness + 1.0;
	float k = (r * r) / 8.0;
	float ggx2 = GeometrySchlickGGX(NdotV, k);
	float ggx1 = GeometrySchlickGGX(NdotL, k);
	return ggx1 * ggx2;
}

vec3 FresnelSchlick(float cosTheta, vec3 F0) {
	return F0 + (1.0 - F0) * pow(max(1.0 - cosTheta, 0.0), 5.0);
}

vec3 FresnelSchlickRoughness(float cosTheta, vec3 F0, float roughness) {
	return F0 + (max(vec3_splat(1.0 - roughness), F0) - F0) * pow(max(1.0 - cosTheta, 0.0), 5.0);
}

vec3 GGX(vec3 V, vec3 N, float NdotV, vec3 L, vec3 albedo, float roughness, float metalness, vec3 F0, vec3 diffuse_color, vec3 specular_color) {
	vec3 H = normalize(V - L);

	float NdotH = max(dot(N, H), 0.0);
	float NdotL = max(-dot(N, L), 0.0);
	float HdotV = max(dot(H, V), 0.0);

	float D = DistributionGGX(NdotH, roughness);
	float G = GeometrySmith(NdotV, NdotL, roughness);
	vec3 F = FresnelSchlick(HdotV, F0);

	vec3 specularBRDF = (F * D * G) / max(4.0 * NdotV * NdotL, 0.001);

	vec3 kD = (vec3_splat(1.0) - F) * (1.0 - metalness); // metallic materials have no diffuse (NOTE: mimics mental ray and 3DX Max ART renderers behavior)
	vec3 diffuseBRDF = kD * albedo;

	return (diffuse_color * diffuseBRDF + specular_color * specularBRDF) * NdotL;
}

//
vec3 DistanceFog(vec3 pos, vec3 color) {
	if (uFogState.y == 0.0)
		return color;

	float k = clamp((pos.z - uFogState.x) * uFogState.y, 0.0, 1.0);
	return mix(color, uFogColor.xyz, k);
}

// Entry point of the forward pipeline default uber shader (Phong and PBR)
void main() {
#if FORWARD_PIPELINE_AAA
	vec4 jitter = texture2D(uNoiseMap, mod(gl_FragCoord.xy, vec2(64, 64)) / vec2(64, 64));
#else
	vec4 jitter = vec4_splat(0.);
#endif

	//
	vec4 occ_rough_metal = uOcclusionRoughnessMetalnessColor;
	
	//
	vec2 pos_terrain = vTexCoord0 - vec2(0.5, 0.5) - offset_terrain.xz;
    //vec3 normal_terrain = compute_normal(pos_terrain, normal_params.x * terrain_scale.w);
    vec3 normal_terrain = compute_normal_flat(gl_PrimitiveID);
	vec4 base_opacity = compute_terrain_color(vWorldPos.y, normal_terrain);
	//
	vec3 view = mul(u_view, vec4(vWorldPos, 1.0)).xyz;
	vec3 P = vWorldPos; // fragment world pos
	vec3 V = normalize(GetT(u_invView) - P); // view vector
	vec3 N = normalize(normal_terrain); // geometry normal

	vec3 R = reflect(-V, N); // view reflection vector around normal

	float NdotV = clamp(dot(N, V), 0.0, 0.99);

	vec3 F0 = vec3(0.04, 0.04, 0.04);
	F0 = mix(F0, base_opacity.xyz, occ_rough_metal.b);

	vec3 color = vec3(0.0, 0.0, 0.0);

	// SLOT 0: linear light
	{
		float k_shadow = 1.0;
#if SLOT0_SHADOWS
		float k_fade_split = 1.0 - jitter.z * 0.3;

		if(view.z < uLinearShadowSlice.x * k_fade_split) {
			k_shadow *= SampleShadowPCF(uLinearShadowMap, vLinearShadowCoord0, uShadowState.y * 0.5, uShadowState.z, jitter);
		} else if(view.z < uLinearShadowSlice.y * k_fade_split) {
			k_shadow *= SampleShadowPCF(uLinearShadowMap, vLinearShadowCoord1, uShadowState.y * 0.5, uShadowState.z, jitter);
		} else if(view.z < uLinearShadowSlice.z * k_fade_split) {
			k_shadow *= SampleShadowPCF(uLinearShadowMap, vLinearShadowCoord2, uShadowState.y * 0.5, uShadowState.z, jitter);
		} else if(view.z < uLinearShadowSlice.w * k_fade_split) {
# if FORWARD_PIPELINE_AAA
			k_shadow *= SampleShadowPCF(uLinearShadowMap, vLinearShadowCoord3, uShadowState.y * 0.5, uShadowState.z, jitter);
# else
			float pcf = SampleShadowPCF(uLinearShadowMap, vLinearShadowCoord3, uShadowState.y * 0.5, uShadowState.z, jitter);
			float ramp_len = (uLinearShadowSlice.w - uLinearShadowSlice.z) * 0.25;
			float ramp_k = clamp((view.z - (uLinearShadowSlice.w - ramp_len)) / max(ramp_len, 1e-8), 0.0, 1.0);
			k_shadow *= pcf * (1.0 - ramp_k) + ramp_k; 
# endif
		}
#endif
		color += GGX(V, N, NdotV, uLightDir[0].xyz, base_opacity.xyz, occ_rough_metal.g, occ_rough_metal.b, F0, uLightDiffuse[0].xyz * k_shadow, uLightSpecular[0].xyz * k_shadow);
	}
	// SLOT 1: point/spot light (with optional shadows)
	{
		vec3 L = P - uLightPos[1].xyz;
		float distance = length(L);
		L /= max(distance, 1e-8);
		float attenuation = LightAttenuation(L, uLightDir[1].xyz, distance, uLightPos[1].w, uLightDir[1].w, uLightDiffuse[1].w);

#if SLOT1_SHADOWS
		attenuation *=SampleShadowPCF(uSpotShadowMap, vSpotShadowCoord, uShadowState.y, uShadowState.w, jitter);
#endif
		color += GGX(V, N, NdotV, L, base_opacity.xyz, occ_rough_metal.g, occ_rough_metal.b, F0, uLightDiffuse[1].xyz * attenuation, uLightSpecular[1].xyz * attenuation);
	}
	// SLOT 2-N: point/spot light (no shadows) [todo]
	{
		for (int i = 2; i < 8; ++i) {
			vec3 L = P - uLightPos[i].xyz;
			float distance = length(L);
			L /= max(distance, 1e-8);
			float attenuation = LightAttenuation(L, uLightDir[i].xyz, distance, uLightPos[i].w, uLightDir[i].w, uLightDiffuse[i].w);

			color += GGX(V, N, NdotV, L, base_opacity.xyz, occ_rough_metal.g, occ_rough_metal.b, F0, uLightDiffuse[i].xyz * attenuation, uLightSpecular[i].xyz * attenuation);
		}
	}

	// IBL
#if FORWARD_PIPELINE_AAA
	vec4 irradiance_occlusion = texture2D(uIrradianceMap, gl_FragCoord.xy / uResolution.xy);

	vec3 irradiance = irradiance_occlusion.xyz;
	vec3 radiance = texture2D(uRadianceMap, gl_FragCoord.xy / uResolution.xy).xyz;
#else
	float MAX_REFLECTION_LOD = 6.;
#if 0 // LOD selection
	vec3 Ndx = normalize(N + ddx(N));
	float dx = length(Ndx.xy / Ndx.z - N.xy / N.z) * 256.0;
	vec3 Ndy = normalize(N + ddy(N));
	float dy = length(Ndy.xy / Ndy.z - N.xy / N.z) * 256.0;

	float dd = max(dx, dy);
	float lod_level = log2(dd);
#endif
	vec3 irradiance = textureCube(uIrradianceMap, N).xyz;
	vec3 radiance = textureCubeLod(uRadianceMap, R, occ_rough_metal.y * MAX_REFLECTION_LOD).xyz;
#endif

	vec3 diffuse = irradiance * base_opacity.xyz;
	vec3 F = FresnelSchlickRoughness(NdotV, F0, occ_rough_metal.y);
	vec2 brdf = texture2D(uBrdfMap, vec2(NdotV, occ_rough_metal.y)).xy;
	vec3 specular = radiance * (F * brdf.x + brdf.y);

	vec3 kS = specular;
	vec3 kD = vec3_splat(1.) - kS;
	kD *= 1. - occ_rough_metal.z;

	color += kD * diffuse;
	color += specular;
	color += uAmbientColor.xyz;
	color *= occ_rough_metal.x;

	color = DistanceFog(view, color);

	float opacity = base_opacity.w;

#if FORWARD_PIPELINE_AAA_PREPASS
	vec3 N_view = mul(u_view, vec4(N, 0)).xyz;
	vec2 velocity = vec2(vProjPos.xy / vProjPos.w - vPrevProjPos.xy / vPrevProjPos.w);
	gl_FragData[0] = vec4(N_view.xyz, vProjPos.z);
	gl_FragData[1] = vec4(velocity.xy, occ_rough_metal.y, 0.);
#else
	// incorrectly apply gamma correction at fragment shader level in the non-AAA pipeline
# if FORWARD_PIPELINE_AAA == 0
	float gamma = 2.2;
	color = pow(color, vec3_splat(1. / gamma));
# endif
	//gl_FragColor = vec4(texture2D(heightMap, vTexCoord0).xyz, opacity);
	gl_FragColor = vec4(color, opacity);
#endif
}
