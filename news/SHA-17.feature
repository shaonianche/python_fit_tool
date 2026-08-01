Retain unknown native field ids on known messages during decode as
`UnknownField` (with `raw_bytes` for later PRESERVATION rewrite). Unedited
`to_bytes(preserve=True)` remains bit-identical via `wire_document`.
