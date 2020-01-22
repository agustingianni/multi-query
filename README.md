# multi-query

Run a single query on multiple CodeQL databases in paralel.

## Installation

You can install `multiquery` using pip. This will create a binary on your system called `multiquery` that you can use to run queries. If you prefer not installing it you can run it from the source directory, but make sure you install the dependencies listed in `setup.py`.

```sh
pip install --user multiquery
```

## Usage

If you do not plan on installing `multi-query` via pip, you can go to the source directory and run it directly as follows:

```sh
export PATH="$PATH:$HOME/semmle/codeql"
export QUERY_FILE="$HOME/semmle/queries/openssl-x509-check-host-return.ql"
export DATABASES="$HOME/semmle/databases"
python -m multiquery.multiquery $QUERY_FILE $DATABASES -o reports
```

If you have the binary installed on your system the command line is very similar:

```sh
export PATH="$PATH:$HOME/semmle/codeql"
export QUERY_FILE="$HOME/semmle/queries/openssl-x509-check-host-return.ql"
export DATABASES="$HOME/semmle/databases"
multiquery $QUERY_FILE $DATABASES -o reports
```

## Command line options

```sh
usage: multiquery.py [-h] [-l LIMIT] [-d] [-f] [-c CPU_COUNT]
                     [-r AVAILABLE_RAM] [-t THREADS] -o OUTPUT
                     query_file database_dir [database_dir ...]

Run a CodeQL query on multiple databases.

positional arguments:
  query_file        CodeQL query file.
  database_dir      Directory with multiple CodeQL databaes.

optional arguments:
  -h, --help        show this help message and exit
  -l LIMIT          Limit the amount of databases processed.
  -d                Set output level to DEBUG.
  -f                Run query even if the results are cached.
  -c CPU_COUNT      Set the number of CPUs to use.
  -r AVAILABLE_RAM  Available ram for use in MB.
  -t THREADS        Number of threads to use.
  -o OUTPUT         Output directory.
```

## User options

With `multiquery` I tried to set some sane default parameters that will run on every system with decent performance. That said, you are encouraged to change them and see what gives you better performance.

### Output directory

Use `-o` to collect all the results of the queries. If the directory does not exists, it will be created. If instead it exists, it refresh old results (that is, we overwrite old queries with the same output name).

### CPU count

By default `multiquery` uses half of the available CPUs. This option has proven (in my experience) to be the sweetspot for performance. If if wish to change it, use the option `-c` on the command line.

### Available RAM

This option (`-r`) controls the amount of RAM (in MB) available for every single instance of `codeql`. By default we use the whole RAM and let `codeql` use as much memory as it needs. Depending on the size of your databases you may want to change this option.

### Available threads

Sets the amount of processing threads `codeql` can use. By default we use 2 threads.

## Development options

The following options are interesting if you want to make changes to `multiquery`.

### Avoid cached results

`codeql` caches the results of queries in order to avoid wasting cpu cycles. If you for some reason need to run a query even though it cached, please use the option `-f` to force the query.

### Getting debug output

Enable debugging information by passing the option `-d` on the command line. This option will enable some extra information that can be useful for debugging purposes, like getting the output of `stderr` and `stdout` from the `codeql` process.

### Limiting the number of databases

By using the command line option `-l` you can limit the amount of databases your query will process. This is mainly a development feature that will most likely be of little use for users.

## Author

Agustin Gianni / agustingianni@gmail.com / @agustingianni
