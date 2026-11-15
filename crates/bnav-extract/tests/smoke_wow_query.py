#!/usr/bin/env python3
"""Offline selected-tile query smoke using two pinned owner cMaNGOS tiles.

No discovery or server access. Extracted payloads and invalid negative controls
stay in a new evidence directory outside Git. A pass does not certify map-wide
coverage, game walkability, or off-mesh traversal (these samples have none).
"""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import stat
import struct
import subprocess
import sys


SAMPLES = {
    '509.mmap': (28, 'fd0aa67e62541bb9f1bc3259c5bc60a0f6e97594091dba3aad42975f7d7de528'),
    '5094627.mmtile': (353612, '80557e38c00386dde3e48ee04fff5a9a5bb9c33fe792d1467dd21c96abaf02ae'),
    '5094628.mmtile': (1654364, 'f1e67ad079ca17d9b2f2d0cfc6df54f91051c34bb48ce0bb8fcdbdfe03d9ba25'),
}
PROFILE = 'cmangos-v8-ref64'
CST = timezone(timedelta(hours=-6), name='CST')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def snapshot(path, limit):
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_size <= limit,
            f'not a bounded regular file: {path}')
    with path.open('rb') as source:
        data = source.read(limit + 1)
    after = path.stat()
    require(len(data) <= limit and len(data) == after.st_size
            and (before.st_size, before.st_mtime_ns, before.st_ino, before.st_dev)
            == (after.st_size, after.st_mtime_ns, after.st_ino, after.st_dev),
            f'file changed during bounded read: {path}')
    return data, {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                  'mtime_ns': after.st_mtime_ns}


def decode_tile(wrapped):
    wrapper = struct.unpack_from('<5I', wrapped)
    require(wrapper[:3] == (0x4d4d4150, 7, 8) and wrapper[3] == len(wrapped) - 20
            and wrapper[4] == 1, 'unexpected pinned v8 tile wrapper')
    data = wrapped[20:]
    header = struct.unpack_from('<15i10f', data)
    require(header[:2] == (0x444e4156, 7) and header[13] == 0, 'unexpected Detour header or offmesh sample')
    counts = [header[i] for i in (7, 6, 8, 9, 10, 11, 12, 13)]
    names = ('vertices', 'polygons', 'links', 'detail_meshes', 'detail_vertices',
             'detail_triangles', 'bv_nodes', 'offmesh_connections')
    sections, offset = {}, 100
    for name, count, stride in zip(names, counts, (12, 32, 16, 12, 12, 4, 16, 36)):
        size = (count * stride + 3) & ~3
        sections[name] = {'offset': offset, 'count': count, 'stride': stride, 'bytes': size}
        offset += size
    require(offset == len(data), 'sample does not have the documented 64-bit section sizes')
    vertices = [struct.unpack_from('<3f', data, sections['vertices']['offset'] + i * 12)
                for i in range(header[7])]
    polygons = [struct.unpack_from('<I12HHBB', data, sections['polygons']['offset'] + i * 32)
                for i in range(header[6])]
    return {'raw': data, 'header': header, 'sections': sections,
            'vertices': vertices, 'polygons': polygons}


def source_anchor(tile, polygon_id):
    """XZ vertex mean, with Y from the containing original detail triangle."""
    polygon = tile['polygons'][polygon_id]
    require(polygon[13] == 1 and polygon[15] >> 6 == 0, 'anchor is not a flags-1 ground polygon')
    indices = polygon[1:1 + polygon[14]]
    vertices = [tile['vertices'][index] for index in indices]
    mean = [sum(vertex[axis] for vertex in vertices) / len(vertices) for axis in range(3)]
    section = tile['sections']
    detail = struct.unpack_from('<IIBB', tile['raw'], section['detail_meshes']['offset'] + polygon_id * 12)
    detail_vertices = [struct.unpack_from('<3f', tile['raw'],
                       section['detail_vertices']['offset'] + (detail[0] + i) * 12)
                       for i in range(detail[2])]
    all_vertices = vertices + detail_vertices
    for i in range(detail[3]):
        triangle_index = detail[1] + i
        triangle = struct.unpack_from('<4B', tile['raw'], section['detail_triangles']['offset'] + triangle_index * 4)
        a, b, c = [all_vertices[index] for index in triangle[:3]]
        denominator = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if abs(denominator) < 1e-10:
            continue
        u = ((b[2] - c[2]) * (mean[0] - c[0]) + (c[0] - b[0]) * (mean[2] - c[2])) / denominator
        v = ((c[2] - a[2]) * (mean[0] - c[0]) + (a[0] - c[0]) * (mean[2] - c[2])) / denominator
        w = 1 - u - v
        if min(u, v, w) >= -1e-8:
            return {'polygon_index_zero_based': polygon_id, 'flags': polygon[13],
                    'area': polygon[15] & 63, 'vertex_indices': list(indices), 'vertices': vertices,
                    'vertex_mean': mean, 'requested_xyz': [mean[0], u*a[1] + v*b[1] + w*c[1], mean[2]],
                    'detail_triangle_index': triangle_index, 'detail_triangle_vertices': [a, b, c],
                    'detail_triangle_local_indices': list(triangle[:3]), 'barycentric': [u, v, w]}
    raise ValueError('anchor XZ does not lie in an original detail triangle')


def ground_component(tile, seed):
    pending, members, portals = [seed], {seed}, []
    while pending:
        index = pending.pop()
        polygon = tile['polygons'][index]
        for edge, neighbor in enumerate(polygon[7:7 + polygon[14]]):
            if neighbor & 0x8000:
                portals.append([index, edge, neighbor & 0xff])
            elif neighbor and neighbor - 1 not in members:
                candidate = tile['polygons'][neighbor - 1]
                if candidate[13] & 1 and candidate[15] >> 6 == 0:
                    members.add(neighbor - 1)
                    pending.append(neighbor - 1)
    return {'polygons': sorted(members), 'external_portals': portals}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bnav', required=True, type=Path)
    parser.add_argument('--backend', required=True, type=Path, help='64-bit-reference native backend')
    parser.add_argument('--backend32', type=Path, help='optional 32-bit-reference backend refusal check')
    parser.add_argument('--data-root', required=True, type=Path)
    parser.add_argument('--evidence-dir', required=True, type=Path)
    args = parser.parse_args()
    try:
        data_root, evidence = args.data_root.resolve(strict=True), args.evidence_dir.resolve()
        binaries = {'bnav': args.bnav.resolve(strict=True), 'backend': args.backend.resolve(strict=True)}
        if args.backend32:
            binaries['backend32'] = args.backend32.resolve(strict=True)
        require(data_root.is_dir(), 'data root is not a directory')
        require(evidence != data_root and data_root not in evidence.parents, 'evidence must be outside input data root')
        require(not any((directory / '.git').exists() for directory in (evidence, *evidence.parents)),
                'evidence with extracted game payloads must be outside Git')
        evidence.mkdir(parents=True, exist_ok=False)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    receipt = {'schema': 'banshee-wow-query-smoke-v1', 'started_cst': datetime.now(CST).isoformat(),
               'verdict': 'FAIL', 'scope': 'offline selected owner tiles, native Detour query',
               'whole_map_coverage': False, 'game_qa': 'NOT_RUN', 'offmesh_traversal': 'NOT_SAMPLED',
               'test_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'data_root': str(data_root), 'binaries': {}, 'inputs': {}, 'extracted': {},
               'anchors': {}, 'commands': [], 'negative_controls': [], 'failures': []}

    def run(label, argv, expected=0, reason=None):
        record = {'label': label, 'argv': list(map(str, argv)), 'expected_exit_code': expected,
                  'expected_stderr_fragment': reason}
        try:
            result = subprocess.run(record['argv'], capture_output=True, text=True,
                                    encoding='utf-8', errors='replace', timeout=30)
            record.update(exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)
            record['passed'] = (result.returncode == expected
                                and (not result.stdout if expected else not result.stderr)
                                and (reason is None or reason in result.stderr))
        except subprocess.TimeoutExpired as error:
            text = lambda value: value.decode('utf-8', errors='replace') if isinstance(value, bytes) else value or ''
            record.update(exit_code=None, stdout=text(error.stdout), stderr=text(error.stderr),
                          error='command exceeded 30 seconds', passed=False)
        except OSError as error:
            record.update(exit_code=None, stdout='', stderr='', error=str(error), passed=False)
        receipt['commands'].append(record)
        if not record['passed']:
            receipt['failures'].append(f'unexpected command result: {label}')
        return record

    try:
        for name, path in binaries.items():
            _, identity = snapshot(path, 128 * 1024 * 1024)
            receipt['binaries'][name] = {'path': str(path), 'before': identity}
        inputs = {}
        for name, (size, digest) in SAMPLES.items():
            path = data_root / name
            require(path.resolve(strict=True).parent == data_root, 'sample escaped explicit data root')
            inputs[name], identity = snapshot(path, size)
            receipt['inputs'][name] = {'path': str(path), 'before': identity}
            require((identity['bytes'], identity['sha256']) == (size, digest), f'pinned sample identity differs: {name}')
        require(struct.unpack('<5fII', inputs['509.mmap'])[-2:] == (40, 0x80000000), 'unexpected map capacity')
        tile_names = ['5094627.mmtile', '5094628.mmtile']
        tiles = [decode_tile(inputs[name]) for name in tile_names]
        require([tile['header'][2:5] for tile in tiles] == [(3, 7, 0), (2, 7, 0)], 'unexpected tile grid')
        for name, tile in zip(tile_names, tiles):
            receipt['inputs'][name]['decoded'] = {
                'grid': tile['header'][2:5], 'bounds_min': tile['header'][18:21],
                'bounds_max': tile['header'][21:24], 'sections': tile['sections'],
                'polygon_flags_counts': dict(Counter(polygon[13] for polygon in tile['polygons']))}
            require(not any(polygon[13] & 4 for polygon in tile['polygons']), 'water-only refusal assumption changed')
        anchors = {'start': source_anchor(tiles[0], 1787), 'end': source_anchor(tiles[1], 8812),
                   'disconnected': source_anchor(tiles[0], 1947)}
        receipt['anchors'] = anchors
        isolated = ground_component(tiles[0], 1947)
        require(len(isolated['polygons']) == 66 and not isolated['external_portals']
                and 1787 not in isolated['polygons'], 'disconnected source component assumption changed')
        receipt['disconnected_component'] = isolated
        raw_paths = []
        for name, tile in zip(tile_names, tiles):
            destination = evidence / (name + '.raw-detour')
            result = run('extract-' + name, [binaries['bnav'], 'extract-mmtile', PROFILE, data_root / name, destination])
            require(result['passed'], f'extraction failed: {name}')
            raw, identity = snapshot(destination, len(tile['raw']))
            require(raw == tile['raw'], 'extraction did not preserve exact original payload')
            receipt['extracted'][name] = {'path': str(destination), 'before': identity,
                                          'exact_original_payload': True}
            raw_paths.append(destination)

        start, end, disconnected = [anchors[name]['requested_xyz'] for name in ('start', 'end', 'disconnected')]

        def query(label, expected=0, origin=start, target=end, selected=None, include=1, exclude=0,
                  backend=None, reason=None):
            return run(label, [backend or binaries['backend'], 'query-map', PROFILE,
                              data_root / '509.mmap', include, exclude, *origin, *target,
                              *(raw_paths if selected is None else selected)], expected, reason)

        def successful_query(label, origin, target):
            record = query(label, origin=origin, target=target)
            require(record['passed'], f'{label} command failed')
            result = json.loads(record['stdout'])
            require(result.get('complete') is True and result.get('scope') == 'selected-tiles'
                    and result.get('whole_map_coverage') is False and result.get('profile') == PROFILE,
                    f'{label} omitted selected-tile scope or completeness')
            require((result.get('reference_bits'), result.get('include_flags'), result.get('exclude_flags'),
                     result.get('loaded_tiles'), result.get('traversed_tiles')) == (64, 1, 0, 2, 2),
                    f'{label} did not traverse both tiles with expected flags and ABI')
            for key, wanted in [('requested_start', origin), ('requested_end', target),
                                ('snapped_start', origin), ('snapped_end', target)]:
                point = result.get(key, [])
                require(len(point) == 3 and all(math.isfinite(v) for v in point)
                        and math.dist(point, wanted) < 0.01, f'{label} has unexpected {key}')
            points = result.get('points', [])
            require(len(points) >= 2 and math.dist(points[0], result['snapped_start']) < 0.01
                    and math.dist(points[-1], result['snapped_end']) < 0.01,
                    f'{label} path endpoints differ from snapped endpoints')
            record['decoded_query'] = result

        successful_query('cross-tile-forward', start, end)
        successful_query('cross-tile-reverse', end, start)
        query('missing-end-tile', 2, selected=[raw_paths[0]], reason='requested endpoint tile is not in the selected set')
        query('missing-start-tile', 2, selected=[raw_paths[1]], reason='requested endpoint tile is not in the selected set')
        query('disconnected-original-ground-component', 2, target=disconnected, reason='no complete path within query budget')
        query('water-only-flags-refusal', 2, include=4, reason='start has no nearby polygon')
        query('include-exclude-cancel-refusal', 2, include=1, exclude=1,
              reason='navigation flags exclude the entire included set')
        query('zero-include-refusal', 2, include=0)
        query('include-overflow-refusal', 2, include=65536)
        query('negative-exclude-refusal', 2, exclude=-1)
        query('duplicate-tile-refusal', 2, selected=[raw_paths[0], raw_paths[0], raw_paths[1]],
              reason='duplicate imported tile coordinates')
        query('nonfinite-coordinate-refusal', 2, origin=['NaN', start[1], start[2]], reason='expected finite numeric argument')
        query('tile-count-limit-refusal', 2, selected=[raw_paths[0]] * 1025, reason='1..1024 raw tiles')
        if 'backend32' in binaries:
            query('32-bit-backend-refusal', 2, backend=binaries['backend32'],
                  reason='import profile reference ABI differs from this backend')

        tile = tiles[0]
        sections = tile['sections']
        bv_index = next(i for i in range(sections['bv_nodes']['count'])
                        if struct.unpack_from('<i', tile['raw'], sections['bv_nodes']['offset'] + i*16 + 12)[0] < 0)
        mutations = [
            ('polygon-vertex-index', sections['polygons']['offset'] + 1787*32 + 4, '<H', tile['header'][7],
             'imported polygon vertex index is out of bounds'),
            ('detail-local-vertex-index', sections['detail_triangles']['offset']
             + anchors['start']['detail_triangle_index']*4, '<B', 255,
             'imported detail triangle index is out of bounds'),
            ('bv-escape-index', sections['bv_nodes']['offset'] + bv_index*16 + 12, '<i',
             -(sections['bv_nodes']['count'] + 1), 'imported BV escape index is out of bounds'),
            ('offmesh-partition-index', 56, '<i', tile['header'][6] + 1, 'invalid tile polygon partition'),
        ]
        for label, offset, encoding, replacement, reason in mutations:
            mutated = bytearray(tile['raw'])
            old = struct.unpack_from(encoding, mutated, offset)[0]
            struct.pack_into(encoding, mutated, offset, replacement)
            destination = evidence / ('invalid-' + label + '.raw-detour')
            with destination.open('xb') as output:
                output.write(mutated)
            receipt['negative_controls'].append({'label': label, 'path': str(destination),
                'source': tile_names[0], 'offset': offset, 'encoding': encoding,
                'old_value': old, 'replacement': replacement, 'bytes': len(mutated),
                'sha256': hashlib.sha256(mutated).hexdigest(), 'intentionally_invalid': True})
            query(label + '-refusal', 2, selected=[destination, raw_paths[1]], reason=reason)
    except (OSError, ValueError, KeyError, IndexError, StopIteration, struct.error) as error:
        receipt['failures'].append(str(error) or type(error).__name__)
    finally:
        identities = [(entry, 128 * 1024 * 1024) for entry in receipt['binaries'].values()]
        identities += [(entry, SAMPLES[name][0]) for name, entry in receipt['inputs'].items()]
        identities += [(entry, SAMPLES[name][0] - 20) for name, entry in receipt['extracted'].items()]
        for entry, limit in identities:
            try:
                _, entry['after'] = snapshot(Path(entry['path']), limit)
                entry['unchanged_after_inspection'] = entry['after'] == entry['before']
                if not entry['unchanged_after_inspection']:
                    receipt['failures'].append(f'input identity changed: {entry["path"]}')
            except (OSError, ValueError) as error:
                receipt['failures'].append(str(error))

    if not receipt['failures']:
        receipt['verdict'] = 'PASS'
    receipt['finished_cst'] = datetime.now(CST).isoformat()
    output = evidence / 'query-receipt.json'
    with output.open('x', encoding='utf-8') as destination:
        json.dump(receipt, destination, indent=2, allow_nan=False)
        destination.write('\n')
    print(json.dumps({'verdict': receipt['verdict'], 'receipt': str(output),
                      'commands': len(receipt['commands']), 'failures': receipt['failures'],
                      'game_qa': 'NOT_RUN', 'whole_map_coverage': False}))
    return 0 if receipt['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
