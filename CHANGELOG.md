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

## v0.3.0 — 2025-03-19

### Added

- Added `kernels` subcommands with:
  - install - install ipykernels
  - remove - remove jupyer kernels
  - list - list jupyter kernels This adds functionality to easy transition from
    nb_conda_kernels to using uv to manage virtual environment.
- Added tests to have full coverage.
