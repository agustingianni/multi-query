import os
import time
import shutil
import signal
import psutil
import logging
import argparse
import subprocess
import collections
import coloredlogs
from multiprocessing import Pool

UpdateResult = collections.namedtuple(
    "UpdateResult",
    [
        "database_name",
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


def UpdateDatabase(database_path):
    database_name = os.path.basename(database_path)
    logging.info("Updating database {}".format(database_name))

    # CLI command to update the database.
    command = [
        "codeql",
        "database",
        "upgrade",
        database_path
    ]

    # Run it and capture stdout/stderr.
    ret = subprocess.run(
        command,
        capture_output=True
    )

    # Return the result.
    result = UpdateResult(
        database_name,
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
        description='Update multiple CodeQL databases.'
    )

    # The rest of the positional arguments are directories that contain CodeQL databases.
    parser.add_argument(
        "database_dirs",
        type=is_dir,
        metavar="database_dir",
        nargs="+",
        help="Directory with multiple CodeQL databaes."
    )

    # Enable debugging output.
    parser.add_argument(
        "-d",
        action="store_true",
        dest="debug",
        help="Set output level to DEBUG."
    )

    # Set the number of CPUs to use.
    parser.add_argument(
        "-c",
        dest="cpu_count",
        type=int,
        default=(psutil.cpu_count() // 2),
        help="Set the number of CPUs to use."
    )

    # Parse arguments.
    arguments = parser.parse_args()

    # Set the logging level.
    level = "DEBUG" if arguments.debug else "INFO"
    coloredlogs.install(level=level)

    # Collect all the project files.
    projects = []
    for databases_dir in arguments.database_dirs:
        projects.extend(GetAllCodeQLDataBasesInDirectory(databases_dir))

    logging.info("Updating {} databases.".format(len(projects)))

    logging.info("Running on a pool of {} processes.".format(
        arguments.cpu_count))

    # Measure how long it takes us to execute all queries.
    start_time = time.time()

    # Create a pool of workers.
    with Pool(arguments.cpu_count, initializer=init_worker) as pool:
        try:
            # Execute and wait for results.
            results = pool.map(
                UpdateDatabase,
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
