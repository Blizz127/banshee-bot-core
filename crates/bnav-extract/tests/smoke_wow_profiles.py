#!/usr/bin/env python3
"""Read-only preflight of two pinned owner cMaNGOS map/tile pairs.

This checks explicit ABI selection and tile placement, not paths or game QA.
Only the four named inputs are read. Receipts contain metadata and command
output; no map/tile payload is copied. Requires Python's standard library only.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import stat
import struct
import subprocess
import sys


# Identities from evidence/wow-nav-preflight-20261115/artifact-receipt.json.
# A changed sample needs a new, reviewed receipt; do not silently accept it.
SAMPLES = {
    '000.mmap': (28, '5bfae4cd801172511a7cb76fe64fed4df7814afa4bf97c6e3d214e2da1152609'),
    '0002239.mmtile': (109128, '26084d182f4cf1053f6007a0bff645fdfcb273287883616f54825ec7c5181776'),
    '509.mmap': (28, 'fd0aa67e62541bb9f1bc3259c5bc60a0f6e97594091dba3aad42975f7d7de528'),
    '5094627.mmtile': (353612, '80557e38c00386dde3e48ee04fff5a9a5bb9c33fe792d1467dd21c96abaf02ae'),
}
PAIRS = [('000.mmap', '0002239.mmtile', 687, (5, 39, 0), 673, 741),
         ('509.mmap', '5094627.mmtile', 40, (3, 7, 0), 1996, 2490)]
CST = timezone(timedelta(hours=-6), name='CST')


def timestamp():
    return datetime.now(CST).isoformat()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def snapshot(path, limit):
    """Bound reads and reject a size/mtime change during the hash operation."""
    before = path.stat()
    require(stat.S_ISREG(before.st_mode), f'not a regular file: {path}')
    require(before.st_size <= limit, f'input exceeds bounded size: {path}')
    with path.open('rb') as source:
        data = source.read(limit + 1)
    after = path.stat()
    require(len(data) <= limit, f'input grew beyond bounded size: {path}')
    require((before.st_size, before.st_mtime_ns, before.st_ino, before.st_dev)
            == (after.st_size, after.st_mtime_ns, after.st_ino, after.st_dev)
            and len(data) == after.st_size, f'input changed during read: {path}')
    return data, {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                  'mtime_ns': after.st_mtime_ns}


def decode_pair(map_data, tile_data, max_tiles, coordinates, polygons, vertices):
    origin_x, origin_y, origin_z, width, height, tiles, poly_bits = struct.unpack('<5fII', map_data)
    require(poly_bits == 0x80000000, 'unexpected map maxPolys bit pattern')
    require(tiles == max_tiles, 'unexpected map maximum tile count')
    require(all(math.isfinite(v) for v in (origin_x, origin_y, origin_z, width, height))
            and width > 0 and height > 0, 'invalid map grid')
    mmap = {'origin': [origin_x, origin_y, origin_z], 'tile_width': width,
            'tile_height': height, 'max_tiles_raw_u32': tiles,
            'max_polys_raw_u32': poly_bits, 'max_polys_i32': -2147483648}
    magic, version, wrapper_version, payload_bytes, liquids = struct.unpack_from('<5I', tile_data)
    require((magic, version, wrapper_version, liquids) == (0x4d4d4150, 7, 8, 1),
            'unexpected cMaNGOS wrapper header')
    require(payload_bytes == len(tile_data) - 20, 'wrapper payload byte count differs')
    header = struct.unpack_from('<15i10f', tile_data, 20)
    require(header[0:2] == (0x444e4156, 7), 'unexpected Detour header')
    require(header[2:5] == coordinates, 'unexpected Detour tile coordinates')
    require(header[6:8] == (polygons, vertices), 'unexpected Detour polygon/vertex counts')
    bmin, bmax = header[18:21], header[21:24]
    require(all(math.isfinite(v) for v in (*bmin, *bmax))
            and all(low <= high for low, high in zip(bmin, bmax)), 'invalid tile bounds')
    tile = {'magic_hex': hex(magic), 'detour_version': version,
            'mmap_version': wrapper_version, 'declared_payload_bytes': payload_bytes,
            'uses_liquids': liquids, 'coordinates': list(coordinates),
            'polygons': polygons, 'vertices': vertices,
            'bounds_min': list(bmin), 'bounds_max': list(bmax)}
    # A cell here is one map tile, not a Recast voxel. Stored tile indices, not
    # filename digits, establish placement against dtNavMeshParams.orig.
    expected = [origin_x + coordinates[0] * width,
                origin_x + (coordinates[0] + 1) * width,
                origin_z + coordinates[1] * height,
                origin_z + (coordinates[1] + 1) * height]
    observed = [bmin[0], bmax[0], bmin[2], bmax[2]]
    residuals = [abs(actual - wanted) / scale
                 for actual, wanted, scale in zip(observed, expected, [width, width, height, height])]
    placement = {'axes': ['x_min', 'x_max', 'z_min', 'z_max'],
                 'expected_world_bounds': expected, 'observed_world_bounds': observed,
                 'absolute_residual_tile_cells': residuals, 'tolerance_tile_cells': 0.001,
                 'passed': max(residuals) <= 0.001}
    return mmap, tile, placement


def run_command(argv, expected_exit, stdout_tokens=(), stderr_fragment=None):
    record = {'argv': list(map(str, argv)), 'expected_exit_code': expected_exit,
              'expected_stdout_tokens': list(stdout_tokens),
              'expected_stderr_fragment': stderr_fragment, 'timeout_seconds': 20}
    try:
        result = subprocess.run(record['argv'], capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=20)
        record.update(exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)
        tokens = set(result.stdout.split())
        record['passed'] = (result.returncode == expected_exit
                            and all(token in tokens for token in stdout_tokens)
                            and (stderr_fragment is None or stderr_fragment in result.stderr)
                            and (not result.stdout if expected_exit else not result.stderr))
    except subprocess.TimeoutExpired as error:
        def text(value):
            return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else value or ''
        record.update(exit_code=None, stdout=text(error.stdout), stderr=text(error.stderr),
                      error='command timed out', passed=False)
    except OSError as error:
        record.update(exit_code=None, stdout='', stderr='', error=str(error), passed=False)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bnav', type=Path, required=True, help='explicit bnav-extract binary')
    parser.add_argument('--data-root', type=Path, required=True, help='directory containing the four pinned files')
    parser.add_argument('--evidence-dir', type=Path, required=True, help='new directory; existing paths are refused')
    args = parser.parse_args()
    try:
        binary = args.bnav.resolve(strict=True)
        data_root = args.data_root.resolve(strict=True)
        evidence = args.evidence_dir.resolve()
        require(data_root.is_dir(), 'data root must be a directory')
        require(evidence != data_root and data_root not in evidence.parents,
                'evidence directory must be outside the input data root')
        evidence.mkdir(parents=True, exist_ok=False)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    receipt = {'schema': 'banshee-wow-profile-smoke-v1', 'started_cst': timestamp(),
               'verdict': 'FAIL', 'scope': 'read-only pinned artifact ABI and grid-placement preflight',
               'data_root': str(data_root), 'game_qa': 'NOT_RUN',
               'connectivity': 'NOT_VERIFIED', 'walkability': 'NOT_VERIFIED',
               'inspector': {'path': str(binary)}, 'artifacts': {}, 'pairs': [],
               'commands': [], 'failures': []}
    try:
        _, receipt['inspector']['before'] = snapshot(binary, 128 * 1024 * 1024)
        payloads = {}
        for name, (expected_size, expected_sha) in SAMPLES.items():
            path = data_root / name
            require(path.resolve(strict=True).parent == data_root,
                    f'sample resolves outside the explicit data root: {name}')
            payloads[name], before = snapshot(path, expected_size)
            receipt['artifacts'][name] = {'path': str(path), 'before': before,
                                          'expected_bytes': expected_size, 'expected_sha256': expected_sha}
            require((before['bytes'], before['sha256']) == (expected_size, expected_sha),
                    f'sample identity differs from observed receipt: {name}')

        for map_name, tile_name, tiles, coordinates, polygons, vertices in PAIRS:
            mmap, tile, placement = decode_pair(payloads[map_name], payloads[tile_name],
                                                 tiles, coordinates, polygons, vertices)
            receipt['artifacts'][map_name]['decoded_header'] = mmap
            receipt['artifacts'][tile_name]['decoded_header'] = tile
            receipt['pairs'].append({'map': map_name, 'tile': tile_name, 'placement': placement})
            if not placement['passed']:
                receipt['failures'].append(f'grid placement exceeds tolerance: {tile_name}')

            inspections = [
                (['inspect-mmap', 'cmangos-v8-ref64', data_root / map_name], 0,
                 ['profile=cmangos-v8-ref64', 'reference_bits=64', 'max_polygons=2147483648',
                  'max_polygons_semantics=fixed-31bit-capacity'], None),
                (['inspect-mmap', data_root / map_name], 2, [], 'invalid maximum polygon count'),
                (['inspect-mmtile', 'cmangos-v8-ref64', data_root / tile_name], 0,
                 ['profile=cmangos-v8-ref64', 'reference_bits=64', 'detour_version=7',
                  f'payload_bytes={tile["declared_payload_bytes"]}', f'polygons={polygons}',
                  f'vertices={vertices}', 'connectivity=unverified', 'walkability=unverified'], None),
                (['inspect-mmtile', 'cmangos-v8', data_root / tile_name], 2, [],
                 'Detour section lengths do not match selected ABI and payload size'),
                (['inspect-mmtile', 'acore-v20', data_root / tile_name], 2, [], 'version'),
            ]
            for arguments, expected_exit, tokens, fragment in inspections:
                command = run_command([binary, *arguments], expected_exit, tokens, fragment)
                receipt['commands'].append(command)
                if not command['passed']:
                    receipt['failures'].append(f'unexpected command result: {command["argv"]}')
    except (OSError, ValueError, struct.error) as error:
        receipt['failures'].append(str(error))
    finally:
        identities = [(binary, receipt['inspector'], 128 * 1024 * 1024)]
        identities += [(Path(entry['path']), entry, SAMPLES[name][0])
                       for name, entry in receipt['artifacts'].items()]
        for path, entry, limit in identities:
            try:
                _, entry['after'] = snapshot(path, limit)
                entry['unchanged_after_inspection'] = entry.get('before') == entry['after']
                if not entry['unchanged_after_inspection']:
                    receipt['failures'].append(f'identity changed during inspection: {path}')
            except (OSError, ValueError) as error:
                entry['unchanged_after_inspection'] = False
                receipt['failures'].append(f'after-inspection read failed: {error}')

    receipt['finished_cst'] = timestamp()
    if not receipt['failures']:
        receipt['verdict'] = 'PASS'
    output = evidence / 'artifact-receipt.json'
    with output.open('x', encoding='utf-8') as destination:
        json.dump(receipt, destination, indent=2, allow_nan=False)
        destination.write('\n')
    print(json.dumps({'verdict': receipt['verdict'], 'receipt': str(output),
                      'commands': len(receipt['commands']), 'failures': receipt['failures'],
                      'game_qa': 'NOT_RUN'}))
    return 0 if receipt['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
