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
# from platform import node as platform_node
# from getpass import getuser
# import pytz
# import tzlocal
from collections import OrderedDict, defaultdict

# from jinja2 import Environment, PackageLoader

from bokeh.charts import Area, output_file, defaults, show

logger = logging.getLogger(__name__)


class OutputGenerator(object):

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
        self.stats = stats
        self.base_dir = os.path.abspath(os.path.expanduser(output_dir))
        self.output_dir = os.path.join(self.base_dir, project_name)
        if os.path.exists(self.output_dir):
            logger.debug('Removing existing per-project directory: %s',
                         self.output_dir)
            shutil.rmtree(self.output_dir)
        logger.debug('Creating per-project output directory: %s',
                     self.output_dir)
        os.makedirs(self.output_dir)

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
        Generate the graph of downloads by version.

        :return:
        :rtype:
        """
        data, labels = self._data_dict_to_bokeh_chart_data(self.stats.per_version_data)
        defaults.width = 400
        defaults.height = 400
        area2 = Area(data, x=labels, title='Downloads By Version', legend="top_left",
                     stack=True, xlabel='Date', ylabel='Downloads')
        output_file('graph.html', title='downloads by version')
        show(area)

    def generate_all(self):
        """
        Generate all output types and write to disk.
        """
        self._generate_by_version()


def filter_resource_dict_sort(d):
    """
    Used to sort a dictionary of resources, tuple-of-strings key and int value,
    sorted reverse by value and alphabetically by key within each value set.
    """
    items = list(d.items())
    keyfunc = lambda x: tuple([-x[1]] + list(x[0]))
    return OrderedDict(sorted(items, key=keyfunc))


"""
env = Environment(loader=PackageLoader('pypuppetdb_daily_report', 'templates'), extensions=['jinja2.ext.loopcontrols'])
    env.filters['reportmetricname'] = filter_report_metric_name
    env.filters['reportmetricformat'] = filter_report_metric_format
    env.filters['resourcedictsort'] = filter_resource_dict_sort
    template = env.get_template('base.html')

    run_info = {
        'version': VERSION,
        'date_s': datetime.datetime.now(pytz.utc).astimezone(tzlocal.get_localzone()).strftime('%Y-%m-%d %H:%M:%S%z %Z'),
        'host': platform_node(),
        'user': getuser(),
    }

    config = {
        'start': start_date,
        'end': end_date,
        'num_rows': NUM_RESULT_ROWS,
    }

    html = template.render(data=date_data,
                           dates=dates,
                           hostname=hostname,
                           config=config,
                           run_info=run_info,
                           )
    return html


{% for res_type, res_title in data[dates[0]]['aggregate']['nodes']['resources']['changed']|resourcedictsort  %}
{% if loop.index > config['num_rows'] %}{% break %}{% endif %}
{% set res_tup = (res_type, res_title) %}


"""

def filter_report_metric_name(s):
    """
    jinja2 filter to return the metric name for a given metric key
    """
    metric_names = {'with_skips': 'With Skipped Resources',
                    'run_time_max': 'Maximum Runtime',
                    'with_failures': 'With Failures',
                    'with_changes': 'With Changes',
                    'run_count': 'Total Reports',
                    'run_time_total': 'Total Runtime',
                    'run_time_avg': 'Average Runtime',
                    'with_no_report': 'With No Report',
                    'with_no_successful_runs': 'With 100% Failed Runs',
                    'with_50+%_failed': 'With 50-100% Failed Runs',
                    'with_too_few_runs': 'With <{n} Runs in 24h'.format(n=RUNS_PER_DAY),
                    }
    return metric_names.get(s, s)


def filter_report_metric_format(o):
    """
    jinja2 filter to return a formatted metric string for the given metric value
    """
    if isinstance(o, str):
        return o
    if isinstance(o, int):
        return '{o}'.format(o=o)
    if isinstance(o, datetime.timedelta):
        d = delta2dict(o)
        s = ''
        for i in ['day', 'hour', 'minute', 'second']:
            if d[i] > 0:
                s += '{i}{suffix} '.format(i=d[i], suffix=i[0])
        s = s.strip()
        return s
    return str(o)
