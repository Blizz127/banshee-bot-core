# Private build candidates

Builds are local review/QA candidates until the existing private publisher and
Game QA report their results. Nothing in this repository publishes a website,
pushes source, replaces a game server or restarts an occupied server.

`scripts/package_build.py` requires clean committed source. It builds the three
Rust workspace crates in release mode using two low-priority jobs, runs CLI
startup checks and confirms the synthetic soak remains incomplete. It archives
the exact source commit, tools, provenance and supplied verification receipts.
Every file has a SHA-256/size entry in the manifest. New output directories and
archives are created without replacing an earlier candidate.

After packaging, run the [archive readback](BUILD_READBACK.md) against its exact
reported byte size. This verifies the archive and embedded files before running
the packaged CLI startup checks in a fresh external evidence directory.

```sh
python3 scripts/package_build.py --build 0001 \
  --output /home/blizz/.local/share/banshee-bot-core/builds \
  --backend /absolute/path/to/bnav-recast \
  --backend-manifest /absolute/path/to/backend/manifest.json \
  --backend-license /absolute/path/to/RECAST-LICENSE.txt \
  --verification /absolute/path/to/compatibility/result.json
```

The native backend is optional but its executable, build manifest and licence
must be supplied together. The packager verifies the backend binary hash and
original bridge source hash against that manifest. Compatibility receipts with
core file hashes must still match the packaged source. Version and build number
identify the candidate; the tarball SHA-256 identifies its exact bytes.

An additional `--backend64`, `--backend64-manifest`, `--backend64-license`
triple packages a separate `bin/bnav-recast64`. Its version must report 64-bit
references; it does not replace or change `bin/bnav-recast`. Both native
identities, exact bridge source, dependency licence and startup versions are
verified. The manifest records each ABI explicitly. Backend compilation can
request `--reference-bits 64` to define `DT_POLYREF64` without modifying external
headers; `--reference-bits 32` refuses a dependency that still builds as 64-bit.
Omitting that compile option retains the selected header's existing behavior.

New manifests also retain the current FFXI no-restart hold. A package never
grants installation/reload permission, and zero players does not lift that hold.

All candidates label live `/fb` P0 and Game QA as **NOT_RUN**, feature defaults
as **OFF**, and deployment/publication as **NOT_PERFORMED**. Local checks cannot
upgrade those fields. Publisher receipts and later Game QA verdicts are recorded
separately in `PROGRESS.md`, referencing the original artifact hash.

There is no established bot-core launcher feed contract in this repository.
Send one concrete artifact intake through Devbox to the existing Banshee Client
Bot/launcher owner, including version, tarball path, hash, byte size, manifest,
check scope and replacement/supersession information. That owner controls private
launcher publication and readback. A task-board report alone is not publication.

Keep assets, binaries, captures, source snapshots and all build outputs outside
git under `~/.local/share/banshee-bot-core/`. The source archive includes only
tracked original repository files, not private game geometry or evidence trees.
