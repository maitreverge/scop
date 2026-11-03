#version 330 core

in vec2 vPlanarUV;
in vec2 vBoxUV;
in vec3 vNormal;
flat in float vShade;

uniform sampler2D uTexture;
uniform float uTextureMix;  // 0 = gray faces,       1 = texture
uniform float uBoxMix;      // 0 = planar mapping,   1 = box mapping
uniform float uLightMix;    // 0 = no lighting,      1 = lighting
// Every value in between is a frame of a smooth transition.

out vec4 FragColor;

const vec3 LIGHT_DIR = normalize(vec3(0.4, 0.7, 1.0));

void main()
{
    vec3 gray = vec3(vShade);

    vec3 planar = texture(uTexture, vPlanarUV).rgb;
    vec3 box = texture(uTexture, vBoxUV).rgb;
    vec3 textured = mix(planar, box, uBoxMix);

    vec3 color = mix(gray, textured, uTextureMix);

    // Two-sided lighting: some models have holes, so we may see the inside
    // of a face. Flip its normal in that case so it is lit too.
    vec3 n = normalize(vNormal);
    if (!gl_FrontFacing)
        n = -n;
    float diffuse = max(dot(n, LIGHT_DIR), 0.0);
    float light = 0.35 + 0.65 * diffuse;
    // Gray faces are rather dark, so boost them a bit when lit.
    vec3 lit = color * light * mix(1.6, 1.0, uTextureMix);

    FragColor = vec4(mix(color, lit, uLightMix), 1.0);
}
