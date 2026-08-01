Encode policies: explicit `EncodeMode.PRESERVE` / `EncodeMode.CANONICAL` on
`FitFile.to_bytes` (legacy `preserve=` still works). Canonical rebuilds all
records with normalized sizes/CRCs; `strict=True` validates first and never
clamps invalid values. Policy matrix documented in README and design doc §6.
