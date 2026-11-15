# Private QA candidate 0.1.0-build0011

Created **2026-11-15 04:01:40 CST**. **QA_CANDIDATE, not released.**
Build, readback and packaged startup: **PASS**. Publication has no receipt;
native FFXI P0 and Game QA remain **NOT_RUN**. New features stay OFF.

| Item | Identity |
| --- | --- |
| Archive | `/home/blizz/.local/share/banshee-bot-core/builds/banshee-bot-core-0.1.0-build0011/banshee-bot-core-0.1.0-build0011.tar.gz` |
| SHA256 | `12766e77afc1e76013e01c6a2d4de711d9bd573fc4770d946f6d3a382c4ed8ed` |
| Bytes | `1042414` |
| Source commit | `512960fc51888d18556d38caadad33f4fea8587e` |
| Manifest/checksum | Same build directory: `manifest.json`, `SHA256SUMS` |

Adds a structured [future Rust producer association](BUILDS.md) and an explicit
compiler-job limit to packaging. A fresh target/intermediate directory avoids
reusing previous Cargo artifacts. The host target, compiler and Cargo are
explicit; compiler wrappers are disabled only for this build. The receipt pins
tracked source/lock inputs, command arguments, tool executable hashes/verbose
versions, observed build-log hash and resulting Rust binaries. Source and tool
identities stayed stable through this one-job, low-priority build.

VERIFIED: **six focused synthetic provenance tests pass**. The actual fresh
build and archive readback also pass: **116 payloads**, **13 startup calls**.
All **102 tracked source files**, the build log and both Rust binaries join to
`provenance/rust-build-manifest.json`. Its SHA256 is
`1fcfb9207da3c81cb9330cf9ce5c8aab473f44744ff52ec858cf304711e847e4`.
Five saved Cargo compiler invocations use the pinned compiler path, covering
the workspace's three crates. No invocation was replayed for that check.

All four packaged executables match build0010 byte-for-byte. In particular,
the new observed release extractor still hashes to
`e34ee982ed73636bc6cc3fb8db20152088629d1d8bb1d5f8a8f2363a903d077f`.
This establishes this fresh build association; it does **not** reconstruct the
different historical `f64f0648` extractor's missing provenance or establish
general producer equivalence. Ambient configuration, linker and dynamic
libraries are not fully pinned; no hermetic/reproducible-build claim is made.

The 20 current core inputs and navigation/decision test sources retain their
completed receipt identities. No Rust API behavior changed in this increment,
and those earlier tests or C1 comparisons were not replayed or aggregated.

Receipts beneath `/home/blizz/.local/share/banshee-bot-core/`:

| Receipt | SHA256 |
| --- | --- |
| `evidence/rust-producer-integrated-20261115-01/result.json` | `14692643b11c5bef313bc4662a73254b4408844d7f3cd9d9693e5955e9586ee9` |
| `evidence/build0011-readback/result.json` | `f1fbca65401c976108573ffd0d281fcd370c3a2462416d14cc7e8b0c02519f9b` |
| `evidence/build0011-readback/producer-evidence-join.json` | `f290b7333e7c40dee756789b26de11aad02d968f9462666f2717ee93900aee2d` |
| `evidence/build0011-readback/compiler-invocations.json` | `f6065da826a41410d700affb8aead7f89c23c5b322e5ff5df6108bb4da9346d4` |

**Supersedes proposed build0010 for the private publisher only.** Retain earlier
candidates for rollback. Same Linux x86-64/Python 3.11 developer tool/source-kit
contract; separate native32/native64 executables and Python query entry points.
Existing publisher `claude-banshee-realm-client`, task `3f9392ca5d00`, owns feed
publication, uploaded identity, launch/update detection and rollback checks.

The owning FFXI 04b/shared6ead source candidate remains canonical. No new native
intake, producer adoption or allowlist change is proposed. Current native P0,
Game QA and C2+ rollout gates persist; C1 has no map gate. **Never restart FFXI**,
including at zero players. This package grants no installation/reload authority.
