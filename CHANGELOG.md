## Release v0.9.15 (2026-02-02)

### Features & Improvements

- Optimize `Field.to_bytes` with `b''.join` for better performance. ([#4](https://github.com/shaonianche/python_fit_tool/issues/4))
- Remove redundant record re-encoding verification from `FitFile.from_bytes` for improved performance. ([#10](https://github.com/shaonianche/python_fit_tool/issues/10))
- Add proper logging for unknown base types in profile generation. ([#17](https://github.com/shaonianche/python_fit_tool/issues/17))
- Add uv support and modernize CLI. ([#18](https://github.com/shaonianche/python_fit_tool/issues/18))

### Bug Fixes

- Fix test errors. ([#2](https://github.com/shaonianche/python_fit_tool/issues/2))
- Optimize `get_developer_field` lookup and fix `StopIteration` bug. ([#7](https://github.com/shaonianche/python_fit_tool/issues/7))

### Dependencies

- Switch the build toolchain to UV ([#19](https://github.com/shaonianche/python_fit_tool/issues/19))

### Miscellany

- Add Codecov integration for code coverage reporting. ([#11](https://github.com/shaonianche/python_fit_tool/issues/11))
- Improve test coverage. ([#13](https://github.com/shaonianche/python_fit_tool/issues/13))
