$input vWorldPos, vNormal, vTexCoord0, vTexCoord1, vTangent, vBinormal

#include <forward_pipeline.sh>

// Surface attributes
uniform vec4 sky_color;
uniform vec4 horizon_color;
uniform vec4 ground_color;
uniform vec4 horizon_size; // x = horizon color thickness, y = horizon falloff thickness
uniform vec4 light_intensity;
uniform vec4 horizon_smooth; // x = sky horizon smooth, y = ground horizon smooth
uniform vec4 sun_dir;
uniform vec4 sun_color;
uniform vec4 sun_params; //size, smooth, glow intensity


SAMPLER2D(self_map, 0);

#define LUM_R 0.2126
#define LUM_G 0.7152
#define LUM_B 0.0722
#define linearstep(edge0, edge1, x) min(max((x - edge0)/(edge1 - edge0), 0.0), 1.0)

float get_sun_intensity(vec3 dir)
{
	float glow_f = sun_params.z;
	float prod_scal = max(dot(sun_dir.xyz, -dir), 0);
	float angle = acos(prod_scal);
	float sun = 1.0 - smoothstep(sun_params.x, sun_params.x + sun_params.y, angle);
	return min(sun +  glow_f * 0.5 * pow(prod_scal,7000.0) + pow(glow_f, 2.0) * 0.4 * pow(prod_scal, 50.0) + pow(glow_f, 3.0) * 0.3 * pow(prod_scal, 2.0), 1.0);
}


vec3 get_atmosphere_color(vec3 dir)
{
	float ray_angle = asin(dir.y);
	vec3 color;
	if (ray_angle > 0.0)
	{
		color = mix(horizon_color.xyz, sky_color.xyz, pow(smoothstep(horizon_size.x, horizon_size.x + horizon_size.y, ray_angle), horizon_smooth.x));
	}
	else
	{
		color = mix(horizon_color.xyz, ground_color.xyz, pow(smoothstep(horizon_size.z, horizon_size.z + horizon_size.w, -ray_angle), horizon_smooth.y));
	}
	return color * light_intensity.x; 
}

vec3 get_sky_color(vec3 dir)
{
	vec3 c_atmosphere = get_atmosphere_color(dir);
	float sun_lum = get_sun_intensity(dir);
	//float sky_lum = c_atmosphere.r * LUM_R + c_atmosphere.g * LUM_G + c_atmosphere.b * LUM_B;
	c_atmosphere = mix(c_atmosphere, sun_color.xyz, sun_lum);
	return c_atmosphere;
}

void main() {
	vec3 dir = normalize(vWorldPos - GetT(u_invView)); // view vector
	vec3 color = get_sky_color(dir);
	gl_FragColor = vec4(color, 1.0); //texture2D(self_map, vTexCoord0) * sky_color;
}
