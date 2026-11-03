#version 330 core

layout(location = 0) in vec3 aPosition;
layout(location = 1) in vec2 aPlanarUV;
layout(location = 2) in vec2 aBoxUV;
layout(location = 3) in float aShade;
layout(location = 4) in vec3 aNormal;

uniform mat4 uMVP;          // projection * view * model, computed on the CPU
uniform mat4 uModel;        // model only, to turn normals with the object

out vec2 vPlanarUV;
out vec2 vBoxUV;
out vec3 vNormal;
flat out float vShade;      // "flat": the whole triangle uses one gray level

void main()
{
    gl_Position = uMVP * vec4(aPosition, 1.0);
    vPlanarUV = aPlanarUV;
    vBoxUV = aBoxUV;
    vShade = aShade;
    // The model matrix only rotates and scales uniformly, so mat3(uModel)
    // is enough to rotate the normal (we normalise it again in the fragment).
    vNormal = mat3(uModel) * aNormal;
}
