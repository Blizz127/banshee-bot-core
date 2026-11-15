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

void build(int argc, char** argv, bool tiled = false) {
    need(argc == (tiled ? 15 : 8), "build requires six settings; build-tile also requires origin-x origin-z min-y max-y tile-cells tile-x tile-z");
    const float cs = number(argv[2]), ch = number(argv[3]);
    const float height = number(argv[4]), radius = number(argv[5]);
    const float climb = number(argv[6]), slope = number(argv[7]);
    need(cs > 0 && ch > 0 && height > 0 && radius >= 0 && climb >= 0 && slope >= 0 && slope < 90,
         "invalid agent or voxel configuration");
    need(height / ch >= 3 && height / ch <= 8191 && radius / cs <= 1024 && climb / ch <= 8191,
         "agent dimensions exceed supported voxel limits (height must span at least three cells)");
    const auto g = read_geometry();
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
    auto solid = std::unique_ptr<rcHeightfield, decltype(&rcFreeHeightField)>(rcAllocHeightfield(), rcFreeHeightField);
    need(bool(solid), "heightfield allocation failed");
    need(rcCreateHeightfield(&context, *solid, config.width, config.height, config.bmin, config.bmax, cs, ch),
         "heightfield creation failed");
    std::vector<unsigned char> areas(nt, RC_NULL_AREA);
    rcMarkWalkableTriangles(&context, slope, g.vertices.data(), nv, g.triangles.data(), nt, areas.data());
    need(rcRasterizeTriangles(&context, g.vertices.data(), nv, g.triangles.data(), areas.data(), nt,
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
    std::cout.write(reinterpret_cast<const char*>(header), sizeof(header));
    std::cout.write(reinterpret_cast<const char*>(data), size);
    need(bool(std::cout), "output write failed");
    std::cerr << "recast_build=PASS detour_reload=PASS reference_bits=" << sizeof(dtPolyRef) * 8
              << " polygons=" << polygons->npolys << " vertices=" << polygons->nverts
              << " grid=" << config.width << 'x' << config.height << " bytes=" << size
              << " tile=" << tile_x << ',' << tile_z << " border_cells=" << config.borderSize << '\n';
}

// Query only tiles generated by this helper and the matching reference ABI.
// This is a local diagnostic, not an untrusted-file server loader.
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

void query_mesh(dtNavMesh& mesh, char** positions, int loaded_tiles) {
    dtNavMeshQuery q;
    need(dtStatusSucceed(q.init(&mesh, 2048)), "query initialization failed");
    const float requested_start[]{number(positions[0]),number(positions[1]),number(positions[2])};
    const float requested_end[]{number(positions[3]),number(positions[4]),number(positions[5])};
    const float extents[]{2,4,2};
    dtPolyRef start_ref=0, end_ref=0;
    float start[3]{},end[3]{};
    dtQueryFilter filter;
    filter.setIncludeFlags(1);
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
    std::cout << "{\"complete\":true,\"reference_bits\":" << sizeof(dtPolyRef)*8
              << ",\"loaded_tiles\":" << loaded_tiles << ",\"traversed_tiles\":" << traversed.size()
              << ",\"corridor_polygons\":" << corridor_count << ",\"direct_path_blocked\":"
              << (direct_fraction < 1 ? "true" : "false") << ",\"points\":[";
    for (int i=0;i<point_count;++i) {
        if (i) std::cout << ',';
        std::cout << '[' << points[3*i] << ',' << points[3*i+1] << ',' << points[3*i+2] << ']';
    }
    std::cout << "]}\n";
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
}

int main(int argc,char** argv) {
    try {
        if (argc == 1 || (argc == 2 && std::string(argv[1]) == "--help")) {
            std::cout << "bnav-recast 0.1.0 - offline Recast/Detour backend\n"
                      << "Use through bnav-extract build-obj, or:\n"
                      << "  bnav-recast query TILE sx sy sz ex ey ez\n"
                      << "  bnav-recast query-tiles ox oy oz tile-world sx sy sz ex ey ez TILE...\n"
                      << "Coordinates: Y up; agent settings use the same world units as geometry.\n"
                      << "Only query this helper's generated tiles, using the matching reference ABI.\n";
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
        else if (std::string(argv[1])=="query") query(argc,argv);
        else if (std::string(argv[1])=="query-tiles") query_tiles(argc,argv);
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
