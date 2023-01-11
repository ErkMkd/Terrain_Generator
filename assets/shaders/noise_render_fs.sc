$input v_texcoord0

#include <bgfx_shader.sh>

uniform vec4 color;
uniform vec4 noise_seed; //seedx, seedy
uniform vec4 noise_params; //num_octaves, persistance, fondamentale_xsize, fondamental_ysize

SAMPLER2D(random_tex, 0);


float random_noise_texture (vec2 st, float seed) {
	vec3 seed_c = texture2DLod(random_tex, st/256.0 * seed, 0).rgb;
	return fract(seed_c.r + seed_c.g + seed_c.b);
    //return fract(sin(dot(st.xy, vec2(12.98,78.23)))* 7.51 * seed);
}

float random_unstable (vec2 st, float seed) {
    return fract(sin(dot(st.xy, vec2(12.98,78.23)))* 7.51 * seed);
}

float linear_interpolation(float a, float b, float t)
{
	return a * (1.0 - t) + b * t;
}

float cos_interpolation(float a, float b, float t, float strongness)
{
	return linear_interpolation(a, b, (-cos(3.141 * pow(t, strongness)) + 1.0) / 2.0);
}


float noise2D_Perlin(vec2 st, vec2 main_octave_size, float octave_id, vec2 seed) 
{
	st *= octave_id;
	vec2 seed_of7 = seed * octave_id;
    vec2 i = floor(st);
    vec2 f = fract(st);
	vec2 octave_size = main_octave_size * octave_id;
	vec2 ic = vec2(mod(i.x + 1.0, octave_size.x), mod(i.y + 1.0, octave_size.y)) ;
	i += seed_of7;
	ic += seed_of7;
	
    float a = random_noise_texture(i, octave_id);
    float b = random_noise_texture(vec2(ic.x, i.y), octave_id);
    float c = random_noise_texture(vec2(i.x, ic.y), octave_id);
    float d = random_noise_texture(ic, octave_id);

    vec2 u = smoothstep(0.0, 1.0, f) ;

    return mix(a, b, u.x) + (c - a)* u.y * (1.0 - u.x) + (d - b) * u.x * u.y;
}

void main() {
    vec3 color1 = vec3(1.0,0.0,0.0);
    vec3 color2 = vec3(0.0,1.0,0.0);
    
	float v, o;
	v=0.0;
	float num_octaves = noise_params.x;
	float persistance = noise_params.y;
	vec2 fundamentale_size = noise_params.zw;
	vec2 pos = v_texcoord0 * fundamentale_size;

	for (int i=0; i<int(num_octaves); i++)
	{	
		float octave_i = float(i+1);
    	o = noise2D_Perlin(pos, fundamentale_size, octave_i, noise_seed.xy);
		v += o * pow(persistance, float(i+1));
	}
	float amplitude = (1.0 - persistance) / (1.0 - pow(persistance, num_octaves));
	v *= amplitude;
	gl_FragColor = vec4(v, v, v, 1.0) * color;
}
