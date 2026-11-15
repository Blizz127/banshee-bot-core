#!/usr/bin/env python3
"""Compare padded-X/Z triangle selection with an explicit unfiltered backend.

Seventeen bounded synthetic fixture/grid cases produce 34 paired bake commands,
two backend version checks and two seam-wall queries. No game assets or runtime.
All generated files stay in a new external directory; input tools, this script,
fixtures and successful raw tiles are fingerprinted before/after use.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import stat
import struct
import subprocess
import sys


SETTINGS = ['0.5', '0.25', '2', '0.5', '0.5', '45']
# Exact binary32 settings: 40 cells * .5 = 20 world units. Radius spans one
# cell; its three extra border cells make padding exactly 2 world units.
GRID = ['0', '0', '0', '3', '40', '0', '0']
PADDED_LOW, PADDED_HIGH = -2.0, 22.0
EXPECTED_CASES, EXPECTED_COMMANDS = 17, 38
CST = timezone(timedelta(hours=-6), name='CST')
SELECTION = re.compile(
    r'^triangle_selection=padded_xz input_triangles=(\d+) '
    r'candidate_triangles=(\d+) culled_triangles=(\d+)\s*$', re.MULTILINE)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fingerprint(path, limit):
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_size <= limit,
            f'not a bounded regular file: {path}')
    with path.open('rb') as source:
        data = source.read(limit + 1)
    after = path.stat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    require(identity(before) == identity(after) and len(data) == after.st_size
            and len(data) <= limit, f'input changed during fingerprint: {path}')
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'mtime_ns': after.st_mtime_ns, 'device': after.st_dev, 'inode': after.st_ino}


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def adjacent_f32(value, direction):
    """One binary32 neighbor, not Python float's much smaller binary64 ULP."""
    require(direction in (-1, 1) and value != 0 and f32(value) == value,
            'boundary must be a nonzero exactly representable binary32 value')
    bits = struct.unpack('<I', struct.pack('<f', value))[0]
    bits += direction if value > 0 else -direction
    result = struct.unpack('<f', struct.pack('<I', bits))[0]
    require(math.isfinite(result) and (result - value) * direction > 0,
            'binary32 neighbor did not move in the requested direction')
    return result


def floor(x0=-4, z0=-4, x1=24, z1=24):
    a, b, c, d = (x0, 0, z0), (x1, 0, z0), (x1, 0, z1), (x0, 0, z1)
    return [(a, c, b), (a, d, c)]


def wall(x, z0=5, z1=15):
    a, b, c, d = (x, 0, z0), (x, 3, z0), (x, 3, z1), (x, 0, z1)
    return [(a, b, c), (a, c, d)]


def distant(x=100, z=100, y=0):
    return ((x, y, z), (x, y, z + 1), (x + 1, y, z))


def fixtures():
    cases = []

    def add(name, triangles, candidates, grid=None, status=0, single=False, metadata=None):
        cases.append({'name': name, 'triangles': triangles, 'candidates': candidates,
                      'grid': list(GRID if grid is None else grid), 'status': status,
                      'single': single, 'metadata': metadata or {}})

    for axis in ('x', 'z'):
        for side, boundary, outward in [('low', PADDED_LOW, -1), ('high', PADDED_HIGH, 1)]:
            for kind, coordinate in [('touch', boundary), ('outside', adjacent_f32(boundary, outward))]:
                probe = (((coordinate, 0, 5), (coordinate, 3, 5), (coordinate, 0, 15))
                         if axis == 'x' else
                         ((5, 0, coordinate), (5, 3, coordinate), (15, 0, coordinate)))
                add(f'{axis}-{side}-{kind}', floor() + [probe], 3 if kind == 'touch' else 2,
                    metadata={'axis': axis, 'padded_boundary': boundary,
                              'probe_coordinate': coordinate, 'outside_binary32_ulps': int(kind == 'outside')})

    crossing = ((-20, 0, -20), (10, 0, 50), (40, 0, -20))
    require(all(not (PADDED_LOW <= v[0] <= PADDED_HIGH and PADDED_LOW <= v[2] <= PADDED_HIGH)
                for v in crossing), 'crossing fixture accidentally contains an in-bounds vertex')
    add('crossing-all-vertices-outside', [distant(), crossing], 1)
    add('negative-origin', [distant(-100, -100)] + floor(-44, -64, -16, -36), 2,
        grid=['-40', '-60', '0', '3', '40', '0', '0'])
    add('border-only-obstacle', floor() + wall(-0.25), 4,
        metadata={'obstacle_outside_nominal_tile': True, 'obstacle_inside_padding': True})

    noise = [distant(100 + i * 4, 100 + (i % 3) * 4) for i in range(32)]
    near = floor()
    # Interleave contributors with disjoint triangles. Selecting a prefix or
    # renumbering kept triangle indices against unchanged vertices must fail.
    add('distant-geometry', noise[:1] + near[:1] + noise[1:17] + near[1:] + noise[17:], 2)
    add('all-disjoint-empty', [distant(), distant(-100, -100)], 0, status=3)
    add('global-y-refusal-despite-disjoint', floor() + [distant(100, 100, 10)], None, status=2)
    add('single-tile-control', floor() + wall(10) + [distant()], None, single=True)

    near = floor(0, 0, 40, 20) + wall(20)
    seam = noise[:1] + near[:2] + noise[1:17] + near[2:] + noise[17:]
    for x in (0, 1):
        add(f'seam-wall-{x}', seam, 4, grid=['0', '0', '0', '3', '40', str(x), '0'])
    require(len(cases) == EXPECTED_CASES, 'fixture count changed without updating expected count')
    return cases


def write_obj(path, triangles):
    lines = []
    for triangle in triangles:
        # Independent vertices keep all original source indices observable even
        # when intervening triangles are culled. Nine digits round-trip f32.
        for vertex in triangle:
            values = [f32(v) for v in vertex]
            require(all(math.isfinite(v) for v in values), 'nonfinite synthetic fixture')
            lines.append('v ' + ' '.join(format(v, '.9g') for v in values))
    for i in range(len(triangles)):
        first = 3 * i + 1
        lines.append(f'f {first} {first + 1} {first + 2}')
    with path.open('x', encoding='utf-8') as target:
        target.write('\n'.join(lines) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extractor', required=True, type=Path)
    parser.add_argument('--backend', required=True, type=Path)
    parser.add_argument('--baseline-backend', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    try:
        tools = {'extractor': args.extractor.resolve(strict=True),
                 'backend': args.backend.resolve(strict=True),
                 'baseline': args.baseline_backend.resolve(strict=True),
                 'script': Path(__file__).resolve(strict=True)}
        root = args.output_dir.resolve()
        require(not any((p / '.git').exists() for p in [root, *root.parents]),
                'output directory must remain outside Git repositories')
        root.mkdir(parents=True, exist_ok=False)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    receipt = {'schema': 'banshee-tile-selection-smoke-v1', 'verdict': 'FAIL',
               'started_cst': datetime.now(CST).isoformat(), 'scope': 'bounded synthetic padded-X/Z regression',
               'game_qa': 'NOT_RUN', 'settings': SETTINGS, 'expected_cases': EXPECTED_CASES,
               'expected_commands': EXPECTED_COMMANDS, 'tools': {}, 'inputs': {}, 'artifacts': {},
               'cases': [], 'commands': [], 'failures': []}
    watched = []

    def watch(name, path, group, limit):
        entry = {'path': str(path), 'before': fingerprint(path, limit)}
        receipt[group][name] = entry
        watched.append((entry, path, limit))
        return entry['before']

    def run(label, argv, expected):
        record = {'label': label, 'argv': list(map(str, argv)), 'expected_exit_code': expected,
                  'timeout_seconds': 90}
        try:
            result = subprocess.run(record['argv'], capture_output=True, text=True, timeout=90)
            record.update(exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)
        except subprocess.TimeoutExpired as error:
            def text(value):
                return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else value or ''
            record.update(exit_code=None, stdout=text(error.stdout), stderr=text(error.stderr), error='timeout')
        except OSError as error:
            record.update(exit_code=None, stdout='', stderr='', error=str(error))
        receipt['commands'].append(record)
        require(record['exit_code'] == expected, f'{label}: expected exit {expected}, got {record["exit_code"]}')
        return record

    try:
        for name, path in tools.items():
            watch(name, path, 'tools', 128 * 1024 * 1024)
        require(receipt['tools']['backend']['before']['sha256'] !=
                receipt['tools']['baseline']['before']['sha256'], 'new and baseline backends are identical')
        versions = {}
        for label in ('baseline', 'backend'):
            result = run(label + '-version', [tools[label], '--version'], 0)
            version = re.search(r'\bdetour=(\d+)\s+reference_bits=(32|64)\b', result['stdout'])
            require(version is not None and version.group(1) == '7', f'{label}: unsupported backend version')
            versions[label] = int(version.group(2))
        require(versions['backend'] == versions['baseline'], 'baseline/new reference widths differ')
        receipt['reference_bits'] = versions['backend']

        paths = {}
        for case in fixtures():
            name, triangles = case['name'], case['triangles']
            source = root / (name + '.obj')
            write_obj(source, triangles)
            watch(name, source, 'inputs', 1024 * 1024)
            outcomes = {}
            for label in ('baseline', 'backend'):
                destination = root / f'{name}-{label}.navtile'
                if case['single']:
                    argv = [tools['extractor'], 'build-obj', tools[label], source, destination, *SETTINGS]
                else:
                    argv = [tools['extractor'], 'build-tile-obj', tools[label], source, destination,
                            *case['grid'], *SETTINGS]
                result = run(name + '-' + label, argv, case['status'])
                selections = SELECTION.findall(result['stderr'])
                if label == 'backend' and case['candidates'] is not None:
                    expected = (len(triangles), case['candidates'], len(triangles) - case['candidates'])
                    require(len(selections) == 1 and tuple(map(int, selections[0])) == expected,
                            f'{name}: unexpected padded selection statistics: {selections}')
                    result['selection_counts'] = dict(zip(('input', 'candidates', 'culled'), expected))
                else:
                    require(not selections and 'triangle_selection=' not in result['stderr'],
                            f'{name}-{label}: unexpected triangle selection stage')
                if case['status'] == 0:
                    info = watch(name + '-' + label, destination, 'artifacts', 64 * 1024 * 1024)
                    require(info['bytes'] > 100, f'{name}-{label}: absent native tile payload')
                    outcomes[label] = {'exit_code': 0, 'raw_bytes': info['bytes'], 'raw_sha256': info['sha256']}
                    paths[name + '-' + label] = destination
                else:
                    require(not destination.exists(), f'{name}-{label}: failure created an output tile')
                    if case['status'] == 2:
                        require('global vertical bounds must contain the supplied geometry' in result['stderr'],
                                f'{name}-{label}: refusal was not global geometry validation')
                    else:
                        require('status=EMPTY' in result['stdout'], f'{name}-{label}: missing empty status')
                    outcomes[label] = {'exit_code': case['status'], 'output_created': False}
            require(outcomes['baseline'] == outcomes['backend'], f'{name}: status or raw tile differs from baseline')
            receipt['cases'].append({'name': name, 'input_triangles': len(triangles),
                                     'expected_candidates': case['candidates'], 'grid': case['grid'],
                                     'single': case['single'], 'metadata': case['metadata'],
                                     'outcomes': outcomes, 'equal_to_baseline': True})

        queries = {}
        for label in ('baseline', 'backend'):
            result = run('seam-wall-query-' + label,
                         [tools[label], 'query-tiles', '0', '-0.25', '0', '20',
                          '2', '0', '10', '38', '0', '10',
                          paths['seam-wall-0-' + label], paths['seam-wall-1-' + label]], 0)
            query = json.loads(result['stdout'])
            require(query.get('complete') is True and query.get('traversed_tiles') == 2
                    and query.get('loaded_tiles') == 2 and query.get('direct_path_blocked') is True
                    and len(query.get('points', [])) > 2, f'{label}: seam-wall route lacks expected detour')
            for a, b in zip(query['points'], query['points'][1:]):
                require(all(math.isfinite(v) for v in a + b), 'nonfinite query point')
                if min(a[0], b[0]) <= 20 <= max(a[0], b[0]):
                    if a[0] == b[0]:
                        require(max(a[2], b[2]) < 5 or min(a[2], b[2]) > 15, 'route follows obstacle plane')
                    else:
                        crossing = a[2] + (20 - a[0]) / (b[0] - a[0]) * (b[2] - a[2])
                        require(crossing < 5 or crossing > 15, 'route crosses the seam wall')
            queries[label] = query
        require(queries['baseline'] == queries['backend'], 'seam-wall query differs from baseline')
        receipt['seam_wall_queries'] = queries
        require(len(receipt['commands']) == EXPECTED_COMMANDS, 'unexpected command count')
        require(len(receipt['cases']) == EXPECTED_CASES, 'unexpected completed case count')
    except (OSError, ValueError, struct.error, KeyError, TypeError) as error:
        receipt['failures'].append(str(error))
    finally:
        for entry, path, limit in watched:
            try:
                entry['after'] = fingerprint(path, limit)
                entry['unchanged'] = entry['after'] == entry['before']
                if not entry['unchanged']:
                    receipt['failures'].append(f'fingerprint changed during smoke: {path}')
            except (OSError, ValueError) as error:
                entry['unchanged'] = False
                receipt['failures'].append(f'fingerprint readback failed: {error}')

    if not receipt['failures']:
        receipt['verdict'] = 'PASS'
    receipt['finished_cst'] = datetime.now(CST).isoformat()
    with (root / 'result.json').open('x', encoding='utf-8') as target:
        json.dump(receipt, target, indent=2, allow_nan=False)
        target.write('\n')
    print(json.dumps({'verdict': receipt['verdict'], 'receipt': str(root / 'result.json'),
                      'cases': len(receipt['cases']), 'commands': len(receipt['commands']),
                      'failures': receipt['failures'], 'game_qa': 'NOT_RUN'}))
    return 0 if receipt['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
