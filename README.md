# walt [![Build Status][build-badge]][action-link] [![Coverage Status][codecov-badge]][codecov-link]

walt — Website Availability Monitor

## Installation

### Requirement

- Python >= 3.8

Clone the repo and install with `pip`:

    $ git clone git@github.com:scorphus/walt.git
    $ cd walt
    $ pip install

Verify the installation:

    $ walt --version

## Usage

Check how to use it with:

    $ walt --help

## Configuration

walt is configured with a [TOML] file. Either base off of
[`config.sample.toml`][config.sample.toml] or generate a new sample:

    $ walt generate_config_sample

Then change the configuration accordingly:

```toml
log_level = "INFO"  # Logging level
```

## Development

### Requirements

- Python >= 3.8
- An activated virtual environment
- [pre-commit]

### Create a development environment

1. Start by creating a new Python virtual environment with the tool of your
   choice (we recommend [pyenv])
2. Install pre-commit (we recommend [installing][pre-commit-install] it not as
   part of the virtual environment — use your system's package manager)
3. Install walt in editable mode with all required dependencies:

       $ make setup

### Run tests

Once you have a working development environment:

1. Run tests

       $ make tests

2. Check code coverage

       $ make coverage
       $ open htmlcov/index.html

3. Lint the code:

       $ make lint

Have fun!

## License

Code in this repository is distributed under the terms of the BSD 3-Clause
License (BSD-3-Clause).

See [LICENSE] for details.

[build-badge]: https://github.com/scorphus/walt/workflows/Python/badge.svg
[action-link]: https://github.com/scorphus/walt/actions?query=workflow%3APython
[codecov-badge]: https://codecov.io/gh/scorphus/walt/branch/main/graph/badge.svg?token=AefYHaJ5VS
[codecov-link]: https://codecov.io/gh/scorphus/walt
[toml]: https://gist.github.com/njsmith/78f68204c5d969f8c8bc645ef77d4a8f#summary
[config.sample.toml]: config.sample.toml
[pre-commit]: https://pre-commit.com
[pre-commit-install]: https://pre-commit.com/#install
[pyenv]: https://github.com/pyenv/pyenv
[license]: LICENSE
