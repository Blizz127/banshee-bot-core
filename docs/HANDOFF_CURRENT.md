# Current handoff — 2026-11-15 06:27 CST

Task `dcc9a63a40ab` remains **working**. The sole root integrator owns this
repository; helper changes are integrated. Current candidate source is
`73cd8da930137278bdf2cf7a2b6028f2ccb6ce04`. This note directs continuation; historical handoff packets
and failure evidence remain valid for their original source and scope.

## Completed boundary

[Build0015](BUILD_0015.md) is the current proposed private tool/source candidate:
archive SHA256 `7c8b21b540123f23462b62c7c60901bdb78833d262f0f81a540c6ed55ad93029`.
Padded selection and one-decode [tile batches](NAV_BATCH.md) are implemented.
Each reference ABI passes 29 checks / 32 commands; separate single-tile controls
match retained bytes. Package/readback passes 138 payloads and 13 startup
invocations. The coordinator intake is queued once in
`evidence/build0015-readback/coordinator-response.json`; this is not publication.
Do not resend it or replay the closed synthetic checks without a new reason.

## Boundaries that remain with their owners

| Item | Current state | Next owning result |
| --- | --- | --- |
| Native C1 | PARTIAL; canonical coherent 04b/shared6ead adoption, isolated module results only | Current native adapter/P0 and Game QA, independent of maps |
| Role-election helper | Pure source comparison passed; additive and unadopted | Native job mapping/state/setter/atomic-clock review and P0 if the owner adopts it |
| Native runtime work | Bounded 06:23 report: native compile failure, all four checks unrun; no shared API defect identified | Owning correction `0be16626` and successor checks; no duplicate worker or retarget |
| Private publication | No receipt in the inspected publisher report | Existing publisher feed identity and launch/update/rollback readback |
| Game navigation | Synthetic and bounded owned evidence only; calibration, collision completeness and runtime coverage remain unproved | Owning geometry/adapter and Game QA acceptance; no producer allowlist expansion |

The existing source comparison, owned native query supplements and producer
identity findings have already been consumed. Follow their links in
[progress](PROGRESS.md), [C1 handoff](C1_ADAPTER_HANDOFF.md), and
[native intake](FFXI_OFFLINE_INTAKE.md), rather than treating an older handoff's
“next check” as a new assignment. Closed native failure evidence remains intact.
The last bounded status observation is
`evidence/c1-metadata-refresh-20261115-062306cst/delta-summary.json`, SHA256
`747b4c9079485a84bb801f330a2dae2e82adb674f7e9976a48d68cd5227f17f1`.
That latest result is an owning-lead summary observation; no native terminal,
source/test body or packet was opened by the refresh.

## Next independent work

Integrate an **opt-in** bounded batch path into `bake_nav_collection.py` while
preserving its default individual-cell behavior and existing manifest validation.
The standalone batch manifest has no source/output hashes and is not a collection
receipt. Collection integration must bind input/tool identities, the batch
command/complete result, every built/empty cell and file hash; reject missing,
tampered or partial batches without fabricating per-cell backend executions.
Keep requested coverage, native ABI and calibration limitations explicit.

The cost measurement is already closed: one four-cell batch used 0.288889 CPU
seconds against a saved 1.496237-second separate-build baseline, all tile bytes
equal. Host load changed; this is a sparse synthetic observation, not a general
speed guarantee. Do not replay the baseline or smoke matrix without a relevant
change. Per-cell bounds and candidate scans still repeat; a spatial index can
wait until another measured need. Keep single-tile mode and distinct reference
ABIs intact. Unknown game formats still require REA; existing setup/native
permission refusals must not be bypassed.

New closed native evidence can be appended once when delivered; do not poll
running/preparing jobs or wait for another lane's acknowledgement. C0 missing
piece requests are already dispatched; do not rebroadcast them. C2+ rollout
remains gated behind C1 acceptance. No later gameplay phase has been enabled.

**NEVER restart FFXI**, including at zero players. No package grants install,
reload, access, player/progress or device authority. No other repository or
shared configuration changes, pushes or public release. All existing holds
persist; coordinator continuation notices do not revoke them.
