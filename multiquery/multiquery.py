import os
import sys
import time
import shutil
import signal
import psutil
import logging
import argparse
import tempfile
import functools
import subprocess
import collections
import coloredlogs
from multiprocessing import Pool

QueryResult = collections.namedtuple(
    "QueryResult",
    [
        "database_name",
        "output_file",
        "stdout",
        "stderr"
    ]
)


def init_worker():
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def is_file(filename):
    if not os.path.exists(filename):
        msg = "{0} is does not exists".format(filename)
        raise argparse.ArgumentTypeError(msg)

    elif not os.path.isfile(filename):
        msg = "{0} is not a file".format(filename)
        raise argparse.ArgumentTypeError(msg)

    return os.path.abspath(os.path.realpath(os.path.expanduser(filename)))


def is_dir(dirname):
    if not os.path.exists(dirname):
        msg = "{0} is does not exists".format(dirname)
        raise argparse.ArgumentTypeError(msg)

    elif not os.path.isdir(dirname):
        msg = "{0} is not a directory".format(dirname)
        raise argparse.ArgumentTypeError(msg)

    return os.path.abspath(os.path.realpath(os.path.expanduser(dirname)))


def RunQuery(query_path, output_dir, database_path, output_format="csv", force=False, threads=None, ram=None):
    database_name = os.path.basename(database_path)
    logging.info("Running query on {}".format(database_name))

    # Create a temporary file for the results of the query.
    output_file = os.path.join(output_dir, database_name)
    logging.debug("Saving query results to {}".format(output_file))

    # CLI command to run the query.
    command = [
        "codeql",
        "database",
        "analyze",
        database_path,
        query_path,
        "--no-metadata-verification",
        "--format=%s" % output_format,
        "--output=%s" % output_file,
        "--threads=%u" % threads,
        "--ram=%u" % ram
    ]

    # Force a run even if the results are in the cache.
    if force:
        command.append("--rerun")

    # Run it and capture stdout/stderr.
    ret = subprocess.run(
        command,
        capture_output=True
    )

    # Return the result.
    result = QueryResult(
        database_name,
        output_file,
        ret.stdout,
        ret.stderr
    )

    return result


def IsCodeQLProjectDirectory(database_path):
    def absolute(filename):
        return os.path.join(database_path, filename)

    project_files = map(absolute, [".project", "codeql-database.yml"])
    return any(map(os.path.exists, project_files))


def GetAllCodeQLDataBasesInDirectory(databases_dir):
    projects = []
    for element in os.listdir(databases_dir):
        absolute_path = os.path.join(databases_dir, element)
        if not os.path.isdir(absolute_path):
            continue

        if not IsCodeQLProjectDirectory(absolute_path):
            continue

        projects.append(absolute_path)

    return projects


def CheckIfCodeQLIsInstalled():
    return shutil.which("codeql") != None


def main():
    # Check if codeql is available.
    if not CheckIfCodeQLIsInstalled():
        logging.error(
            "CodeQL binary `codeql` could not be found. Make sure to add it to the PATH.")
        return -1

    # Create a parser for our arguments.
    parser = argparse.ArgumentParser(
        description='Run a CodeQL query on multiple databases.'
    )

    # The first positional argument is the CodeQL query file.
    parser.add_argument(
        "query_file",
        type=is_file,
        help="CodeQL query file."
    )

    # The rest of the positional arguments are directories that contain CodeQL databases.
    parser.add_argument(
        "database_dirs",
        type=is_dir,
        metavar="database_dir",
        nargs="+",
        help="Directory with multiple CodeQL databaes."
    )

    # Limit the amount of databases processed.
    parser.add_argument(
        "-l",
        dest="limit",
        type=int,
        default=0,
        help="Limit the amount of databases processed."
    )

    # Enable debugging output.
    parser.add_argument(
        "-d",
        action="store_true",
        dest="debug",
        help="Set output level to DEBUG."
    )

    # Force query. Used when there are cached results in the database and we want to skip them.
    parser.add_argument(
        "-f",
        action="store_true",
        dest="force",
        help="Run query even if the results are cached."
    )

    # Set the number of CPUs to use.
    parser.add_argument(
        "-c",
        dest="cpu_count",
        type=int,
        default=(psutil.cpu_count() // 2),
        help="Set the number of CPUs to use."
    )

    # Set the amount of available ram for use.
    parser.add_argument(
        "-r",
        dest="available_ram",
        type=int,
        default=psutil.virtual_memory().total // 1048576,
        help="Available ram for use in MB."
    )

    # Set the amount of available ram for use.
    parser.add_argument(
        "-t",
        dest="threads",
        type=int,
        default=2,
        help="Number of threads to use."
    )

    # Output directory for results.
    parser.add_argument(
        "-o",
        dest="output",
        required=True,
        help="Output directory."
    )

    # Parse arguments.
    arguments = parser.parse_args()

    # Set the logging level.
    level = "DEBUG" if arguments.debug else "INFO"
    coloredlogs.install(level=level)

    # Get the output directory.
    output_dir = os.path.abspath(arguments.output)
    os.makedirs(output_dir, exist_ok=True)
    logging.info("Saving results to {}.".format(output_dir))

    # Get the query file from command line.
    query_path = os.path.abspath(arguments.query_file)
    query_name = os.path.basename(query_path)

    # Collect all the project files.
    projects = []
    for databases_dir in arguments.database_dirs:
        projects.extend(GetAllCodeQLDataBasesInDirectory(databases_dir))

    logging.info("Running query {} on {} databases.".format(
        query_name, len(projects)))

    # Limit the amount of databases processed.
    if arguments.limit and arguments.limit < len(projects):
        logging.info("Limiting the amount of databases from {} to {}".format(
            len(projects), arguments.limit))

        projects = projects[:arguments.limit]

    logging.info("Running on a pool of {} processes.".format(
        arguments.cpu_count))

    logging.info("Using {} threads per process.".format(
        arguments.threads))

    logging.info("Using {} MB of RAM per process.".format(
        arguments.available_ram))

    if arguments.force:
        logging.info("Forcing query execution.")

    # Collect findings.
    results = []

    # Measure how long it takes us to execute all queries.
    start_time = time.time()

    # Create a pool of workers.
    with Pool(arguments.cpu_count, initializer=init_worker) as pool:
        # Partially apply the target function.
        partially_applied = functools.partial(
            RunQuery,
            query_path,
            output_dir,
            threads=arguments.threads,
            ram=arguments.available_ram,
            force=arguments.force
        )

        try:
            # Execute and wait for results.
            results = pool.map(
                partially_applied,
                projects
            )

        except (KeyboardInterrupt, SystemExit):
            logging.warning("Processing interrupted by user ...")
            pool.terminate()

            # Wait for the results.
            logging.info("Waiting for results ...")
            pool.join()

    # Show extra details if loglevel is debug.
    for result in results:
        logging.debug("Database `{}`".format(result.database_name))

        if result.stdout:
            elements = result.stdout.split(b'\n')
            for e in map(lambda x: x.decode("utf-8"), elements):
                logging.debug(e)

        if result.stderr:
            elements = result.stderr.split(b'\n')
            for e in map(lambda x: x.decode("utf-8"), elements):
                logging.debug(e)

    logging.info("Running time {}.".format(time.time() - start_time))

    return 0


if __name__ == "__main__":
    main()
