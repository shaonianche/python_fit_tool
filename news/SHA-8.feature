Unify stream and in-memory FIT decoding on one state machine (`FitDecoder`
over the wire layer) so definition snapshots, developer-field registration,
and CRC handling stay aligned between `FitFile.from_bytes` and `iter_*`.
