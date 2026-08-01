Post-edit **PRESERVATION**: per-record dirty tracking (field mutations mark
`Record.dirty`) so `to_bytes(preserve=True)` re-encodes only edited records and
copies `source_bytes` for the rest (unknown fields and other records survive).
Opt-in `ConformanceLevel.PRESERVATION` reports loss when unknown-field
`raw_bytes` were cleared. Structural `mark_dirty()` / add / remove still force
a full projected re-encode.
