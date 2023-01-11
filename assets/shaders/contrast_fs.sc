$input v_texcoord0

#include <bgfx_shader.sh>

uniform vec4 params; //x:brightness, y:contrast, z:threshold

SAMPLER2D(u_tex, 0);

#define FACTEUR_GRIS_R 0.11
#define FACTEUR_GRIS_V 0.59
#define FACTEUR_GRIS_B 0.3

void main() {
    
    vec4 c;
	vec4 p = texture2D(u_tex, v_texcoord0);	
	float c0 = p.r * FACTEUR_GRIS_R + p.g * FACTEUR_GRIS_V + p.b * FACTEUR_GRIS_B;

    //Brightness:
    c.rgb = params.x * p.rgb;
    
    //Contrast:
    c.r = clamp(c.r + params.y * (c0 - params.z), 0.0, 1.0);
    c.g = clamp(c.g + params.y * (c0 - params.z), 0.0, 1.0);
    c.b = clamp(c.b + params.y * (c0 - params.z), 0.0, 1.0);

    //c.a = clamp(c.b + params.y * (c0 - params.z), 0.0, 1.0);	//Alpha layer as a function of pixel brightness
    c.a = 1.0;

	gl_FragColor = c;
}
