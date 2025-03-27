<!-- markdownlint-disable MD024 -->
<!-- markdownlint-disable MD013 -->
<!-- prettier-ignore-start -->
# Changelog

Changelog for `uv-workon`

## Unreleased

[changelog.d]: https://github.com/usnistgov/uv-workon/tree/main/changelog.d

See the fragment files in [changelog.d]
<!-- prettier-ignore-end -->

<!-- markdownlint-enable MD013 -->

<!-- scriv-insert-here -->

## v0.5.1 — 2025-03-27

### Changed

- Cleanup output for kernels install for environments without ipykernels. Now
  only outputs `No ipykernels` if `--verbose` option passed

## v0.5.0 — 2025-03-27

### Added

- Added subcommand `uvw venv-link` to link from workon-home to local `.venv`.

## v0.4.0 — 2025-03-25

### Changed

- Now supports `--yes/--no` options. Default is to query the user to yes/no
  questions. Passing `--yes` will always answer yes. Passing `--no` will always
  answer no.

## v0.3.1 — 2025-03-25

### Fixed

- Removed warning from `uvw kernels list` and type completion.

## v0.3.0 — 2025-03-19

### Added

- Added `kernels` subcommands with:
  - install - install ipykernels
  - remove - remove jupyer kernels
  - list - list jupyter kernels This adds functionality to easy transition from
    nb_conda_kernels to using uv to manage virtual environment.
- Added tests to have full coverage.
