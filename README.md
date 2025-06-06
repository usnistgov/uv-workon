<!-- markdownlint-disable MD041 -->

<!-- prettier-ignore-start -->
[![Repo][repo-badge]][repo-link]
[![Docs][docs-badge]][docs-link]
[![PyPI license][license-badge]][license-link]
[![PyPI version][pypi-badge]][pypi-link]
[![Code style: ruff][ruff-badge]][ruff-link]
[![uv][uv-badge]][uv-link]
<!-- [![Conda (channel only)][conda-badge]][conda-link] -->

<!--
  For more badges, see
  https://shields.io/category/other
  https://naereen.github.io/badges/
  [pypi-badge]: https://badge.fury.io/py/uv-workon
-->

[ruff-badge]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
[ruff-link]: https://github.com/astral-sh/ruff
[uv-badge]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json
[uv-link]: https://github.com/astral-sh/uv
[pypi-badge]: https://img.shields.io/pypi/v/uv-workon
[pypi-link]: https://pypi.org/project/uv-workon
[docs-badge]: https://img.shields.io/badge/docs-sphinx-informational
[docs-link]: https://pages.nist.gov/uv-workon/
[repo-badge]: https://img.shields.io/badge/--181717?logo=github&logoColor=ffffff
[repo-link]: https://github.com/usnistgov/uv-workon
<!-- [conda-badge]: https://img.shields.io/conda/v/wpk-nist/uv-workon -->
<!-- [conda-link]: https://anaconda.org/wpk-nist/uv-workon -->
[license-badge]: https://img.shields.io/pypi/l/uv-workon?color=informational
[license-link]: https://github.com/usnistgov/uv-workon/blob/main/LICENSE

<!-- other links -->

[uv]: https://docs.astral.sh/uv/
[virtualenvwrapper]: https://virtualenvwrapper.readthedocs.io/en/latest/
[conda]: https://github.com/conda/conda
[uv-central-discussion]: https://github.com/astral-sh/uv/issues/1495

<!-- prettier-ignore-end -->

# `uv-workon`

Command line program `uv-workon` to work with multiple [uv] based virtual
environments. Note that the program name `uv-workon` differs from the project
name `uv-workon` as `uv-workon` was taken on pypi.

## Overview

[`uv`][uv] has taken the python world by storm, and for good reason. It manages
projects, dependencies, virtual environment creation, and much more, all while
being blazingly fast. One of the central ideas of [uv] is that the old method of
activating virtual environments should be replace with `uv run ...` and letting
[uv] figure out the rest. We fully agree with this workflow, but it does run
counter to how many have used python virtual environments day to day for data
work. For example, many have historically used tools like [`conda`][conda] or
[`virtualenvwrapper`][virtualenvwrapper] to manage centrally located python
environments, that can be reused for multiple tasks. While we discorage using
"mega" environments (i.e., sticking every dependency you'll ever need in a
single python environments), there is utility in using a virtual environment for
multiple tasks. There is [active discussion][uv-central-discussion] regarding if
and how [uv] should manage centralized virtual environments.

We takes the perspective that python virtual environments should be managed with
uv inside a project. `uv-workon` allows for the usage of such virtual
environments _outside_ the project. The basic workflow is as follows:

1. Create a project `my-project` using `uv init ...`
2. Create a virtual environment `my-project/.venv` using `uv sync ...`
3. Link to central location using `uv-workon link my-project`

Now, from anywhere, you can use the virtual environment `my-project`:

- Activate with `uv-workon activate -n my-project`
- Run python using the `my-project` virtual environment with
  `uv-workon run -n my-project ...`
- Change to the `my-project` project directory with `uv-workon cd -n my-project`

## Features

- Link virtual environment to central location with `uv-workon link`. These
  links are located at `WORKON_HOME` environment variable, defaulting to
  `~/.virtualenvs`.
- Activate virtual environment with `uv-workon activate ...` (requires shell
  integration)
- Run under virtual environment with `uv-workon run ...`
- Change to project directory with `uv-workon cd ...` (requires shell
  integration)
- List available virtual environments with `uv-workon list`
- Cleanup missing symlinks with `uv-workon clean`
- Manage [`ipykernel`](https://github.com/ipython/ipykernel) with
  `uv-workon kernels ...`
  - Install kernels for linked virtual environments which have `ipykernel`
    installed with `uv-workon kernels install ...`
  - Remove kernels (including remove all missing/broken kernels) with
    `uv-workon kernels remove ...`
  - list installed kernels with `uv-workon kernels list ...`

## Status

This package is actively used by the author. Please feel free to create a pull
request for wanted features and suggestions!

<!-- end-docs -->

## Quick start

<!-- start-installation -->

It is recommended to install with [`uv`](https://docs.astral.sh/uv/):

```bash
uv tool install uv-workon
```

To include the ability to manage
[`ipykernel`](https://github.com/ipython/ipykernel), include the `jupyter`
extra:

```bash
uv tool install "uv-workon[jupyter]"
```

### Add autocompletion

Run the following to add autocompletion for `uv-workon`:

```bash
uv-workon --install-completion
```

### Shell integration

To use `uv-workon activate` and `uv-workon cd`, you must enable the shell
configuration with `eval "$(uv-workon shell-config)", or add it to you config
script with:

```bash
# for zsh
echo 'eval "$(uv-workon shell-config)"' >> ~/.zshrc
# for bash
echo 'eval "$(uv-workon shell-config)"' >> ~/.bashrc
# for fish
echo 'uv-workon shell-config | source' >> ~/.config/fish/completions/uv-workon.fish
```

Open a issue if you need support for another shell.

<!-- end-installation -->

## Documentation

See the [documentation][docs-link] for further details.

## License

This is free software. See [LICENSE][license-link].

## Related work

Any other stuff to mention....

## Contact

The author can be reached at <wpk@nist.gov>.

## Credits

This package was created using
[Cookiecutter](https://github.com/audreyr/cookiecutter) with the
[usnistgov/cookiecutter-nist-python](https://github.com/usnistgov/cookiecutter-nist-python)
template.
