"""
The latest version of this package is available at:
<http://github.com/jantman/pypi-download-stats>

##################################################################################
Copyright 2016 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

    This file is part of pypi-download-stats, also known as pypi-download-stats.

    pypi-download-stats is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    pypi-download-stats is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with pypi-download-stats.  If not, see <http://www.gnu.org/licenses/>.

The Copyright and Authors attributions contained herein may not be removed or
otherwise altered, except to add the Author attribution of a contributor to
this work. (Additional Terms pursuant to Section 7b of the AGPL v3)
##################################################################################
While not legally required, I sincerely request that anyone who finds
bugs please submit them at <https://github.com/jantman/pypi-download-stats> or
to me via email, and that you send any contributions or improvements
either as a pull request on GitHub, or to me via email.
##################################################################################

AUTHORS:
Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>
##################################################################################
"""

import sys
import argparse
import logging
import os

try:
    import xmlrpclib
except ImportError:
    import xmlrpc.client as xmlrpclib

from pypi_download_stats.dataquery import DataQuery
from pypi_download_stats.diskdatacache import DiskDataCache
from pypi_download_stats.outputgenerator import OutputGenerator
from pypi_download_stats.projectstats import ProjectStats
from pypi_download_stats.version import PROJECT_URL, VERSION

FORMAT = "[%(asctime)s %(levelname)s] %(message)s"
logging.basicConfig(level=logging.WARNING, format=FORMAT)
logger = logging.getLogger()

# suppress googleapiclient internal logging below WARNING level
googleapiclient_log = logging.getLogger("googleapiclient")
googleapiclient_log.setLevel(logging.WARNING)
googleapiclient_log.propagate = True

# suppress oauth2client internal logging below WARNING level
oauth2client_log = logging.getLogger("oauth2client")
oauth2client_log.setLevel(logging.WARNING)
oauth2client_log.propagate = True


def parse_args(argv):
    """
    Use Argparse to parse command-line arguments.

    :param argv: list of arguments to parse (``sys.argv[1:]``)
    :type argv: list
    :return: parsed arguments
    :rtype: :py:class:`argparse.Namespace`
    """
    p = argparse.ArgumentParser(
        description='pypi-download-stats - Calculate detailed download stats '
                    'and generate HTML and badges for PyPI packages - '
                    '<%s>' % PROJECT_URL,
        prog='pypi-download-stats'
    )
    p.add_argument('-V', '--version', action='version',
                   version='%(prog)s ' + VERSION)
    p.add_argument('-v', '--verbose', dest='verbose', action='count',
                   default=0,
                   help='verbose output. specify twice for debug-level output.')
    m = p.add_mutually_exclusive_group()
    m.add_argument('-Q', '--no-query', dest='query', action='store_false',
                   default=True, help='do not query; just generate output '
                                      'from cached data')
    m.add_argument('-G', '--no-generate', dest='generate', action='store_false',
                   default=True, help='do not generate output; just query '
                                      'data and cache results')
    p.add_argument('-o', '--out-dir', dest='out_dir', action='store', type=str,
                   default='./pypi-stats', help='output directory (default: '
                                                './pypi-stats')
    p.add_argument('-p', '--project-id', dest='project_id', action='store',
                   type=str, default=None,
                   help='ProjectID for your Google Cloud user, if not using '
                        'service account credentials JSON file')
    # @TODO this is tied to the DiskDataCache class
    p.add_argument('-c', '--cache-dir', dest='cache_dir', action='store',
                   type=str, default='./pypi-stats-cache',
                   help='stats cache directory (default: ./pypi-stats-cache)')
    p.add_argument('-B', '--backfill-num-days', dest='backfill_days', type=int,
                   action='store', default=7,
                   help='number of days of historical data to backfill, if '
                        'missing (defaut: 7). Note this may incur BigQuery '
                        'charges. Set to -1 to backfill all available history.')
    g = p.add_mutually_exclusive_group()
    g.add_argument('-P', '--project', dest='PROJECT', action='append', type=str,
                   help='project name to query/generate stats for (can be '
                        'specified more than once; '
                        'this will reduce query cost for multiple projects)')
    g.add_argument('-U', '--user', dest='user', action='store', type=str,
                   help='Run for all PyPI projects owned by the specified'
                        'user.')
    args = p.parse_args(argv)
    return args


def set_log_info():
    """set logger level to INFO"""
    set_log_level_format(logging.INFO,
                         '%(asctime)s %(levelname)s:%(name)s:%(message)s')


def set_log_debug():
    """set logger level to DEBUG, and debug-level output format"""
    set_log_level_format(
        logging.DEBUG,
        "%(asctime)s [%(levelname)s %(filename)s:%(lineno)s - "
        "%(name)s.%(funcName)s() ] %(message)s"
    )


def set_log_level_format(level, format):
    """
    Set logger level and format.

    :param level: logging level; see the :py:mod:`logging` constants.
    :type level: int
    :param format: logging formatter format string
    :type format: str
    """
    formatter = logging.Formatter(fmt=format)
    logger.handlers[0].setFormatter(formatter)
    logger.setLevel(level)


def _pypi_get_projects_for_user(username):
    """
    Given the username of a PyPI user, return a list of all of the user's
    projects from the XMLRPC interface.

    See: https://wiki.python.org/moin/PyPIXmlRpc

    :param username: PyPI username
    :type username: str
    :return: list of string project names
    :rtype: list
    """
    client = xmlrpclib.ServerProxy('https://pypi.python.org/pypi')
    pkgs = client.user_packages(username)  # returns [role, package]
    return [x[1] for x in pkgs]


def main(args=None):
    """
    Main entry point
    """
    # parse args
    if args is None:
        args = parse_args(sys.argv[1:])

    # set logging level
    if args.verbose > 1:
        set_log_debug()
    elif args.verbose == 1:
        set_log_info()

    outpath = os.path.abspath(os.path.expanduser(args.out_dir))
    cachepath = os.path.abspath(os.path.expanduser(args.cache_dir))
    cache = DiskDataCache(cache_path=cachepath)

    if args.user:
        args.PROJECT = _pypi_get_projects_for_user(args.user)

    if args.query:
        DataQuery(args.project_id, args.PROJECT, cache).run_queries(
            backfill_num_days=args.backfill_days)
    else:
        logger.warning('Query disabled by command-line flag; operating on '
                       'cached data only.')
    if not args.generate:
        logger.warning('Output generation disabled by command-line flag; '
                       'exiting now.')
        raise SystemExit(0)
    for proj in args.PROJECT:
        logger.info('Generating output for: %s', proj)
        stats = ProjectStats(proj, cache)
        outdir = os.path.join(outpath, proj)
        OutputGenerator(proj, stats, outdir).generate()


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    main(args)
