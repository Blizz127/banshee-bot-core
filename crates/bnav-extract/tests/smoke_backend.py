#!/usr/bin/env python3
"""Focused synthetic Recast build/reload/path smoke; no game data or services."""
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
    extractor = str(args.extractor.resolve(strict=True))
    backend = str(args.backend.resolve(strict=True))
    records = []

    def run(command, expected=0):
        result = subprocess.run(command, text=True, capture_output=True, timeout=90)
        record = dict(argv=list(map(str, command)), exit_code=result.returncode,
                      stdout=result.stdout, stderr=result.stderr)
        records.append(record)
        (root/'commands.json').write_text(json.dumps(records, indent=2)+'\n')
        assert result.returncode == expected, record
        return result

    floor = 'v 0 0 0\nv 20 0 0\nv 20 0 20\nv 0 0 20\nf 1 3 2\nf 1 4 3\n'
    wall = 'v 10 0 5\nv 10 3 5\nv 10 3 15\nv 10 0 15\nf 5 6 7\nf 5 7 8\n'
    fixtures = {
        'floor': floor, 'wall': floor + wall,
        'disconnected': 'v 0 0 0\nv 8 0 0\nv 8 0 20\nv 0 0 20\nv 12 0 0\nv 20 0 0\nv 20 0 20\nv 12 0 20\nf 1 3 2\nf 1 4 3\nf 5 7 6\nf 5 8 7\n',
        'huge': 'v 0 0 0\nv 100000 0 0\nv 0 0 100000\nf 1 3 2\n',
    }
    for name, text in fixtures.items():
        (root/f'{name}.obj').write_text(text)
    run([backend, '--help'])
    identity = run([backend, '--version']).stdout
    bits = identity.strip().split('reference_bits=')[1]
    for name in ['floor', 'wall', 'disconnected']:
        run([extractor, 'build-obj', backend, root/f'{name}.obj', root/f'{name}.navtile'])
        run([extractor, 'inspect-detour', bits, root/f'{name}.navtile'])

    def query(name, expected=0):
        result = run([backend, 'query', root/f'{name}.navtile', '2', '0', '10', '18', '0', '10'], expected)
        return json.loads(result.stdout) if expected == 0 else result

    straight = query('floor')
    assert straight['complete'] and not straight['direct_path_blocked']
    assert len(straight['points']) == 2
    detour = query('wall')
    assert detour['complete'] and detour['direct_path_blocked']
    assert len(detour['points']) > 2
    # No returned segment may cross the physical wall at x=10, z=[5,15].
    for left, right in zip(detour['points'], detour['points'][1:]):
        if min(left[0], right[0]) <= 10 <= max(left[0], right[0]):
            assert right[0] != left[0]
            fraction = (10-left[0])/(right[0]-left[0])
            crossing_z = left[2]+fraction*(right[2]-left[2])
            assert crossing_z < 5 or crossing_z > 15, detour
    assert 'no complete path' in query('disconnected', 2).stderr
    run([extractor, 'build-obj', backend, root/'huge.obj', root/'huge.navtile'], 2)
    assert not (root/'huge.navtile').exists()
    for label, settings in [
        ('zero-cell', ['0','.2','2','.6','.9','45']),
        ('nan-height', ['.3','.2','NaN','.6','.9','45']),
        ('negative-radius', ['.3','.2','2','-.6','.9','45']),
    ]:
        run([extractor, 'build-obj', backend, root/'floor.obj', root/f'{label}.navtile', *settings], 2)
        assert not (root/f'{label}.navtile').exists()
    original = hashlib.sha256((root/'floor.navtile').read_bytes()).hexdigest()
    run([extractor, 'build-obj', backend, root/'wall.obj', root/'floor.navtile'], 2)
    assert hashlib.sha256((root/'floor.navtile').read_bytes()).hexdigest() == original
    wrong_bits = '64' if bits == '32' else '32'
    run([extractor, 'inspect-detour', wrong_bits, root/'wall.navtile'], 2)
    result = {'verdict':'PASS', 'scope':'synthetic single-tile bake/reload/query',
              'reference_bits':int(bits), 'wall_query':detour,
              'game_qa':'not run', 'backend_sha256':hashlib.sha256(Path(backend).read_bytes()).hexdigest(),
              'artifacts_sha256':{path.name:hashlib.sha256(path.read_bytes()).hexdigest()
                                  for path in sorted(root.glob('*.navtile'))}}
    (root/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
