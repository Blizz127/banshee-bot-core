#!/usr/bin/env python3
"""Focused synthetic cross-tile bake/query smoke. No game assets or runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extractor', required=True, type=Path)
    parser.add_argument('--backend', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    root = args.output_dir.resolve()
    root.mkdir(parents=True, exist_ok=False)
    extractor, backend = str(args.extractor.resolve(strict=True)), str(args.backend.resolve(strict=True))
    commands = []

    def run(argv, expected=0):
        result = subprocess.run(list(map(str, argv)), capture_output=True, text=True, timeout=90)
        commands.append({'argv': list(map(str, argv)), 'exit_code': result.returncode,
                         'stdout': result.stdout, 'stderr': result.stderr})
        (root/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        assert result.returncode == expected, commands[-1]
        return result

    floor = 'v 0 0 0\nv 40 0 0\nv 40 0 20\nv 0 0 20\nf 1 3 2\nf 1 4 3\n'
    wall = 'v 20 0 5\nv 20 3 5\nv 20 3 15\nv 20 0 15\nf 5 6 7\nf 5 7 8\n'
    separated = 'v 0 0 0\nv 18 0 0\nv 18 0 20\nv 0 0 20\nv 22 0 0\nv 40 0 0\nv 40 0 20\nv 22 0 20\nf 1 3 2\nf 1 4 3\nf 5 7 6\nf 5 8 7\n'
    settings = ['.5', '.2', '2', '.6', '.9', '45']
    for name, geometry in [('floor', floor), ('wall', floor+wall), ('separated', separated)]:
        source = root/(name+'.obj')
        source.write_text(geometry)
        for x in [0, 1]:
            run([extractor, 'build-tile-obj', backend, source, root/f'{name}-{x}.navtile',
                 '0', '0', '0', '3', '40', str(x), '0', *settings])
    version = run([backend, '--version']).stdout
    bits = int(version.strip().split('reference_bits=')[1])
    for tile in root.glob('*.navtile'):
        run([extractor, 'inspect-detour', bits, tile])

    def query(name, expected=0, subset=(0, 1)):
        result = run([backend, 'query-tiles', '0', '-.2', '0', '20',
                      '2', '0', '10', '38', '0', '10',
                      *[root/f'{name}-{x}.navtile' for x in subset]], expected)
        return json.loads(result.stdout) if expected == 0 else result

    direct = query('floor')
    assert direct['complete'] and not direct['direct_path_blocked']
    assert direct['loaded_tiles'] == 2 and direct['traversed_tiles'] == 2
    detour = query('wall')
    assert detour['complete'] and detour['direct_path_blocked']
    assert detour['traversed_tiles'] == 2 and len(detour['points']) > 2
    for a, b in zip(detour['points'], detour['points'][1:]):
        if min(a[0], b[0]) <= 20 <= max(a[0], b[0]):
            if a[0] == b[0]:
                assert max(a[2], b[2]) < 5 or min(a[2], b[2]) > 15
            else:
                crossing_z = a[2] + (20-a[0])/(b[0]-a[0])*(b[2]-a[2])
                assert crossing_z < 5 or crossing_z > 15, detour
    assert 'no complete path' in query('separated', 2).stderr
    query('floor', 2, (0,))
    query('floor', 2, (0, 0))
    run([backend, 'query-tiles', '1', '-.2', '0', '20', '2', '0', '10', '38', '0', '10',
         root/'floor-0.navtile', root/'floor-1.navtile'], 2)
    empty = root/'empty.navtile'
    run([extractor, 'build-tile-obj', backend, root/'floor.obj', empty,
         '0', '0', '0', '3', '40', '3', '0', *settings], 3)
    assert not empty.exists()
    for label, grid in [
        ('zero-cells', ['0', '0', '0', '3', '0', '0', '0']),
        ('negative-tile', ['0', '0', '0', '3', '40', '-1', '0']),
        ('nonfinite-origin', ['NaN', '0', '0', '3', '40', '0', '0']),
        ('clipped-height', ['0', '0', '0', '1', '40', '0', '0']),
    ]:
        destination = root/(label+'.navtile')
        run([extractor, 'build-tile-obj', backend, root/'wall.obj', destination, *grid, *settings], 2)
        assert not destination.exists()
    before = hashlib.sha256((root/'floor-0.navtile').read_bytes()).hexdigest()
    run([extractor, 'build-tile-obj', backend, root/'wall.obj', root/'floor-0.navtile',
         '0', '0', '0', '3', '40', '0', '0', *settings], 2)
    assert hashlib.sha256((root/'floor-0.navtile').read_bytes()).hexdigest() == before
    result = {'verdict': 'PASS', 'scope': 'synthetic cross-tile Recast/Detour bake/reload/query',
              'reference_bits': bits, 'floor_query': direct, 'wall_query': detour,
              'backend_sha256': hashlib.sha256(Path(backend).read_bytes()).hexdigest(),
              'extractor_sha256': hashlib.sha256(Path(extractor).read_bytes()).hexdigest(),
              'game_qa': 'NOT_RUN',
              'tiles_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.glob('*.navtile'))}}
    (root/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
