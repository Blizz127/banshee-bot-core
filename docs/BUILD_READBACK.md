# Private build archive readback

`scripts/check_build.py` verifies a local candidate produced by
`scripts/package_build.py`, then runs the tools read back from that archive.
It does not publish, deploy, contact a game server or establish Game QA.
Use it only for the owner's known private build artifacts: matching checksums
establish byte identity, not trust in a binary supplied by somebody else.

```sh
python3 scripts/check_build.py \
  --artifact /home/blizz/.local/share/banshee-bot-core/builds/banshee-bot-core-0.1.0-build0002/banshee-bot-core-0.1.0-build0002.tar.gz \
  --expected-bytes 736760 \
  --evidence /home/blizz/.local/share/banshee-bot-core/evidence/build0002-readback
```

Take `--expected-bytes` from the packager's JSON output or recorded publisher
intake. Do not obtain an expected size by measuring the artifact being checked.
The existing `SHA256SUMS` sidecar contains a digest and filename, with no size;
`manifest.json` contains sizes for individual files, with no compressed archive
size. Both sidecars default to the artifact's directory. `--manifest` and
`--sha256-file` select explicit sidecars when needed.

The evidence directory must be new, outside a git worktree, with an existing
parent. There is no overwrite option. Failed attempts remain available for
inspection; choose a new directory for the next attempt.

## Verification and output

The checker verifies the archive size and SHA-256, compares the embedded
manifest byte for byte with its sidecar, and streams every manifest entry to
check its size and SHA-256. It rejects missing, duplicate or unlisted members
except the expected `manifest.json` and `build.log`. It also rejects absolute
or noncanonical paths, links, special files, sparse files, privileged mode bits
and nonzero content after the tar end marker. Input sidecars and the archive
are checked again before any extracted tool runs.

Only these fixed destinations are materialized from archive payloads:

- `bin/bnav-extract` and `bin/bot-soak`.
- `bin/bnav-recast`, when included in the manifest.
- `bin/bnav-recast64`, when separately included with a matching explicit ABI identity.
- `synthetic-short.csv`, from the packaged soak example.

Source, provenance and verification files are hashed without extraction. Files
are created exclusively inside the new evidence directory. Binaries become
executable only after the full archive passes. Each packaged tool runs `--help`
and `--version`; versions must match the manifest. The packaged soak example
must return exit 3 with `source=synthetic`, `verdict=INCOMPLETE` and
`live_game_qa=NOT_RUN`. Its incomplete status is the expected smoke outcome.

Readback limits are 256 MiB compressed, 512 MiB expanded including tar metadata,
128 MiB per member, 4 MiB for the manifest, 4,096 listed files and 1 MiB for the
synthetic CSV. Tool invocations use low priority, a 20-second wall timeout,
15 CPU seconds, a 1 MiB combined output limit and disabled core dumps. These
limits keep this a bounded CLI smoke, not a load test or execution sandbox.

`result.json` records the original input paths, expected and observed artifact
identity, manifest/checker digests, source commit, every checked file, extracted
paths, invocation arguments, exit codes and log hashes. A validation failure
after creating the output directory produces a FAIL receipt; invalid or reused
output paths fail without modifying an earlier attempt. Exit 0 means readback
and startup PASS; exit 1 means failure; argument errors use argparse exit 2.

Native navigation smoke is deliberately recorded as `NOT_RUN` here. The lead
may run the current focused tile/collection smoke against `bin/bnav-extract`
and `bin/bnav-recast` afterward and keep its receipt beside this one. No source
or test script from the archive is executed. Native FFXI P0, live deployment,
private publication and actual-client Game QA retain their separate evidence.
