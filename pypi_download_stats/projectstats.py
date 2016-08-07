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

logger = logging.getLogger(__name__)


class ProjectStats(object):

    def __init__(self, project_name, cache_instance):
        """
        Initialize a ProjectStats class for the specified project.
        :param project_name: project name to calculate stats for
        :type project_name: str
        :param cache_instance: DataCache instance
        :type cache_instance: :py:class:`~.DiskDataCache`
        """
        logger.debug('Initializing ProjectStats for project: %s', project_name)
        self.project_name = project_name
        self.cache = cache_instance
        self.cache_dates = self.cache.get_dates_for_project(project_name)
        self.cache_data = {}
        self.as_of_date = self._cache_get(
            self.cache_dates[-1])['cache_metadata']['updated']

    def _cache_get(self, date):
        """
        Return cache data for the specified day; cache locally in this class.

        :param date: date to get data for
        :type date: datetime.datetime
        :return: cache data for date
        :rtype: dict
        """
        if date in self.cache_data:
            logger.debug('Using class-cached data for date %s',
                         date.strftime('%Y-%m-%d'))
            return self.cache_data[date]
        logger.debug('Getting data from cache for date %s',
                     date.strftime('%Y-%m-%d'))
        data = self.cache.get(self.project_name, date)
        self.cache_data[date] = data
        return data

    @property
    def per_version_data(self):
        """
        Return download data by version for num_days

        :return: dict of cache data; keys are datetime objects, values are
          dict of version (str) to count (int)
        :rtype: dict
        """
        ret = {}
        for cache_date in self.cache_dates:
            data = self._cache_get(cache_date)
            ret[cache_date] = data['by_project_version']
        return ret
