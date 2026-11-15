#!/usr/bin/env python3
"""Focused synthetic query-report smoke; no game assets or native compilation.

Supply matching-ABI retained seam-wall collection and long_corridor_fixture.cpp
output. The caller separately pins the generator's successful run, dependency,
and build. All commands run sequentially at nice 19. A fresh external directory
retains exact argv, stdout, stderr, input hashes and partial outputs on failure.
This tests diagnostics only: no gameplay, whole-map or adapter adoption claim.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import stat
import struct
import subprocess
import sys
import time


CST = timezone(timedelta(hours=-6), name='CST')
WALL_SECONDS = 45
CPU_SECONDS = 15
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_ADDRESS_BYTES = 512 * 1024 * 1024
ISLANDS_OBJ = b'''# Original disconnected synthetic floor, Y up, arbitrary source units.
v 0 0 0
v 8 0 0
v 8 0 20
v 0 0 20
v 12 0 0
v 20 0 0
v 20 0 20
v 12 0 20
f 1 3 2
f 1 4 3
f 5 7 6
f 5 8 7
'''


def need(condition, message):
    if not condition:
        raise ValueError(message)


def snapshot(path, limit=MAX_FILE_BYTES):
    before = path.stat()
    need(stat.S_ISREG(before.st_mode) and before.st_size <= limit,
         f'input is not a bounded regular file: {path}')
    with path.open('rb') as source:
        data = source.read(limit + 1)
    after = path.stat()
    identity = lambda value: (value.st_size, value.st_mtime_ns, value.st_ino, value.st_dev)
    need(len(data) <= limit and len(data) == after.st_size and identity(before) == identity(after),
         f'input changed during bounded read: {path}')
    return data, {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                  'mtime_ns': after.st_mtime_ns}


def child_limits():
    # These limits apply to this smoke's children only, including the backend
    # spawned by the extractor. Timeout handling targets only our process group.
    for kind, value in ((resource.RLIMIT_CPU, CPU_SECONDS),
                        (resource.RLIMIT_AS, MAX_ADDRESS_BYTES),
                        (resource.RLIMIT_FSIZE, MAX_FILE_BYTES),
                        (resource.RLIMIT_CORE, 0)):
        _, hard = resource.getrlimit(kind)
        bound = value if hard == resource.RLIM_INFINITY else min(value, hard)
        resource.setrlimit(kind, (bound, bound))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('backend', 'baseline-backend', 'extractor', 'collection', 'long-corridor', 'output-dir'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    try:
        output = args.output_dir.resolve()
        need(not any((ancestor / '.git').exists() for ancestor in (output, *output.parents)),
             'output must be outside Git')
        output.mkdir(parents=True, exist_ok=False)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    receipt = {'format': 'bnav-query-report-smoke-v1', 'verdict': 'FAIL',
               'started_cst': datetime.now(CST).isoformat(),
               'scope': 'synthetic local diagnostics, matching reference ABI only',
               'game_qa': 'NOT_RUN', 'node_exhaustion': 'NOT_EXERCISED',
               'straight_path_exhaustion': 'NOT_EXERCISED',
               'limits': {'wall_seconds_per_command': WALL_SECONDS,
                          'cpu_seconds_per_process': CPU_SECONDS,
                          'address_bytes_per_process': MAX_ADDRESS_BYTES,
                          'bytes_per_output_file': MAX_FILE_BYTES,
                          'nice': 19, 'commands_sequential': True},
               'load_average_before': list(os.getloadavg()),
               'inputs': {}, 'commands': [], 'checks': [], 'failures': []}
    pins = {}

    def pin(name, path, limit=MAX_FILE_BYTES):
        path = path.resolve(strict=True)
        data, identity = snapshot(path, limit)
        receipt['inputs'][name] = {'path': str(path), 'before': identity}
        pins[name] = (path, limit)
        return data

    def write_fixture(name, data):
        path = output / name
        with path.open('xb') as destination:
            destination.write(data)
        pin(name, path)
        return path

    def run(label, argv):
        index = len(receipt['commands'])
        record = {'label': label, 'argv': ['nice', '-n', '19', *map(str, argv)],
                  'cwd': str(output), 'exit_code': None, 'timed_out': False}
        receipt['commands'].append(record)
        stdout_path, stderr_path = [output / f'{index:02d}-{label}.{suffix}'
                                    for suffix in ('stdout', 'stderr')]
        started = time.monotonic()
        with stdout_path.open('xb') as stdout, stderr_path.open('xb') as stderr:
            child = subprocess.Popen(record['argv'], cwd=output, stdin=subprocess.DEVNULL,
                                     stdout=stdout, stderr=stderr, start_new_session=True,
                                     preexec_fn=child_limits)
            try:
                record['exit_code'] = child.wait(timeout=WALL_SECONDS)
            except subprocess.TimeoutExpired:
                record['timed_out'] = True
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                record['exit_code'] = child.wait()
        record['wall_seconds'] = time.monotonic() - started
        stdout, stdout_identity = snapshot(stdout_path)
        stderr, stderr_identity = snapshot(stderr_path)
        record.update(stdout={'path': str(stdout_path), **stdout_identity},
                      stderr={'path': str(stderr_path), **stderr_identity})
        need(not record['timed_out'], f'{label} exceeded wall limit')
        return record['exit_code'], stdout, stderr

    def check_report(label, mode, values, reason, stage):
        code, stdout, stderr = run(label, [backend, mode + '-report', *values])
        need(code == 3, f'{label}: expected typed refusal exit 3, got {code}')
        decoded = json.loads(stdout)
        expected = {'format': 'bnav-query-refusal-v1', 'complete': False,
                    'reference_bits': bits, 'reason': reason, 'stage': stage,
                    'node_limit': 2048, 'path_limit': 256, 'nearest_extents': [2, 4, 2]}
        need(decoded == expected and decoded.get('complete') is False
             and type(decoded.get('reference_bits')) is int
             and type(decoded.get('node_limit')) is int and type(decoded.get('path_limit')) is int
             and all(type(value) in (int, float) for value in decoded.get('nearest_extents', [])),
             f'{label}: refusal JSON differs from the exact schema')
        need(not stderr, f'{label}: typed refusal unexpectedly wrote stderr')
        receipt['checks'].append({'label': label, 'typed_refusal': decoded})

    def equivalence(label, mode, values, reason=None, stage=None, legacy_error=None):
        before = run(label + '-baseline', [baseline, mode, *values])
        after = run(label + '-legacy', [backend, mode, *values])
        need(before == after, f'{label}: legacy exit/stdout/stderr changed')
        if reason:
            need(after[0] == 2 and not after[1] and legacy_error.encode() in after[2],
                 f'{label}: unexpected legacy refusal')
            check_report(label + '-report', mode, values, reason, stage)
        else:
            need(after[0] == 0 and not after[2], f'{label}: legacy success failed')
            reported = run(label + '-report', [backend, mode + '-report', *values])
            need(reported == after, f'{label}: report success differs from legacy output')
            decoded = json.loads(reported[1])
            need(decoded.get('complete') is True and decoded.get('reference_bits') == bits,
                 f'{label}: success did not contain expected completeness/ABI')
            if mode != 'query':
                need(decoded.get('loaded_tiles') == 2 and decoded.get('traversed_tiles') == 2,
                     f'{label}: success did not traverse the retained seam')
            receipt['checks'].append({'label': label, 'successful_query': decoded})
        receipt['checks'].append({'label': label, 'legacy_byte_equivalence': True})

    def ordinary_error(label, mode, values, fragment, compare=False):
        if compare:
            before = run(label + '-baseline', [baseline, mode, *values])
            after = run(label + '-legacy', [backend, mode, *values])
            need(before == after, f'{label}: legacy invalid-input behavior changed')
        reported = run(label + '-report', [backend, mode + '-report', *values])
        need(reported[0] == 2 and not reported[1] and fragment.encode() in reported[2],
             f'{label}: invalid input was not an ordinary stderr-only exit 2')
        if compare:
            need(reported == after, f'{label}: invalid-input report differs from legacy')
        receipt['checks'].append({'label': label, 'ordinary_error_not_typed_refusal': True})

    try:
        backend, baseline, extractor = [path.resolve(strict=True) for path in
                                       (args.backend, args.baseline_backend, args.extractor)]
        for name, path in (('backend', backend), ('baseline_backend', baseline), ('extractor', extractor)):
            pin(name, path, 128 * 1024 * 1024)
        pin('runner', Path(__file__))
        collection = args.collection.resolve(strict=True)
        manifest = json.loads(pin('collection_manifest', collection / 'manifest.json'))
        need(manifest.get('format') in ('bnav-collection-v1', 'bnav-collection-batch-v1')
             and manifest.get('status') == 'COMPLETE' and manifest.get('game') == 'synthetic'
             and manifest.get('zone') == 'batch-collection-seam-wall',
             'requires the retained synthetic seam-wall collection')
        grid = manifest['grid']
        need(all(grid.get(key) == value for key, value in {
            'origin_x': -20, 'origin_z': -20, 'min_y': 0, 'max_y': 3,
            'tile_cells': 40, 'cell_size': .5, 'cell_height': .2,
            'x_min': 0, 'x_max': 1, 'z_min': 0, 'z_max': 1}.items()),
            'retained seam-wall grid differs from fixed smoke assumptions')
        built = sorted((tile for tile in manifest['tiles'] if tile['status'] == 'built'),
                       key=lambda tile: (tile['x'], tile['z']))
        need([(tile['x'], tile['z']) for tile in built] == [(0, 0), (1, 0)],
             'expected exactly two retained built seam-wall tiles')
        tiles = []
        for tile in built:
            path = (collection / tile['path']).resolve(strict=True)
            need(path.is_relative_to(collection), 'manifest tile escaped collection')
            name = f"collection_tile_{tile['x']}_{tile['z']}"
            pin(name, path)
            identity = receipt['inputs'][name]['before']
            need((identity['bytes'], identity['sha256']) == (tile['bytes'], tile['sha256']),
                 'retained tile identity differs from its manifest')
            tiles.append(path)
        corridor = args.long_corridor.resolve(strict=True)
        corridor_data = pin('long_corridor', corridor)
        need(len(corridor_data) >= 100 and struct.unpack_from('<2i', corridor_data) == (0x444e4156, 7)
             and struct.unpack_from('<2i', corridor_data, 24) == (300, 602),
             'expected the original 300-quad long-corridor fixture')
        versions = []
        for name, binary in (('backend', backend), ('baseline', baseline)):
            code, stdout, stderr = run(name + '-version', [binary, '--version'])
            match = re.search(rb'\breference_bits=(32|64)\b', stdout)
            need(code == 0 and not stderr and match is not None, f'{name} version/ABI failed')
            versions.append(int(match.group(1)))
        bits = versions[0]
        need(versions == [bits, bits] and manifest['reference_bits'] == bits,
             'backend, baseline and collection ABIs differ')
        receipt['reference_bits'] = bits
        profile = 'cmangos-v8' if bits == 32 else 'cmangos-v8-ref64'
        params = write_fixture('seam-map.params', struct.pack('<5f2i', -20, -.2, -20, 20, 20, 4, 128))
        start, nearby, end = [-18, 0, -10], [-10, 0, -10], [18, 0, -10]
        collection_values = [-20, -.2, -20, 20, *start, *end, *tiles]
        map_values = [profile, params, 1, 0, *start, *end, *tiles]
        equivalence('single-success', 'query', [tiles[0], *start, *nearby])
        equivalence('collection-success', 'query-tiles', collection_values)
        equivalence('selected-map-success', 'query-map', map_values)
        equivalence('missing-start', 'query', [tiles[0], -18, 100, -10, *nearby],
                    'START_POLYGON_NOT_FOUND', 'nearest_start', 'start has no nearby polygon')
        equivalence('missing-end', 'query', [tiles[0], *start, -10, 100, -10],
                    'END_POLYGON_NOT_FOUND', 'nearest_end', 'end has no nearby polygon')
        equivalence('path-buffer-exhaustion', 'query', [corridor, .5, 0, 2, 299.5, 0, 2],
                    'QUERY_BUDGET_EXCEEDED', 'find_path', 'no complete path within query budget')

        obj = write_fixture('disconnected.obj', ISLANDS_OBJ)
        islands = output / 'disconnected.navtile'
        code, _, _ = run('build-disconnected', [extractor, 'build-tile-obj', backend, obj, islands,
                                               0, 0, 0, 0, 40, 0, 0, .5, .2, 2, .6, .9, 45])
        need(code == 0, 'synthetic disconnected tile build failed')
        pin('disconnected_tile', islands)
        island_params = write_fixture('disconnected-map.params', struct.pack('<5f2i', 0, -.2, 0, 20, 20, 1, 128))
        anchors = [2, 0, 10, 18, 0, 10]
        equivalence('disconnected', 'query', [islands, *anchors],
                    'NO_COMPLETE_CORRIDOR', 'find_path', 'no complete path within query budget')
        check_report('disconnected-collection', 'query-tiles', [0, -.2, 0, 20, *anchors, islands],
                     'NO_COMPLETE_CORRIDOR', 'find_path')
        check_report('disconnected-selected-map', 'query-map', [profile, island_params, 1, 0, *anchors, islands],
                     'NO_COMPLETE_CORRIDOR', 'find_path')

        invalid = write_fixture('truncated.navtile', struct.pack('<2i', 0x444e4156, 7))
        ordinary_error('invalid-single', 'query', [invalid, *start, *nearby], 'invalid tile file size', compare=True)
        ordinary_error('invalid-collection', 'query-tiles', [-20, -.2, -20, 20, *start, *end, invalid],
                       'invalid tile file size')
        ordinary_error('invalid-selected-map', 'query-map', [profile, params, 1, 0, *start, *end, invalid],
                       'invalid tile file size')
        wrong_profile = 'cmangos-v8-ref64' if bits == 32 else 'cmangos-v8'
        ordinary_error('wrong-abi', 'query-map', [wrong_profile, *map_values[1:]],
                       'import profile reference ABI differs from this backend')
        ordinary_error('missing-selected-tile', 'query-map', [profile, params, 1, 0, *start, *end, tiles[0]],
                       'requested endpoint tile is not in the selected set')
        need(len(receipt['commands']) == 33, 'focused command matrix changed unexpectedly')
    except Exception as error:
        receipt['failures'].append(f'{type(error).__name__}: {error}')
    finally:
        for name, (path, limit) in pins.items():
            try:
                _, identity = snapshot(path, limit)
                receipt['inputs'][name]['after'] = identity
                need(identity == receipt['inputs'][name]['before'], f'pinned input changed: {name}')
            except (OSError, ValueError) as error:
                receipt['failures'].append(str(error))
        receipt['load_average_after'] = list(os.getloadavg())
        receipt['finished_cst'] = datetime.now(CST).isoformat()
        if not receipt['failures']:
            receipt['verdict'] = 'PASS'
        result = output / 'result.json'
        with result.open('x') as destination:
            json.dump(receipt, destination, indent=2)
            destination.write('\n')
        print(json.dumps({'verdict': receipt['verdict'], 'result': str(result),
                          'sha256': hashlib.sha256(result.read_bytes()).hexdigest(),
                          'commands': len(receipt['commands']), 'failures': receipt['failures']}))
    return 0 if receipt['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
