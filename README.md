# walt [![Build Status][build-badge]][action-link] [![Coverage Status][codecov-badge]][codecov-link] [![Maintainability][codeclimate-badge]][codeclimate-link] [![Code Quality][codacy-badge]][codacy-link]

walt — Website Availability Monitor

Check target websites and keep all verification results on your database! walt
coordinates data flow with Kafka and stores results on Postgres.

walt takes a collection of URLs and their optional regular expression patterns
and checks for:

-   HTTP response time
-   HTTP status code
-   Occurrence of regexp pattern in the page

Verification results are either a `result`:

    walt=> SELECT * FROM result LIMIT 10;
     result_id |                    url                    |    response_time    | status_code |  pattern  |         timestamp          
    -----------+-------------------------------------------+---------------------+-------------+-----------+----------------------------
             1 | https://duckduckgo.com/?q=walt            | 0.08444564199999993 |         200 | FOUND     | 2021-02-07 21:24:24.583+00
             2 | https://www.google.com/search?q=walt      |  1.8681911579999997 |         200 | FOUND     | 2021-02-07 21:24:26.378+00
             3 | https://duckduckgo.com/?q=doge+meme       | 0.01953169999999993 |         200 | NOT_FOUND | 2021-02-07 21:24:26.606+00
             4 | https://duckduckgo.com/?q=walt            | 0.03456038500000069 |         200 | FOUND     | 2021-02-07 21:24:28.641+00
             5 | https://www.google.com/search?q=doge+meme |  0.6267991500000001 |         200 | FOUND     | 2021-02-07 21:24:29.01+00
             6 | https://duckduckgo.com/?q=doge+meme       | 0.02907168100000046 |         200 | NOT_FOUND | 2021-02-07 21:24:31.042+00
             7 | https://www.google.com/search?q=walt      |  1.1037337520000001 |         200 | FOUND     | 2021-02-07 21:24:31.749+00
             8 | https://duckduckgo.com/?q=walt            |          0.03649068 |         200 | FOUND     | 2021-02-07 21:24:33.083+00
             9 | https://www.google.com/search?q=doge+meme |  0.0821932520000015 |         200 | FOUND     | 2021-02-07 21:24:33.832+00
            10 | https://duckduckgo.com/?q=doge+meme       | 0.01893998200000091 |         200 | NOT_FOUND | 2021-02-07 21:24:35.107+00
    (10 rows)

Or an `error`, for cases where there was no response:

    walt=> SELECT * FROM error LIMIT 10;
     error_id |                      url             |     error     |         timestamp          
    ----------+--------------------------------------+---------------+----------------------------
            1 | https://www.google.com/search?q=walt | TIMEOUT_ERROR | 2021-02-07 21:38:50.293+00
            2 | https://foobar.m.pipedream.net/p/179 | TIMEOUT_ERROR | 2021-02-07 21:42:59.343+00
            3 | https://foobar.m.pipedream.net/p/04  | TIMEOUT_ERROR | 2021-02-07 21:42:59.343+00
            4 | https://foobar.m.pipedream.net/p/01  | TIMEOUT_ERROR | 2021-02-07 21:42:59.344+00
            5 | https://foobar.m.pipedream.net/p/359 | TIMEOUT_ERROR | 2021-02-07 21:42:59.343+00
            6 | https://foobar.m.pipedream.net/p/13  | TIMEOUT_ERROR | 2021-02-07 21:42:59.343+00
            7 | https://foobar.m.pipedream.net/p/02  | TIMEOUT_ERROR | 2021-02-07 21:42:59.344+00
            8 | https://foobar.m.pipedream.net/p/11  | TIMEOUT_ERROR | 2021-02-07 21:42:59.344+00
            9 | https://foobar.m.pipedream.net/p/10  | TIMEOUT_ERROR | 2021-02-07 21:42:59.344+00
           10 | https://foobar.m.pipedream.net/p/05  | TIMEOUT_ERROR | 2021-02-07 21:42:59.343+00
    (10 rows)

## Installation

### System requirement

-   Python >= 3.8

### Install with pip

Clone the repo and install with `pip`:

    $ git clone git@github.com:scorphus/walt.git
    $ cd walt
    $ pip install

Verify the installation:

    $ walt --version

## Usage

After installation, a script is created in your local Python `bin` path. Check
how to use it with:

    $ walt --help

## Configuration

walt is configured with a [TOML][] file. Either base off of
[`config.sample.toml`][config.sample.toml] or generate a new sample:

    $ walt generate_config_sample > config.toml

Then change the configuration accordingly. These are the default values:

```toml
log_level = "INFO" # Logging level
concurrent = 2 # Number of concurrent workers checking URLs
interval = 2 # Interval between consecutive checks by the same worker
timeout = 30 # Timeout for connections

# A map of URLs and their respective regular expressions: URL = regexp pattern
[url_map]
"https://duckduckgo.com/?q=walt" = "Walt Disney"
"https://www.google.com/search?q=walt" = "Walt Disney"
"https://duckduckgo.com/?q=doge+meme" = "Kabosu"
"https://www.google.com/search?q=doge+meme" = "Kabosu"

[kafka]
uri = "localhost:9092" # Kafka server URI
cafile = "" # Certificate Authority file path
certfile = "" # Client Certificate file path
keyfile = "" # Client Private Key file path
topic = "walt" # Default topic

[postgres]
host = "localhost" # Database host address
port = 5432 # Connection port number
user = "postgres" # User name used to authenticate
password = "mysecretpassword" # Password used to authenticate
dbname = "walt" # Database name

```

You don't need to write all entries in the TOML file. The above, for instance,
does not specify the user agent and the HTTP headers:

```toml
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36"

[headers]
Pragma = "no-cache"
```

### Environment Variables

Apart from `url_map`, all other config values can be set with environment
variables. Declare them in UPPER CASE prefixed with `WALT_`. For example:

    $ env WALT_LOG_LEVEL=DEBUG WALT_TIMEOUT=17 walt generate_config_sample_from_env

## Running

### Setting up

Once you provisioned your infrastructure and configured walt accordingly, you
can start by creating the database and/or tables:

    $ walt -c config.toml create_database  # skip if the database already exists
    $ walt -c config.toml create_tables

Check [walt.tf][] if you plan to use walt with [Aiven][] database services.

### Consuming/Producing

Start the consumer with the following:

    $ walt -c config.toml consume

Start the producer with the following:

    $ walt -c config.toml produce

## Development

### Requirements

-   Python >= 3.8
-   An activated virtual environment
-   [pre-commit][]

### Create a development environment

1.  Start by creating a new Python virtual environment with the tool of your
    choice (we recommend [pyenv][])

2.  Install pre-commit (we recommend [installing][pre-commit-install] it not as
    part of the virtual environment — use your system's package manager)

3.  Install walt in editable mode with all required dependencies:

        $ make setup

### Run tests

Once you have a working development environment:

1.  Run tests

        $ make tests

2.  Check code coverage

        $ make coverage
        $ open htmlcov/index.html

3.  Lint the code:

        $ make lint

### Run locally

To help with local development, the repository includes a `docker-compose.yml`
file that can be used to run the both Kafka and Postgres — default configuration
values work with them.

    $ docker-compose up -d

Have fun!

## License

Code in this repository is distributed under the terms of the BSD 3-Clause
License (BSD-3-Clause).

See [LICENSE][] for details.

[build-badge]: https://github.com/scorphus/walt/workflows/Python/badge.svg
[action-link]: https://github.com/scorphus/walt/actions?query=workflow%3APython
[codecov-badge]: https://codecov.io/gh/scorphus/walt/branch/main/graph/badge.svg
[codecov-link]: https://codecov.io/gh/scorphus/walt
[codeclimate-badge]: https://api.codeclimate.com/v1/badges/1a6687203d55505d015d/maintainability
[codeclimate-link]: https://codeclimate.com/github/scorphus/walt/maintainability
[codacy-badge]: https://app.codacy.com/project/badge/Grade/06b3ee97b12b45abbe47bf92169b65be
[codacy-link]: https://www.codacy.com/gh/scorphus/walt/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=scorphus/walt&amp;utm_campaign=Badge_Grade
[toml]: https://gist.github.com/njsmith/78f68204c5d969f8c8bc645ef77d4a8f#summary
[config.sample.toml]: config.sample.toml
[walt.tf]: https://github.com/scorphus/walt.tf
[aiven]: https://aiven.io/
[pre-commit]: https://pre-commit.com
[pre-commit-install]: https://pre-commit.com/#install
[pyenv]: https://github.com/pyenv/pyenv
[license]: LICENSE
