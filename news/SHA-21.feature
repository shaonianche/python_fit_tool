FILE_TYPE validation for **Workout** files: required `workout` / `workout_step`
messages and fields (`num_valid_steps`, step `message_index` /
`duration_type` / `target_type`). Activity behavior unchanged; other
`file_id.type` values (e.g. Course) still fail closed. SDK Workout fixtures
validate clean under FILE_TYPE.
