// Original offline compatibility fixture. Build manually against an explicitly
// selected external Recast/Detour source checkout; never bundled game geometry.
#include "DetourNavMeshBuilder.h"
#include "DetourNavMesh.h"
#include "DetourAlloc.h"
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

int main(int argc, char** argv) {
    if (argc != 3) return 2;
    const std::string profile(argv[1]);
    const bool acore = profile == "acore-v20";
    if (!acore && profile != "cmangos-v8") return 2;
    if (sizeof(dtPolyRef) != (acore ? 8 : 4)) return 3;
    unsigned short vertices[] = {0, 0, 0, 10, 0, 0, 10, 0, 10, 0, 0, 10};
    unsigned short polygons[] = {0, 1, 2, 3, 0xffff, 0xffff,
                                0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff};
    unsigned short flags[] = {1};
    unsigned char areas[] = {1};
    dtNavMeshCreateParams params{};
    params.verts = vertices;
    params.vertCount = 4;
    params.polys = polygons;
    params.polyFlags = flags;
    params.polyAreas = areas;
    params.polyCount = 1;
    params.nvp = 6;
    params.walkableHeight = 2;
    params.walkableRadius = 0.5f;
    params.walkableClimb = 0.4f;
    params.bmax[0] = 10;
    params.bmax[1] = 2;
    params.bmax[2] = 10;
    params.cs = 1;
    params.ch = 1;
    params.buildBvTree = true;
    unsigned char* data = nullptr;
    int size = 0;
    if (!dtCreateNavMeshData(&params, &data, &size)) return 4;
    std::vector<unsigned char> wrapper(acore ? 56 : 20, 0);
    const uint32_t header[] = {0x4d4d4150, DT_NAVMESH_VERSION,
                              acore ? 20u : 8u, static_cast<uint32_t>(size)};
    std::memcpy(wrapper.data(), header, sizeof(header));
    std::ofstream output(argv[2], std::ios::binary);
    output.write(reinterpret_cast<char*>(wrapper.data()), wrapper.size());
    output.write(reinterpret_cast<char*>(data), size);
    output.close();
    dtFree(data);
    if (!output) return 5;
    std::cout << "synthetic=true profile=" << profile << " detour_version=" << DT_NAVMESH_VERSION
              << " reference_bits=" << sizeof(dtPolyRef) * 8 << " payload_bytes=" << size << '\n';
}
