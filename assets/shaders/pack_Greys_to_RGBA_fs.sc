$input v_texcoord0

#include <bgfx_shader.sh>

//uniform vec4 color;

// Only R component are read:

SAMPLER2D(tex_R, 0);
SAMPLER2D(tex_G, 1);
SAMPLER2D(tex_B, 2);
//SAMPLER2D(tex_A, 3);


void main() {
    float R = texture2D(tex_R, v_texcoord0).r;
    float G = texture2D(tex_G, v_texcoord0).r;
    float B = texture2D(tex_B, v_texcoord0).r;
    //float A = texture2D(tex_A, v_texcoord0).r;
    float A = 1.0;
	gl_FragColor = vec4(R, G, B, A);
}
