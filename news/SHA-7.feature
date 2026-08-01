Introduce a wire-layer MVP (`fit_tool/wire`) with raw header/record models and a
stateful decoder that keeps immutable definition snapshots. `FitFile.from_bytes`
now decodes via the wire layer and projects to existing typed messages; public
API behavior stays compatible. Deferred: compressed-timestamp reconstruction,
component expansion, chained multi-segment API, and lossless unknown-field rewrite.
