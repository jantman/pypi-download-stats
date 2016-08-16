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

import logging
import os
import shutil
from platform import node as platform_node
from getpass import getuser
from datetime import datetime
from collections import OrderedDict, defaultdict

import pytz
import tzlocal
from jinja2 import Environment, PackageLoader
from bokeh.resources import Resources

from .version import VERSION, PROJECT_URL
from .graphs import FancyAreaGraph

logger = logging.getLogger(__name__)


class OutputGenerator(object):

    # this list defines the order in which graphs will show up on the page
    GRAPH_KEYS = [
        'by-version'
    ]

    def __init__(self, project_name, stats, output_dir):
        """
        Initialize an OutputGenerator for one project.

        :param project_name: name of the project to generate output for
        :type project_name: str
        :param stats: ProjectStats instance for the project
        :type stats: :py:class:`~.ProjectStats`hey
        :param output_dir: path to write project output to
        :type output_dir: str
        """
        logger.debug('Initializing OutputGenerator for project %s '
                     '(output_dir=%s)', project_name, output_dir)
        self.project_name = project_name
        self._stats = stats
        self.output_dir = os.path.abspath(os.path.expanduser(output_dir))
        if os.path.exists(self.output_dir):
            logger.debug('Removing existing per-project directory: %s',
                         self.output_dir)
            shutil.rmtree(self.output_dir)
        logger.debug('Creating per-project output directory: %s',
                     self.output_dir)
        os.makedirs(self.output_dir)
        self._graphs = {}

    def _generate_html(self):
        """
        Generate the HTML for the specified graphs.

        :return:
        :rtype:
        """
        logger.debug('Generating templated HTML')
        env = Environment(
            loader=PackageLoader('pypi_download_stats', 'templates'),
            extensions=['jinja2.ext.loopcontrols'])
        env.filters['format_date_long'] = filter_format_date_long
        env.filters['format_date_ymd'] = filter_format_date_ymd
        env.filters['data_columns'] = filter_data_columns
        template = env.get_template('base.html')

        logger.debug('Rendering template')
        html = template.render(
            project=self.project_name,
            curr_date=datetime.now(
                pytz.utc).astimezone(tzlocal.get_localzone()),
            user=getuser(),
            host=platform_node(),
            version=VERSION,
            proj_url=PROJECT_URL,
            graphs=self._graphs,
            graph_keys=self.GRAPH_KEYS,
            resources=Resources(mode='inline').render()
        )
        logger.debug('Template rendered')
        return html

    def _data_dict_to_bokeh_chart_data(self, data):
        """
        Take a dictionary of data, as returned by the :py:class:`~.ProjectStats`
        per_*_data properties, return a 2-tuple of data dict and x labels list
        usable by bokeh.charts.

        :param data: data dict from :py:class:`~.ProjectStats` property
        :type data: dict
        :return: 2-tuple of data dict, x labels list
        :rtype: tuple
        """
        labels = []
        # find all the data keys
        keys = set()
        for date in data:
            for k in data[date]:
                keys.add(k)
        # final output dict
        out_data = {}
        for k in keys:
            out_data[k] = []
        # transform the data; deal with sparse data
        for data_date, data_dict in sorted(data.items()):
            labels.append(data_date)
            for k in out_data:
                if k in data_dict:
                    out_data[k].append(data_dict[k])
                else:
                    out_data[k].append(0)
        return out_data, labels

    def _generate_by_version(self):
        """
        Generate the graph of downloads by version; append it to
        ``self._graphs``.
        """
        logger.debug('Generating chart data for by-version graph')
        data, labels = self._data_dict_to_bokeh_chart_data(
            self._stats.per_version_data)
        logger.debug('Generating by-version graph')
        title = 'Downloads by Version'
        script, div = FancyAreaGraph(
            'by-version', '%s %s' % (self.project_name, title), data, labels,
            'Version').generate_graph()
        logger.debug('by-version graph generated')
        self._graphs['by-version'] = {
            'title': title,
            'script': script,
            'div': div,
            'raw_data': self._stats.per_version_data
        }

    def generate(self):
        """
        Generate all output types and write to disk.
        """
        logger.info('Generating graphs')
        self._generate_by_version()
        logger.info('Generating HTML')
        html = self._generate_html()
        html_path = os.path.join(self.output_dir, 'index.html')
        with open(html_path, 'w') as fh:
            fh.write(html)
        logger.info('HTML report written to %s', html_path)


def filter_format_date_long(dt):
    """
    Format a datetime into a long string

    :param dt: datetime to format
    :type dt: datetime.datetime
    :returns: long date string
    :rtype: str
    """
    return dt.strftime('%Y-%m-%d %H:%M:%S%z (%Z)')


def filter_format_date_ymd(dt):
    """
    Format a datetime into a Y-m-d string

    :param dt: datetime to format
    :type dt: datetime.datetime
    :returns: Y-m-d date string
    :rtype: str
    """
    return dt.strftime('%Y-%m-%d')


def filter_data_columns(data):
    """
    Given a dict of data such as those in :py:class:`~.ProjectStats` attributes,
    made up of :py:class:`datetime.datetime` keys and values of dicts of column
    keys to counts, return a list of the distinct column keys in sorted order.

    :param data: data dict as returned by ProjectStats attributes
    :type data: dict
    :return: sorted list of distinct keys
    :rtype: list
    """
    keys = set()
    for dt, d in data.items():
        for k in d:
            keys.add(k)
    return sorted([x for x in keys])