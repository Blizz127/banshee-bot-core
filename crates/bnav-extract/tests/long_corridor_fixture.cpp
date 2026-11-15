// Original synthetic fixture: 300 adjoining quads, no game geometry.
// Compile against the backend's pinned Detour headers/objects and reference ABI.
// The caller records that build association; this program does not build tools.
#include "DetourAlloc.h"
#include "DetourNavMesh.h"
#include "DetourNavMeshBuilder.h"
#include "DetourNavMeshQuery.h"
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <unistd.h>
#include <vector>

namespace {
void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

struct Allocation {
    void operator()(unsigned char* data) const { dtFree(data); }
};

// Never replace or delete an existing artifact. A write failure retains the
// partial output for diagnosis; consumers must require successful completion.
void write_new(const char* path, const std::vector<unsigned char>& bytes) {
    const int fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600);
    require(fd >= 0, "cannot create new fixture output");
    bool good = true;
    std::size_t offset = 0;
    while (offset < bytes.size()) {
        const auto count = write(fd, bytes.data() + offset, bytes.size() - offset);
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) { good = false; break; }
        offset += static_cast<std::size_t>(count);
    }
    if (good && fsync(fd) != 0) good = false;
    if (close(fd) != 0) good = false;
    require(good, "fixture output write failed; partial output retained");
}
}

int main(int argc, char** argv) {
    try {
        require(argc == 2, "usage: long_corridor_fixture NEW_OUTPUT_TILE");
        constexpr int count = 300, nvp = 4;
        std::vector<unsigned short> vertices((count + 1) * 2 * 3, 0);
        std::vector<unsigned short> polygons(count * 2 * nvp, 0xffff);
        std::vector<unsigned short> flags(count, 1);
        std::vector<unsigned char> areas(count, 0);
        for (int i = 0; i <= count; ++i) {
            vertices[i * 6] = vertices[i * 6 + 3] = static_cast<unsigned short>(i);
            vertices[i * 6 + 5] = 4;
        }
        for (int i = 0; i < count; ++i) {
            const int base = i * 2 * nvp;
            polygons[base] = static_cast<unsigned short>(2 * i);
            polygons[base + 1] = static_cast<unsigned short>(2 * i + 1);
            polygons[base + 2] = static_cast<unsigned short>(2 * (i + 1) + 1);
            polygons[base + 3] = static_cast<unsigned short>(2 * (i + 1));
            // dtNavMeshCreateParams uses zero-based neighboring polygon indices.
            if (i > 0) polygons[base + nvp] = static_cast<unsigned short>(i - 1);
            if (i + 1 < count) polygons[base + nvp + 2] = static_cast<unsigned short>(i + 1);
        }
        dtNavMeshCreateParams params{};
        params.verts = vertices.data();
        params.vertCount = (count + 1) * 2;
        params.polys = polygons.data();
        params.polyFlags = flags.data();
        params.polyAreas = areas.data();
        params.polyCount = count;
        params.nvp = nvp;
        params.walkableHeight = 2;
        params.walkableRadius = 0.5f;
        params.walkableClimb = 0.5f;
        params.bmax[0] = count;
        params.bmax[1] = 2;
        params.bmax[2] = 4;
        params.cs = params.ch = 1;
        params.buildBvTree = true;
        unsigned char* data = nullptr;
        int size = 0;
        require(dtCreateNavMeshData(&params, &data, &size), "fixture serialization failed");
        std::unique_ptr<unsigned char, Allocation> allocation(data);
        require(size > 0, "fixture serialization was empty");
        // Loading reconstructs runtime links in place. Save the serialized bytes
        // before that mutation, and keep their allocation alive past the mesh.
        const std::vector<unsigned char> serialized(data, data + size);
        dtNavMesh mesh;
        require(dtStatusSucceed(mesh.init(data, size, 0)), "fixture reload failed");
        dtNavMeshQuery query;
        require(dtStatusSucceed(query.init(&mesh, 2048)), "fixture query init failed");
        dtQueryFilter filter;
        filter.setIncludeFlags(1);
        const float requested_start[]{0.5f, 0, 2}, requested_end[]{299.5f, 0, 2};
        const float extents[]{2, 4, 2};
        float start[3]{}, end[3]{};
        dtPolyRef start_ref = 0, end_ref = 0;
        require(dtStatusSucceed(query.findNearestPoly(requested_start, extents, &filter, &start_ref, start))
                && start_ref, "fixture start polygon absent");
        require(dtStatusSucceed(query.findNearestPoly(requested_end, extents, &filter, &end_ref, end))
                && end_ref, "fixture end polygon absent");
        dtPolyRef full[512]{}, truncated[256]{};
        int full_count = 0, truncated_count = 0;
        const auto full_status = query.findPath(start_ref, end_ref, start, end, &filter,
                                               full, &full_count, 512);
        require(dtStatusSucceed(full_status) && !dtStatusDetail(full_status, DT_BUFFER_TOO_SMALL)
                && !dtStatusDetail(full_status, DT_OUT_OF_NODES)
                && !dtStatusDetail(full_status, DT_PARTIAL_RESULT)
                && full_count == count && full[full_count - 1] == end_ref,
                "fixture did not prove a complete 300-polygon corridor");
        const auto truncated_status = query.findPath(start_ref, end_ref, start, end, &filter,
                                                    truncated, &truncated_count, 256);
        require(dtStatusSucceed(truncated_status) && dtStatusDetail(truncated_status, DT_BUFFER_TOO_SMALL)
                && !dtStatusDetail(truncated_status, DT_OUT_OF_NODES)
                && truncated_count == 256 && truncated[truncated_count - 1] != end_ref,
                "fixture did not isolate path-buffer exhaustion");
        write_new(argv[1], serialized);
        std::cout << "{\"scope\":\"synthetic-300-quad-corridor\",\"reference_bits\":"
                  << sizeof(dtPolyRef) * 8 << ",\"polygons\":300,\"vertices\":602,\"bytes\":" << size
                  << ",\"full_path_polygons\":" << full_count << ",\"truncated_path_polygons\":"
                  << truncated_count << ",\"node_limit\":2048,\"budget_detail_verified\":true}\n";
        require(bool(std::cout), "fixture result output failed");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "long_corridor_fixture: " << error.what() << '\n';
        return 2;
    }
}
