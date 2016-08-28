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
import json
import re
from datetime import datetime
import time

from pypi_download_stats.version import VERSION

logger = logging.getLogger(__name__)


class DiskDataCache(object):

    def __init__(self, cache_path):
        """
        Initialize the disk data cache.

        :param cache_path: absolute path to the cache directory
        :type cache_path: str
        """
        cache_path = os.path.abspath(os.path.expanduser(cache_path))
        if not os.path.exists(cache_path):
            logger.debug('Creating cache directory: %s', cache_path)
            os.makedirs(cache_path)
        logger.info('Initialized DiskDataCache cache_path=%s', cache_path)
        self.cache_path = cache_path

    def _path_for_file(self, project_name, date):
        """
        Generate the path on disk for a specified project and date.

        :param project_name: the PyPI project name for the data
        :type project: str
        :param date: the date for the data
        :type date: datetime.datetime
        :return: path for where to store this data on disk
        :rtype: str
        """
        return os.path.join(
            self.cache_path,
            '%s_%s.json' % (project_name, date.strftime('%Y%m%d'))
        )

    def get(self, project, date):
        """
        Get the cache data for a specified project for the specified date.
        Returns None if the data cannot be found in the cache.

        :param project: PyPi project name to get data for
        :type project: str
        :param date: date to get data for
        :type date: datetime.datetime
        :return: dict of per-date data for project
        :rtype: :py:obj:`dict` or ``None``
        """
        fpath = self._path_for_file(project, date)
        logger.debug('Cache GET project=%s date=%s - path=%s',
                     project, date.strftime('%Y-%m-%d'), fpath)
        try:
            with open(fpath, 'r') as fh:
                data = json.loads(fh.read())
        except:
            logger.debug('Error getting from cache for project=%s date=%s',
                         project, date.strftime('%Y-%m-%d'))
            return None
        data['cache_metadata']['date'] = datetime.strptime(
            data['cache_metadata']['date'],
            '%Y%m%d'
        )
        data['cache_metadata']['updated'] = datetime.fromtimestamp(
            data['cache_metadata']['updated']
        )
        return data

    def set(self, project, date, data, data_ts):
        """
        Set the cache data for a specified project for the specified date.

        :param project: project name to set data for
        :type project: str
        :param date: date to set data for
        :type date: datetime.datetime
        :param data: data to cache
        :type data: dict
        :param data_ts: maximum timestamp in the BigQuery data table
        :type data_ts: int
        """
        data['cache_metadata'] = {
            'project': project,
            'date': date.strftime('%Y%m%d'),
            'updated': time.time(),
            'version': VERSION,
            'data_ts': data_ts
        }
        fpath = self._path_for_file(project, date)
        logger.debug('Cache SET project=%s date=%s - path=%s',
                     project, date.strftime('%Y-%m-%d'), fpath)
        with open(fpath, 'w') as fh:
            fh.write(json.dumps(data))

    def get_dates_for_project(self, project):
        """
        Return a list of the dates we have in cache for the specified project,
        sorted in ascending date order.

        :param project: project name
        :type project: str
        :return: list of datetime.datetime objects
        :rtype: datetime.datetime
        """
        file_re = re.compile(r'^%s_([0-9]{8})\.json$' % project)
        all_dates = []
        for f in os.listdir(self.cache_path):
            if not os.path.isfile(os.path.join(self.cache_path, f)):
                continue
            m = file_re.match(f)
            if m is None:
                continue
            all_dates.append(datetime.strptime(m.group(1), '%Y%m%d'))
        return sorted(all_dates)
