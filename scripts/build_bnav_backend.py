#!/usr/bin/env python3
"""Compile the original bridge with explicitly selected external Recast sources.

All outputs go into a new directory outside this repository and the dependency
tree. Sources and their licence stay in place; the manifest pins every input.
"""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import shutil


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recast-root', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--cxx', default='c++')
    args = parser.parse_args()
    if not 1 <= args.jobs <= 8:
        parser.error('--jobs must be between 1 and 8; size it to measured host pressure')
    repo = Path(__file__).resolve().parents[1]
    source = args.recast_root.resolve(strict=True)
    output = args.output_dir.resolve()
    if output.is_relative_to(repo) or output.is_relative_to(source):
        parser.error('output must be outside the repository and external source tree')
    required = ['License.txt','Recast/Include/Recast.h','Detour/Include/DetourNavMesh.h']
    for relative in required:
        if not (source / relative).is_file():
            parser.error(f'missing expected source input: {relative}')
    bridge = repo / 'crates/bnav-extract/native/bnav_recast.cpp'
    sources = [bridge]
    headers = []
    for library in ['Recast','Detour']:
        sources.extend(sorted((source/library/'Source').glob('*.cpp')))
        headers.extend(sorted((source/library/'Include').glob('*.h')))
    if len(sources) < 10:
        parser.error('incomplete Recast/Detour source tree')
    inputs = sources + headers + [source/'License.txt']
    source_identity = {str(path):digest(path) for path in inputs}
    # New output directories prevent replacing a previously published helper.
    output.mkdir(parents=True, exist_ok=False)
    flags = ['-std=c++17','-O2','-DNDEBUG','-I',str(source/'Recast/Include'),'-I',str(source/'Detour/Include')]
    commands = []
    objects = []
    for index, path in enumerate(sources):
        obj = output / f'{index:02d}-{path.stem}.o'
        objects.append(obj)
        commands.append(['nice','-n','19',args.cxx,*flags,'-c',str(path),'-o',str(obj)])

    def compile_one(command):
        run = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return {'argv': command, 'exit_code': run.returncode, 'output': run.stdout}

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(compile_one, commands))
    (output/'compile.json').write_text(json.dumps(results,indent=2)+'\n')
    failed = [r for r in results if r['exit_code']]
    if failed:
        for record in failed:
            print(record['output'],file=sys.stderr)
        return 1
    binary = output/'bnav-recast'
    link = compile_one(['nice','-n','19',args.cxx,*map(str,objects),'-o',str(binary)])
    (output/'link.json').write_text(json.dumps(link,indent=2)+'\n')
    if link['exit_code']:
        print(link['output'],file=sys.stderr)
        return 1
    identity = subprocess.run(['git','-C',str(source),'rev-parse','HEAD'],text=True,capture_output=True)
    if {str(path):digest(path) for path in inputs} != source_identity:
        print('source inputs changed during compilation; output is not publishable',file=sys.stderr)
        return 1
    shutil.copyfile(source/'License.txt', output/'RECAST-LICENSE.txt')
    manifest = {
        'backend': str(binary), 'backend_sha256': digest(binary),
        'dependency_root': str(source), 'dependency_licence': 'zlib',
        'dependency_parent_commit': identity.stdout.strip() if identity.returncode == 0 else None,
        'inputs_sha256': source_identity,
        'compiler': subprocess.check_output([args.cxx,'--version'],text=True).splitlines()[0],
        'flags': flags, 'jobs': args.jobs,
        'scope': 'single-tile geometry-to-Recast/Detour; no game format decoder',
    }
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'backend':str(binary),'sha256':manifest['backend_sha256'],'manifest':str(output/'manifest.json')}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
