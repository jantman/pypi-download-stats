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
import requests

from jinja2 import Environment, PackageLoader
from bokeh.resources import Resources

from .version import VERSION, PROJECT_URL
from .graphs import FancyAreaGraph

logger = logging.getLogger(__name__)


class OutputGenerator(object):

    # this list defines the order in which graphs will show up on the page
    GRAPH_KEYS = [
        'by-version',
        'by-file-type',
        'by-installer',
        'by-implementation',
        'by-system',
        'by-country',
        'by-distro'
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
        self._badges = {}

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
            cache_date=self._stats.as_of_datetime,
            user=getuser(),
            host=platform_node(),
            version=VERSION,
            proj_url=PROJECT_URL,
            graphs=self._graphs,
            graph_keys=self.GRAPH_KEYS,
            resources=Resources(mode='inline').render(),
            badges=self._badges
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

    def _limit_data(self, data):
        """
        Find the per-day average of each series in the data over the last 7
        days; drop all but the top 10.

        :param data: original graph data
        :type data: dict
        :return: dict containing only the top 10 series, based on average over
          the last 7 days.
        :rtype: dict
        """
        if len(data.keys()) <= 10:
            logger.debug("Data has less than 10 keys; not limiting")
            return data
        # average last 7 days of each series
        avgs = {}
        for k in data:
            if len(data[k]) <= 7:
                vals = data[k]
            else:
                vals = data[k][-7:]
            avgs[k] = sum(vals) / len(vals)
        # hold state
        final_data = {}  # final data dict
        other = []  # values for dropped/'other' series
        count = 0  # iteration counter
        # iterate the sorted averages; either drop or keep
        for k in sorted(avgs, key=avgs.get, reverse=True):
            if count < 10:
                final_data[k] = data[k]
                logger.debug("Keeping data series %s (average over last 7 "
                             "days of data: %d", k, avgs[k])
            else:
                logger.debug("Adding data series %s to 'other' (average over "
                             "last 7 days of data: %d", k, avgs[k])
                other.append(data[k])
            count += 1
        # sum up the other data and add to final
        final_data['other'] = [sum(series) for series in zip(*other)]
        return final_data

    def _generate_graph(self, name, title, stats_data, y_name):
        """
        Generate a downloads graph; append it to ``self._graphs``.

        :param name: HTML name of the graph, also used in ``self.GRAPH_KEYS``
        :type name: str
        :param title: human-readable title for the graph
        :type title: str
        :param stats_data: data dict from ``self._stats``
        :type stats_data: dict
        :param y_name: Y axis metric name
        :type y_name: str
        """
        logger.debug('Generating chart data for %s graph', name)
        orig_data, labels = self._data_dict_to_bokeh_chart_data(stats_data)
        data = self._limit_data(orig_data)
        logger.debug('Generating %s graph', name)
        script, div = FancyAreaGraph(
            name, '%s %s' % (self.project_name, title), data, labels,
            y_name).generate_graph()
        logger.debug('%s graph generated', name)
        self._graphs[name] = {
            'title': title,
            'script': script,
            'div': div,
            'raw_data': stats_data
        }

    def _generate_badges(self):
        """
        Generate download badges. Append them to ``self._badges``.
        """
        daycount = self._stats.downloads_per_day
        day = self._generate_badge('Downloads', '%d/day' % daycount)
        self._badges['per-day'] = day
        weekcount = self._stats.downloads_per_week
        if weekcount is None:
            # we don't have enough data for week (or month)
            return
        week = self._generate_badge('Downloads', '%d/week' % weekcount)
        self._badges['per-week'] = week
        monthcount = self._stats.downloads_per_month
        if monthcount is None:
            # we don't have enough data for month
            return
        month = self._generate_badge('Downloads', '%d/month' % monthcount)
        self._badges['per-month'] = month

    def _generate_badge(self, subject, status):
        """
        Generate SVG for one badge via shields.io.

        :param subject: subject; left-hand side of badge
        :type subject: str
        :param status: status; right-hand side of badge
        :type status: str
        :return: badge SVG
        :rtype: str
        """
        url = 'https://img.shields.io/badge/%s-%s-brightgreen.svg' \
              '?style=flat&maxAge=3600' % (subject, status)
        logger.debug("Getting badge for %s => %s (%s)", subject, status, url)
        res = requests.get(url)
        if res.status_code != 200:
            raise Exception("Error: got status %s for shields.io badge: %s",
                            res.status_code, res.text)
        logger.debug('Got %d character response from shields.io', len(res.text))
        return res.text

    def generate(self):
        """
        Generate all output types and write to disk.
        """
        logger.info('Generating graphs')
        self._generate_graph(
            'by-version',
            'Downloads by Version',
            self._stats.per_version_data,
            'Version'
        )
        self._generate_graph(
            'by-file-type',
            'Downloads by File Type',
            self._stats.per_file_type_data,
            'File Type'
        )
        self._generate_graph(
            'by-installer',
            'Downloads by Installer',
            self._stats.per_installer_data,
            'Installer'
        )
        self._generate_graph(
            'by-implementation',
            'Downloads by Python Implementation/Version',
            self._stats.per_implementation_data,
            'Implementation/Version'
        )
        self._generate_graph(
            'by-system',
            'Downloads by System Type',
            self._stats.per_system_data,
            'System'
        )
        self._generate_graph(
            'by-country',
            'Downloads by Country',
            self._stats.per_country_data,
            'Country'
        )
        self._generate_graph(
            'by-distro',
            'Downloads by Distro',
            self._stats.per_distro_data,
            'Distro'
        )
        self._generate_badges()
        logger.info('Generating HTML')
        html = self._generate_html()
        html_path = os.path.join(self.output_dir, 'index.html')
        with open(html_path, 'w') as fh:
            fh.write(html)
        logger.info('HTML report written to %s', html_path)
        logger.info('Writing SVG badges')
        for name, svg in self._badges.items():
            path = os.path.join(self.output_dir, '%s.svg' % name)
            with open(path, 'w') as fh:
                fh.write(svg)
            logger.info('%s badge written to: %s', name, path)


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