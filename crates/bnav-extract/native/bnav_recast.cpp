// Original Banshee bridge to externally supplied Recast/Detour (zlib licence).
// Reads a canonical triangle stream; writes an IPC envelope containing a real
// dtCreateNavMeshData tile. No proprietary formats, game assets or server APIs.
#include "Recast.h"
#include "DetourAlloc.h"
#include "DetourNavMesh.h"
#include "DetourNavMeshBuilder.h"
#include "DetourNavMeshQuery.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
void need(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

struct EmptyTile : std::runtime_error { using std::runtime_error::runtime_error; };

int integer(const char* value, int minimum, int maximum) {
    std::size_t used = 0;
    long result = std::stol(value, &used);
    need(used == std::strlen(value) && result >= minimum && result <= maximum,
         "integer grid argument is outside supported limits");
    return static_cast<int>(result);
}

class Context final : public rcContext {
    void doLog(const rcLogCategory, const char* message, const int length) override {
        std::cerr.write(message, length) << '\n';
    }
};

float number(const char* value) {
    std::size_t used = 0;
    float result = std::stof(value, &used);
    need(used == std::strlen(value) && std::isfinite(result), "expected finite numeric argument");
    return result;
}

struct Geometry {
    std::vector<float> vertices;
    std::vector<int> triangles;
};

Geometry read_geometry() {
    std::string magic;
    int vertices = 0, triangles = 0;
    std::cin >> magic >> vertices >> triangles;
    need(magic == "BNAV_TRIANGLES_V1" && vertices > 0 && vertices <= 1000000 &&
         triangles > 0 && triangles <= 1000000, "invalid or excessive canonical geometry counts");
    Geometry g;
    g.vertices.resize(static_cast<std::size_t>(vertices) * 3);
    g.triangles.resize(static_cast<std::size_t>(triangles) * 3);
    for (float& value : g.vertices) {
        std::cin >> value;
        need(bool(std::cin) && std::isfinite(value) && std::abs(value) < 10000000,
             "invalid or excessive geometry coordinate");
    }
    for (int& index : g.triangles) {
        std::cin >> index;
        need(bool(std::cin) && index >= 0 && index < vertices, "invalid triangle index");
    }
    std::string trailing;
    need(!(std::cin >> trailing), "trailing canonical geometry data");
    return g;
}

// Only eliminate triangles strictly outside the padded horizontal heightfield.
// A crossing triangle may have all three vertices outside; a bounds comparison
// retains it, along with every triangle touching a border. Preserve source order
// because rasterized span merging must receive the same contributing sequence.
std::vector<int> select_tile_triangles(const Geometry& geometry, const rcConfig& config) {
    std::vector<int> selected;
    for (std::size_t triangle = 0; triangle < geometry.triangles.size(); triangle += 3) {
        bool disjoint = false;
        for (const int axis : {0, 2}) {
            const auto coordinate = [&](std::size_t corner) {
                return geometry.vertices[static_cast<std::size_t>(geometry.triangles[triangle + corner]) * 3 + axis];
            };
            const float lower = std::min({coordinate(0), coordinate(1), coordinate(2)});
            const float upper = std::max({coordinate(0), coordinate(1), coordinate(2)});
            if (upper < config.bmin[axis] || lower > config.bmax[axis]) {
                disjoint = true;
                break;
            }
        }
        if (!disjoint) {
            selected.insert(selected.end(), geometry.triangles.begin() + triangle,
                            geometry.triangles.begin() + triangle + 3);
        }
    }
    return selected;
}

struct BuildSettings {
    float cs, ch, height, radius, climb, slope;
};

BuildSettings read_build_settings(char** argv) {
    const float cs = number(argv[2]), ch = number(argv[3]);
    const float height = number(argv[4]), radius = number(argv[5]);
    const float climb = number(argv[6]), slope = number(argv[7]);
    need(cs > 0 && ch > 0 && height > 0 && radius >= 0 && climb >= 0 && slope >= 0 && slope < 90,
         "invalid agent or voxel configuration");
    need(height / ch >= 3 && height / ch <= 8191 && radius / cs <= 1024 && climb / ch <= 8191,
         "agent dimensions exceed supported voxel limits (height must span at least three cells)");
    return {cs, ch, height, radius, climb, slope};
}

void build(int argc, char** argv, bool tiled = false, const Geometry* shared_geometry = nullptr,
           std::vector<unsigned char>* raw_result = nullptr) {
    need(argc == (tiled ? 15 : 8), "build requires six settings; build-tile also requires origin-x origin-z min-y max-y tile-cells tile-x tile-z");
    const auto settings = read_build_settings(argv);
    const float cs = settings.cs, ch = settings.ch;
    const float height = settings.height, radius = settings.radius;
    const float climb = settings.climb, slope = settings.slope;
    // Legacy calls still decode at the same point after settings validation.
    // Batch calls borrow one immutable decode, keeping per-cell validation and
    // every Recast/Detour operation below in the original order.
    const auto decoded = shared_geometry ? Geometry{} : read_geometry();
    const Geometry& g = shared_geometry ? *shared_geometry : decoded;
    const int nv = static_cast<int>(g.vertices.size() / 3);
    const int nt = static_cast<int>(g.triangles.size() / 3);
    Context context;
    rcConfig config{};
    config.cs = cs;
    config.ch = ch;
    config.walkableSlopeAngle = slope;
    config.walkableHeight = static_cast<int>(std::ceil(height / ch));
    config.walkableClimb = static_cast<int>(std::floor(climb / ch));
    config.walkableRadius = static_cast<int>(std::ceil(radius / cs));
    config.maxEdgeLen = std::max(1, static_cast<int>(std::min(4096.0, 12.0 / double(cs))));
    config.maxSimplificationError = 1.3f;
    config.minRegionArea = 8 * 8;
    config.mergeRegionArea = 20 * 20;
    config.maxVertsPerPoly = DT_VERTS_PER_POLYGON;
    config.detailSampleDist = 6 * cs;
    config.detailSampleMaxError = ch;
    rcCalcBounds(g.vertices.data(), nv, config.bmin, config.bmax);
    const float geometry_min_y = config.bmin[1], geometry_max_y = config.bmax[1];
    config.bmin[1] -= ch;
    config.bmax[1] += height + climb + ch;
    int tile_x = 0, tile_z = 0;
    if (tiled) {
        const float ox = number(argv[8]), oz = number(argv[9]);
        const float min_y = number(argv[10]), max_y = number(argv[11]);
        const int cells = integer(argv[12], 8, 1024);
        tile_x = integer(argv[13], 0, 4095);
        tile_z = integer(argv[14], 0, 4095);
        need(min_y <= max_y && min_y <= geometry_min_y && max_y >= geometry_max_y,
             "global vertical bounds must contain the supplied geometry");
        config.tileSize = cells;
        config.borderSize = config.walkableRadius + 3;
        const double side = double(cells) * cs;
        const double border = double(config.borderSize) * cs;
        config.bmin[0] = static_cast<float>(double(ox) + tile_x * side - border);
        config.bmax[0] = static_cast<float>(double(ox) + (tile_x + 1) * side + border);
        config.bmin[2] = static_cast<float>(double(oz) + tile_z * side - border);
        config.bmax[2] = static_cast<float>(double(oz) + (tile_z + 1) * side + border);
        config.bmin[1] = min_y - ch;
        config.bmax[1] = max_y + height + climb + ch;
        for (int axis = 0; axis < 3; ++axis)
            need(std::isfinite(config.bmin[axis]) && std::isfinite(config.bmax[axis]) &&
                 std::abs(config.bmin[axis]) < 10000000 && std::abs(config.bmax[axis]) < 10000000,
                 "tile bounds exceed finite supported coordinates");
    }
    const double width = (double(config.bmax[0]) - config.bmin[0]) / cs;
    const double depth = (double(config.bmax[2]) - config.bmin[2]) / cs;
    need(width >= 1 && depth >= 1 && width < 4096 && depth < 4096 && width * depth <= 4000000,
         "single-tile grid limit exceeded; choose coarser cells or split geometry");
    need((double(config.bmax[1]) - config.bmin[1]) / ch < 8191,
         "vertical span exceeds Recast heightfield range");
    rcCalcGridSize(config.bmin, config.bmax, cs, &config.width, &config.height);
    const auto selected = tiled ? select_tile_triangles(g, config) : std::vector<int>{};
    const int* triangles = tiled ? selected.data() : g.triangles.data();
    const int triangle_count = tiled ? static_cast<int>(selected.size() / 3) : nt;
    if (tiled) {
        std::cerr << "triangle_selection=padded_xz input_triangles=" << nt
                  << " candidate_triangles=" << triangle_count
                  << " culled_triangles=" << nt - triangle_count << '\n';
        if (triangle_count == 0) throw EmptyTile("tile contains no triangles overlapping its padded bounds");
    }
    auto solid = std::unique_ptr<rcHeightfield, decltype(&rcFreeHeightField)>(rcAllocHeightfield(), rcFreeHeightField);
    need(bool(solid), "heightfield allocation failed");
    need(rcCreateHeightfield(&context, *solid, config.width, config.height, config.bmin, config.bmax, cs, ch),
         "heightfield creation failed");
    std::vector<unsigned char> areas(triangle_count, RC_NULL_AREA);
    rcMarkWalkableTriangles(&context, slope, g.vertices.data(), nv, triangles, triangle_count, areas.data());
    need(rcRasterizeTriangles(&context, g.vertices.data(), nv, triangles, areas.data(), triangle_count,
                             *solid, config.walkableClimb), "triangle rasterization failed");
    rcFilterLowHangingWalkableObstacles(&context, config.walkableClimb, *solid);
    rcFilterLedgeSpans(&context, config.walkableHeight, config.walkableClimb, *solid);
    rcFilterWalkableLowHeightSpans(&context, config.walkableHeight, *solid);
    auto compact = std::unique_ptr<rcCompactHeightfield, decltype(&rcFreeCompactHeightfield)>(
        rcAllocCompactHeightfield(), rcFreeCompactHeightfield);
    need(bool(compact), "compact heightfield allocation failed");
    need(rcBuildCompactHeightfield(&context, config.walkableHeight, config.walkableClimb, *solid, *compact),
         "compact heightfield creation failed");
    solid.reset();
    if (tiled && compact->spanCount == 0) throw EmptyTile("tile contains no walkable spans");
    need(rcErodeWalkableArea(&context, config.walkableRadius, *compact), "walkable erosion failed");
    need(rcBuildDistanceField(&context, *compact), "distance field creation failed");
    need(rcBuildRegions(&context, *compact, config.borderSize, config.minRegionArea, config.mergeRegionArea), "region creation failed");
    auto contours = std::unique_ptr<rcContourSet, decltype(&rcFreeContourSet)>(rcAllocContourSet(), rcFreeContourSet);
    need(bool(contours), "contour allocation failed");
    need(rcBuildContours(&context, *compact, config.maxSimplificationError, config.maxEdgeLen, *contours),
         "contour creation failed");
    auto polygons = std::unique_ptr<rcPolyMesh, decltype(&rcFreePolyMesh)>(rcAllocPolyMesh(), rcFreePolyMesh);
    need(bool(polygons), "polygon mesh allocation failed");
    need(rcBuildPolyMesh(&context, *contours, config.maxVertsPerPoly, *polygons), "polygon mesh creation failed");
    if (tiled && polygons->npolys == 0) throw EmptyTile("tile contains no walkable polygons after filtering");
    need(polygons->npolys > 0 && polygons->nverts > 0 && polygons->nverts < 65535,
         "no usable polygons, or vertex limit exceeded; check winding, scale and agent dimensions");
    auto details = std::unique_ptr<rcPolyMeshDetail, decltype(&rcFreePolyMeshDetail)>(rcAllocPolyMeshDetail(), rcFreePolyMeshDetail);
    need(bool(details), "detail mesh allocation failed");
    need(rcBuildPolyMeshDetail(&context, *polygons, *compact, config.detailSampleDist,
                              config.detailSampleMaxError, *details), "detail mesh creation failed");
    for (int i = 0; i < polygons->npolys; ++i) {
        polygons->areas[i] = 0;
        polygons->flags[i] = 1;
    }
    dtNavMeshCreateParams params{};
    params.verts = polygons->verts;
    params.vertCount = polygons->nverts;
    params.polys = polygons->polys;
    params.polyAreas = polygons->areas;
    params.polyFlags = polygons->flags;
    params.polyCount = polygons->npolys;
    params.nvp = polygons->nvp;
    params.detailMeshes = details->meshes;
    params.detailVerts = details->verts;
    params.detailVertsCount = details->nverts;
    params.detailTris = details->tris;
    params.detailTriCount = details->ntris;
    params.walkableHeight = height;
    params.walkableRadius = radius;
    params.walkableClimb = climb;
    std::copy_n(polygons->bmin, 3, params.bmin);
    std::copy_n(polygons->bmax, 3, params.bmax);
    params.cs = cs;
    params.ch = ch;
    params.buildBvTree = true;
    params.tileX = tile_x;
    params.tileY = tile_z;
    unsigned char* data = nullptr;
    int size = 0;
    need(dtCreateNavMeshData(&params, &data, &size), "Detour serialization failed");
    auto allocation = std::unique_ptr<unsigned char, decltype(&dtFree)>(data, dtFree);
    need(size > 100 && size <= 64 * 1024 * 1024, "unexpected Detour output size");
    dtNavMesh mesh;
    need(dtStatusSucceed(mesh.init(data, size, 0)), "Detour rejected its serialized tile");
    // IPC only. Rust strips this 16-byte transport header; the saved file is
    // exclusively the native dtCreateNavMeshData output, not a custom navmesh.
    const uint32_t header[] = {0x56414e42, DT_NAVMESH_VERSION,
                              static_cast<uint32_t>(sizeof(dtPolyRef) * 8), static_cast<uint32_t>(size)};
    const uint16_t endian = 1;
    need(*reinterpret_cast<const unsigned char*>(&endian) == 1, "only little-endian hosts are supported");
    if (raw_result) {
        raw_result->assign(data, data + size);
    } else {
        std::cout.write(reinterpret_cast<const char*>(header), sizeof(header));
        std::cout.write(reinterpret_cast<const char*>(data), size);
        need(bool(std::cout), "output write failed");
    }
    std::cerr << "recast_build=PASS detour_reload=PASS reference_bits=" << sizeof(dtPolyRef) * 8
              << " polygons=" << polygons->npolys << " vertices=" << polygons->nverts
              << " grid=" << config.width << 'x' << config.height << " bytes=" << size
              << " tile=" << tile_x << ',' << tile_z << " border_cells=" << config.borderSize << '\n';
}

// Bounded streaming IPC only. The raw tile bytes have no legacy BNAV envelope;
// the caller must require the final BEND record before accepting the batch.
void emit_batch_record(const std::array<std::uint32_t, 4>& words,
                       const std::vector<unsigned char>* payload = nullptr) {
    std::cout.write(reinterpret_cast<const char*>(words.data()), sizeof(std::uint32_t) * words.size());
    if (payload && !payload->empty())
        std::cout.write(reinterpret_cast<const char*>(payload->data()),
                        static_cast<std::streamsize>(payload->size()));
    std::cout.flush();
    need(bool(std::cout), "batch output write failed");
}

void build_tiles(int argc, char** argv) {
    need(argc >= 15 && argc <= 45 && (argc - 13) % 2 == 0,
         "build-tiles requires six settings, origin-x origin-z min-y max-y tile-cells and 1..16 coordinate pairs");
    const auto count = static_cast<std::uint32_t>((argc - 13) / 2);
    std::vector<std::pair<int, int>> cells;
    cells.reserve(count);
    std::set<std::pair<int, int>> unique;
    for (int arg = 13; arg < argc; arg += 2) {
        const int x = integer(argv[arg], 0, 4095), z = integer(argv[arg + 1], 0, 4095);
        need(unique.emplace(x, z).second, "duplicate batch tile coordinates");
        cells.emplace_back(x, z);
    }
    // Reject malformed common numeric fields before reading geometry or
    // emitting the protocol header. Global geometry/Y checks still run for
    // every cell in the same tile engine as an individual build-tile call.
    read_build_settings(argv);
    for (int arg = 8; arg <= 11; ++arg) number(argv[arg]);
    integer(argv[12], 8, 1024);
    const std::uint16_t endian = 1;
    need(*reinterpret_cast<const unsigned char*>(&endian) == 1, "only little-endian hosts are supported");
    const auto geometry = read_geometry();
    std::cerr << "geometry_decode_count=1 batch_cells=" << count << '\n';
    emit_batch_record({0x54424e42u, 1u, static_cast<std::uint32_t>(sizeof(dtPolyRef) * 8), count});

    std::array<char*, 15> cell_args{};
    std::copy_n(argv, 13, cell_args.begin());
    std::uint64_t total_payload = 0;
    constexpr std::uint64_t max_payload = 128u * 1024u * 1024u;
    std::uint32_t built = 0, empty = 0;
    for (std::uint32_t index = 0; index < count; ++index) {
        cell_args[13] = argv[13 + index * 2];
        cell_args[14] = argv[14 + index * 2];
        const auto& cell = cells[index];
        std::cerr << "batch_cell_x=" << cell.first << " batch_cell_z=" << cell.second << '\n';
        std::vector<unsigned char> payload;
        std::uint32_t status = 0;
        try {
            build(static_cast<int>(cell_args.size()), cell_args.data(), true, &geometry, &payload);
        } catch (const EmptyTile& error) {
            status = 3;
            std::cerr << "bnav-recast: empty_tile=" << error.what() << '\n';
        }
        need(payload.size() <= 64u * 1024u * 1024u &&
             ((status == 0 && payload.size() > 100) || (status == 3 && payload.empty())),
             "invalid batch tile payload");
        // Check before any bytes of this cell's record are emitted. Previous
        // records may already be consumed, but an error never adds BEND.
        need(payload.size() <= max_payload - total_payload,
             "batch total payload exceeds 128 MiB limit");
        emit_batch_record({static_cast<std::uint32_t>(cell.first), static_cast<std::uint32_t>(cell.second),
                           status, static_cast<std::uint32_t>(payload.size())}, &payload);
        total_payload += payload.size();
        if (status == 3) ++empty;
        else ++built;
    }
    emit_batch_record({0x444e4542u, count, built, empty});
}

// Shared envelope checks. Imported tiles receive additional structural checks
// below. All query modes are local diagnostics, not untrusted-file server loaders.
std::vector<unsigned char> load_tile(const char* path) {
    std::ifstream input(path, std::ios::binary | std::ios::ate);
    need(bool(input), "cannot open tile");
    const auto size = input.tellg();
    need(size >= std::streamoff(sizeof(dtMeshHeader)) && size <= std::streamoff(64 * 1024 * 1024), "invalid tile file size");
    std::vector<unsigned char> bytes(static_cast<std::size_t>(size));
    input.seekg(0);
    input.read(reinterpret_cast<char*>(bytes.data()), size);
    need(bool(input), "tile read failed");
    dtMeshHeader h{};
    std::memcpy(&h, bytes.data(), sizeof(h));
    need(h.magic == DT_NAVMESH_MAGIC && h.version == DT_NAVMESH_VERSION, "tile version or byte order mismatch");
    const std::array<int, 9> counts{h.vertCount,h.polyCount,h.maxLinkCount,h.detailMeshCount,
        h.detailVertCount,h.detailTriCount,h.bvNodeCount,h.offMeshConCount,h.offMeshBase};
    for (const int count : counts) need(count >= 0, "negative tile count");
    const std::array<std::size_t,8> strides{sizeof(float)*3,sizeof(dtPoly),sizeof(dtLink),sizeof(dtPolyDetail),
        sizeof(float)*3,4,sizeof(dtBVNode),sizeof(dtOffMeshConnection)};
    std::uint64_t expected = sizeof(dtMeshHeader);
    for (std::size_t i = 0; i < strides.size(); ++i) expected += std::uint64_t(counts[i]) * strides[i];
    need(expected == bytes.size() && h.polyCount > 0 && h.vertCount > 0, "tile sections do not match this backend ABI");
    need(h.offMeshBase <= h.polyCount && h.offMeshConCount == h.polyCount - h.offMeshBase &&
         h.detailMeshCount == h.offMeshBase, "invalid tile polygon partition");
    for (int axis = 0; axis < 3; ++axis)
        need(std::isfinite(h.bmin[axis]) && std::isfinite(h.bmax[axis]) && h.bmin[axis] <= h.bmax[axis],
             "invalid tile bounds");
    return bytes;
}

template<class T> T item(const std::vector<unsigned char>& data, std::size_t offset) {
    need(offset <= data.size() && sizeof(T) <= data.size() - offset, "truncated imported structure");
    T result{};
    std::memcpy(&result, data.data() + offset, sizeof(T));
    return result;
}

bool bounded_coordinate(float value) {
    return std::isfinite(value) && std::abs(value) <= 10000000;
}

// Native addTile() trusts indices and reconstructs runtime links. Check every
// serialized index used by loading/nearest/path operations before giving it data.
// Geometry, flags, areas, connection records and section bytes are not repaired.
void validate_import_tile(const std::vector<unsigned char>& data) {
    const auto h = item<dtMeshHeader>(data, 0);
    need(h.maxLinkCount > 0, "imported tile has no link storage");
    need(h.layer == 0 && h.x >= -4095 && h.x <= 4095 && h.y >= -4095 && h.y <= 4095,
         "imported tile coordinate or layer is outside diagnostic limits");
    for (int axis = 0; axis < 3; ++axis)
        need(bounded_coordinate(h.bmin[axis]) && bounded_coordinate(h.bmax[axis]),
             "imported tile bounds exceed diagnostic limits");
    need(std::isfinite(h.walkableHeight) && h.walkableHeight > 0 &&
         std::isfinite(h.walkableRadius) && h.walkableRadius >= 0 &&
         std::isfinite(h.walkableClimb) && h.walkableClimb >= 0 &&
         std::isfinite(h.bvQuantFactor) && h.bvQuantFactor > 0,
         "invalid imported agent or quantization settings");
    const std::size_t verts = sizeof(dtMeshHeader);
    const std::size_t polys = verts + std::size_t(h.vertCount) * 12;
    const std::size_t details = polys + std::size_t(h.polyCount) * sizeof(dtPoly) +
                                std::size_t(h.maxLinkCount) * sizeof(dtLink);
    const std::size_t detail_verts = details + std::size_t(h.detailMeshCount) * sizeof(dtPolyDetail);
    const std::size_t detail_tris = detail_verts + std::size_t(h.detailVertCount) * 12;
    const std::size_t bv = detail_tris + std::size_t(h.detailTriCount) * 4;
    const std::size_t offmesh = bv + std::size_t(h.bvNodeCount) * sizeof(dtBVNode);
    for (int i = 0; i < h.vertCount * 3; ++i)
        need(bounded_coordinate(item<float>(data, verts + std::size_t(i) * 4)),
             "invalid imported vertex coordinate");
    for (int i = 0; i < h.detailVertCount * 3; ++i)
        need(bounded_coordinate(item<float>(data, detail_verts + std::size_t(i) * 4)),
             "invalid imported detail vertex coordinate");
    for (int i = 0; i < h.polyCount; ++i) {
        const auto p = item<dtPoly>(data, polys + std::size_t(i) * sizeof(dtPoly));
        const bool ground = i < h.offMeshBase;
        need(p.getType() == (ground ? DT_POLYTYPE_GROUND : DT_POLYTYPE_OFFMESH_CONNECTION) &&
             p.vertCount >= (ground ? 3 : 2) && p.vertCount <= DT_VERTS_PER_POLYGON &&
             (ground || p.vertCount == 2), "invalid imported polygon type or vertex count");
        for (int j = 0; j < p.vertCount; ++j) {
            need(p.verts[j] < h.vertCount, "imported polygon vertex index is out of bounds");
            const unsigned short neighbour = p.neis[j];
            if (neighbour & DT_EXT_LINK)
                need(ground && (neighbour == (DT_EXT_LINK | 0) || neighbour == (DT_EXT_LINK | 2) ||
                     neighbour == (DT_EXT_LINK | 4) || neighbour == (DT_EXT_LINK | 6)),
                     "invalid imported external portal side");
            else
                need(neighbour <= h.offMeshBase, "imported polygon neighbour is out of bounds");
        }
        if (!ground) continue;
        const auto d = item<dtPolyDetail>(data, details + std::size_t(i) * sizeof(dtPolyDetail));
        need(std::uint64_t(d.vertBase) + d.vertCount <= std::uint64_t(h.detailVertCount) &&
             std::uint64_t(d.triBase) + d.triCount <= std::uint64_t(h.detailTriCount) && d.triCount > 0,
             "imported detail mesh range is out of bounds");
        for (unsigned int tri = 0; tri < d.triCount; ++tri)
            for (int corner = 0; corner < 3; ++corner)
                need(data[detail_tris + (std::size_t(d.triBase) + tri) * 4 + corner] <
                     unsigned(p.vertCount) + d.vertCount, "imported detail triangle index is out of bounds");
    }
    for (int i = 0; i < h.bvNodeCount; ++i) {
        const auto node = item<dtBVNode>(data, bv + std::size_t(i) * sizeof(dtBVNode));
        for (int axis = 0; axis < 3; ++axis)
            need(node.bmin[axis] <= node.bmax[axis], "inverted imported BV node bounds");
        if (node.i >= 0)
            need(node.i < h.offMeshBase, "imported BV leaf index is out of bounds");
        else
            need(-std::int64_t(node.i) <= std::int64_t(h.bvNodeCount) - i,
                 "imported BV escape index is out of bounds");
    }
    for (int i = 0; i < h.offMeshConCount; ++i) {
        const auto c = item<dtOffMeshConnection>(data, offmesh + std::size_t(i) * sizeof(dtOffMeshConnection));
        need(c.poly == h.offMeshBase + i, "imported off-mesh polygon index is out of bounds or order");
        need(c.side == 0xff || c.side <= 7, "invalid imported off-mesh side");
        need(std::isfinite(c.rad) && c.rad >= 0, "invalid imported off-mesh radius");
        for (float value : c.pos) need(bounded_coordinate(value), "invalid imported off-mesh coordinate");
    }
}

void query_mesh(dtNavMesh& mesh, char** positions, int loaded_tiles,
                unsigned short include_flags = 1, unsigned short exclude_flags = 0,
                const char* imported_profile = nullptr) {
    dtNavMeshQuery q;
    need(dtStatusSucceed(q.init(&mesh, 2048)), "query initialization failed");
    const float requested_start[]{number(positions[0]),number(positions[1]),number(positions[2])};
    const float requested_end[]{number(positions[3]),number(positions[4]),number(positions[5])};
    if (imported_profile) {
        const auto& params = *mesh.getParams();
        for (const float* position : {requested_start, requested_end}) {
            for (int axis = 0; axis < 3; ++axis)
                need(bounded_coordinate(position[axis]), "requested endpoint exceeds diagnostic coordinate limit");
            const double tx = std::floor((double(position[0]) - params.orig[0]) / params.tileWidth);
            const double ty = std::floor((double(position[2]) - params.orig[2]) / params.tileHeight);
            need(tx >= -4095 && tx <= 4095 && ty >= -4095 && ty <= 4095 &&
                 mesh.getTileAt(static_cast<int>(tx), static_cast<int>(ty), 0),
                 "requested endpoint tile is not in the selected set");
        }
    }
    const float extents[]{2,4,2};
    dtPolyRef start_ref=0, end_ref=0;
    float start[3]{},end[3]{};
    dtQueryFilter filter;
    filter.setIncludeFlags(include_flags);
    filter.setExcludeFlags(exclude_flags);
    need(dtStatusSucceed(q.findNearestPoly(requested_start,extents,&filter,&start_ref,start)) && start_ref,
         "start has no nearby polygon");
    need(dtStatusSucceed(q.findNearestPoly(requested_end,extents,&filter,&end_ref,end)) && end_ref,
         "end has no nearby polygon");
    dtPolyRef corridor[256]{};
    int corridor_count=0;
    auto status=q.findPath(start_ref,end_ref,start,end,&filter,corridor,&corridor_count,256);
    need(dtStatusSucceed(status) && !dtStatusDetail(status,DT_BUFFER_TOO_SMALL) &&
         !dtStatusDetail(status,DT_OUT_OF_NODES) && corridor_count>0 && corridor[corridor_count-1]==end_ref,
         "no complete path within query budget");
    float points[256*3]{};
    unsigned char flags[256]{};
    dtPolyRef references[256]{};
    int point_count=0;
    status=q.findStraightPath(start,end,corridor,corridor_count,points,flags,references,&point_count,256);
    need(dtStatusSucceed(status) && !dtStatusDetail(status,DT_BUFFER_TOO_SMALL) && point_count>=2,
         "straight path failed or exceeded budget");
    float direct_fraction=0, normal[3]{};
    int direct_count=0;
    dtPolyRef direct[256]{};
    need(dtStatusSucceed(q.raycast(start_ref,start,end,&filter,&direct_fraction,normal,direct,&direct_count,256)),
         "direct-path raycast failed");
    std::set<std::pair<int,int>> traversed;
    for (int i = 0; i < corridor_count; ++i) {
        const dtMeshTile* tile = nullptr;
        const dtPoly* poly = nullptr;
        need(dtStatusSucceed(mesh.getTileAndPolyByRef(corridor[i], &tile, &poly)), "corridor lost a polygon");
        traversed.emplace(tile->header->x, tile->header->y);
    }
    if (imported_profile) std::cout << std::setprecision(std::numeric_limits<float>::max_digits10);
    std::cout << "{\"complete\":true,\"reference_bits\":" << sizeof(dtPolyRef)*8
              << ",\"loaded_tiles\":" << loaded_tiles << ",\"traversed_tiles\":" << traversed.size()
              << ",\"corridor_polygons\":" << corridor_count << ",\"direct_path_blocked\":"
              << (direct_fraction < 1 ? "true" : "false") << ",\"points\":[";
    for (int i=0;i<point_count;++i) {
        if (i) std::cout << ',';
        std::cout << '[' << points[3*i] << ',' << points[3*i+1] << ',' << points[3*i+2] << ']';
    }
    std::cout << ']';
    if (imported_profile) {
        std::cout << ",\"scope\":\"selected-tiles\",\"whole_map_coverage\":false,\"profile\":\"" << imported_profile
                  << "\",\"include_flags\":" << include_flags << ",\"exclude_flags\":" << exclude_flags;
        const char* names[]{"requested_start", "requested_end", "snapped_start", "snapped_end"};
        const float* values[]{requested_start, requested_end, start, end};
        for (int i = 0; i < 4; ++i)
            std::cout << ",\"" << names[i] << "\":[" << values[i][0] << ',' << values[i][1] << ',' << values[i][2] << ']';
    }
    std::cout << "}\n";
}

void query(int argc, char** argv) {
    need(argc == 9, "query requires tile sx sy sz ex ey ez");
    auto bytes = load_tile(argv[2]);
    dtNavMesh mesh;
    need(dtStatusSucceed(mesh.init(bytes.data(), static_cast<int>(bytes.size()), 0)), "tile reload failed");
    query_mesh(mesh, argv + 3, 1);
}

void query_tiles(int argc, char** argv) {
    need(argc >= 13 && argc <= 1036,
         "query-tiles requires origin-x origin-y origin-z tile-world sx sy sz ex ey ez and 1..1024 tiles");
    dtNavMeshParams params{};
    for (int axis = 0; axis < 3; ++axis) params.orig[axis] = number(argv[2 + axis]);
    params.tileWidth = params.tileHeight = number(argv[5]);
    need(params.tileWidth > 0, "tile world dimension must be positive");
    const int count = argc - 12;
    std::vector<std::vector<unsigned char>> data;
    data.reserve(count);
    std::set<std::pair<int,int>> coordinates;
    std::uint64_t bytes_total = 0;
    int largest_poly_count = 0;
    dtMeshHeader first{};
    for (int arg = 12; arg < argc; ++arg) {
        data.push_back(load_tile(argv[arg]));
        bytes_total += data.back().size();
        need(bytes_total <= 256 * 1024 * 1024, "tile collection exceeds 256 MiB diagnostic limit");
        dtMeshHeader h{};
        std::memcpy(&h, data.back().data(), sizeof(h));
        need(h.layer == 0 && h.x >= 0 && h.y >= 0 && h.x <= 4095 && h.y <= 4095,
             "unsupported tile coordinate or layer");
        need(coordinates.emplace(h.x, h.y).second, "duplicate tile coordinates");
        const double tolerance = std::max(0.00001, double(params.tileWidth) * 0.00001);
        for (int dimension = 0; dimension < 2; ++dimension) {
            const int axis = dimension == 0 ? 0 : 2;
            const int index = dimension == 0 ? h.x : h.y;
            const double lower = double(params.orig[axis]) + index * double(params.tileWidth);
            need(std::abs(double(h.bmin[axis]) - lower) <= tolerance &&
                 std::abs(double(h.bmax[axis]) - (lower + params.tileWidth)) <= tolerance,
                 "tile bounds disagree with the declared collection grid");
        }
        if (arg == 12) first = h;
        need(h.bmin[1] == first.bmin[1] && h.bmax[1] == first.bmax[1] &&
             h.walkableHeight == first.walkableHeight && h.walkableRadius == first.walkableRadius &&
             h.walkableClimb == first.walkableClimb && h.bvQuantFactor == first.bvQuantFactor,
             "tile collection has mixed vertical bounds or agent settings");
        largest_poly_count = std::max(largest_poly_count, h.polyCount);
    }
    params.maxTiles = 1;
    while (params.maxTiles < count) params.maxTiles *= 2;
    params.maxPolys = 1;
    while (params.maxPolys < largest_poly_count) {
        need(params.maxPolys < (1 << 20), "tile polygon count exceeds diagnostic capacity");
        params.maxPolys *= 2;
    }
    dtNavMesh mesh;
    need(dtStatusSucceed(mesh.init(&params)), "Detour reference allocation cannot fit this tile collection");
    for (auto& bytes : data)
        need(dtStatusSucceed(mesh.addTile(bytes.data(), static_cast<int>(bytes.size()), 0, 0, nullptr)),
             "Detour rejected a collection tile");
    query_mesh(mesh, argv + 6, count);
}

unsigned short flag_mask(const char* text, bool include) {
    need(*text, "empty navigation flag mask");
    for (const char* p = text; *p; ++p) need(*p >= '0' && *p <= '9', "flag masks must be decimal unsigned integers");
    return static_cast<unsigned short>(integer(text, include ? 1 : 0, 65535));
}

void query_map(int argc, char** argv) {
    need(argc >= 13 && argc <= 1036,
         "query-map requires profile map-params include-flags exclude-flags sx sy sz ex ey ez and 1..1024 raw tiles");
    const std::string profile = argv[2];
    const bool cmangos64 = profile == "cmangos-v8-ref64";
    const unsigned int bits = profile == "cmangos-v8" ? 32 : 64;
    need(profile == "cmangos-v8" || cmangos64 || profile == "acore-v20", "unsupported imported navigation profile");
    need(sizeof(dtPolyRef) * 8 == bits, "import profile reference ABI differs from this backend");
    const uint16_t endian = 1;
    need(*reinterpret_cast<const unsigned char*>(&endian) == 1 && sizeof(dtNavMeshParams) == 28 && sizeof(dtMeshHeader) == 100,
         "imported navigation requires the known little-endian native layouts");
    const unsigned short include = flag_mask(argv[4], true), exclude = flag_mask(argv[5], false);
    need((include & ~exclude) != 0, "navigation flags exclude the entire included set");
    dtNavMeshParams params{};
    std::ifstream input(argv[3], std::ios::binary | std::ios::ate);
    need(bool(input) && input.tellg() == std::streamoff(sizeof(params)), "map parameters must be exactly 28 bytes");
    input.seekg(0);
    input.read(reinterpret_cast<char*>(&params), sizeof(params));
    need(bool(input), "map parameter read failed");
    for (float value : params.orig) need(bounded_coordinate(value), "invalid imported map origin");
    need(std::isfinite(params.tileWidth) && std::isfinite(params.tileHeight) &&
         params.tileWidth >= 1 && params.tileHeight >= 1 &&
         params.tileWidth <= 10000000 && params.tileHeight <= 10000000,
         "imported map dimensions are outside diagnostic limits (1..10000000)");
    need(params.maxTiles > 0 && params.maxTiles <= 4096, "imported original map capacity exceeds 1..4096 diagnostic limit");
    std::uint32_t polygon_bits = 0;
    std::memcpy(&polygon_bits, &params.maxPolys, sizeof(polygon_bits));
    need(params.maxPolys > 0 || (cmangos64 && polygon_bits == 0x80000000u),
         "invalid imported maximum polygon count for profile");
    if (bits == 32) {
        auto needed_bits = [](std::uint32_t count) {
            unsigned int result = 0;
            for (std::uint64_t capacity = 1; capacity < count; capacity *= 2) ++result;
            return result;
        };
        need(needed_bits(params.maxTiles) + needed_bits(polygon_bits) <= 22,
             "imported map exceeds 32-bit Detour reference capacity");
    }
    const int count = argc - 12;
    need(count <= params.maxTiles, "selected tile count exceeds original map capacity");
    std::vector<std::vector<unsigned char>> data;
    data.reserve(count);
    std::set<std::pair<int,int>> coordinates;
    std::uint64_t total = 0;
    for (int arg = 12; arg < argc; ++arg) {
        data.push_back(load_tile(argv[arg]));
        total += data.back().size();
        need(total <= 256 * 1024 * 1024, "imported selected set exceeds 256 MiB diagnostic limit");
        validate_import_tile(data.back());
        const auto h = item<dtMeshHeader>(data.back(), 0);
        need(coordinates.emplace(h.x, h.y).second, "duplicate imported tile coordinates");
        for (int dimension = 0; dimension < 2; ++dimension) {
            const int axis = dimension == 0 ? 0 : 2;
            const int index = dimension == 0 ? h.x : h.y;
            const double side = dimension == 0 ? params.tileWidth : params.tileHeight;
            const double lower = double(params.orig[axis]) + index * side;
            const double tolerance = std::max(0.00001, side * 0.00001);
            need(std::abs(double(h.bmin[axis]) - lower) <= tolerance &&
                 std::abs(double(h.bmax[axis]) - (lower + side)) <= tolerance,
                 "imported tile bounds disagree with original map grid");
        }
    }
    dtNavMesh mesh;
    need(dtStatusSucceed(mesh.init(&params)), "Detour rejected original imported map parameters");
    for (auto& bytes : data)
        need(dtStatusSucceed(mesh.addTile(bytes.data(), static_cast<int>(bytes.size()), 0, 0, nullptr)),
             "Detour rejected an imported tile");
    query_mesh(mesh, argv + 6, count, include, exclude, argv[2]);
}
}

int main(int argc,char** argv) {
    try {
        if (argc == 1 || (argc == 2 && std::string(argv[1]) == "--help")) {
            std::cout << "bnav-recast 0.1.0 - offline Recast/Detour backend\n"
                      << "Use through bnav-extract build-obj, or:\n"
                      << "  bnav-recast build-tiles CS CH HEIGHT RADIUS CLIMB SLOPE OX OZ MINY MAXY CELLS X0 Z0 [X1 Z1 ...]\n"
                      << "    Batch IPC via bnav-extract: BNBT v1 records, 1..16 cells; require final BEND footer.\n"
                      << "  bnav-recast query TILE sx sy sz ex ey ez\n"
                      << "  bnav-recast query-tiles ox oy oz tile-world sx sy sz ex ey ez TILE...\n"
                      << "  bnav-recast query-map PROFILE MAP_PARAMS INCLUDE_FLAGS EXCLUDE_FLAGS sx sy sz ex ey ez RAW_TILE...\n"
                      << "Coordinates: Y up; agent settings use the same world units as geometry.\n"
                      << "query/query-tiles accept this helper's generated tiles with matching ABI.\n"
                      << "query-map accepts trusted imported raw tiles with explicit profile/flags; selected-set scope only.\n";
            return 0;
        }
        if (argc == 2 && std::string(argv[1]) == "--version") {
            std::cout << "bnav-recast 0.1.0 detour=" << DT_NAVMESH_VERSION
                      << " reference_bits=" << sizeof(dtPolyRef) * 8 << '\n';
            return 0;
        }
        need(argc>=2,"use build or query; see docs/BNAV_EXTRACT.md");
        if (std::string(argv[1])=="build") build(argc,argv);
        else if (std::string(argv[1])=="build-tile") build(argc,argv,true);
        else if (std::string(argv[1])=="build-tiles") build_tiles(argc,argv);
        else if (std::string(argv[1])=="query") query(argc,argv);
        else if (std::string(argv[1])=="query-tiles") query_tiles(argc,argv);
        else if (std::string(argv[1])=="query-map") query_map(argc,argv);
        else throw std::runtime_error("unknown backend command");
        return 0;
    } catch(const EmptyTile& error) {
        std::cerr << "bnav-recast: empty_tile=" << error.what() << '\n';
        return 3;
    } catch(const std::exception& error) {
        std::cerr << "bnav-recast: " << error.what() << '\n';
        return 2;
    }
}
