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
from datetime import datetime, timedelta
from pytz import utc
from tzlocal import get_localzone
from iso3166 import countries
from math import ceil

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
        self.cache_data = {}
        self.cache_dates = self._get_cache_dates()
        self.as_of_timestamp = self._cache_get(
            self.cache_dates[-1])['cache_metadata']['data_ts']
        self.as_of_datetime = datetime.fromtimestamp(
            self.as_of_timestamp, utc).astimezone(get_localzone())

    def _get_cache_dates(self):
        """
        Get s list of dates (:py:class:`datetime.datetime`) present in cache,
        beginning with the longest contiguous set of dates that isn't missing
        more than one date in series.

        :return: list of datetime objects for contiguous dates in cache
        :rtype: list
        """
        all_dates = self.cache.get_dates_for_project(self.project_name)
        dates = []
        last_date = None
        for val in sorted(all_dates):
            if last_date is None:
                last_date = val
                continue
            if val - last_date > timedelta(hours=48):
                # reset dates to start from here
                logger.warning("Last cache date was %s, current date is %s; "
                               "delta is too large. Starting cache date series "
                               "at current date.", last_date, val)
                dates = []
            last_date = val
            dates.append(val)
        # find the first download record, and only look at dates after that
        for idx, cache_date in enumerate(dates):
            data = self._cache_get(cache_date)
            if not self._is_empty_cache_record(data):
                logger.debug("First cache date with data: %s", cache_date)
                return dates[idx:]
        return dates

    def _is_empty_cache_record(self, rec):
        """
        Return True if the specified cache record has no data, False otherwise.

        :param rec: cache record returned by :py:meth:`~._cache_get`
        :type rec: dict
        :return: True if record is empty, False otherwise
        :rtype: bool
        """
        # these are taken from DataQuery.query_one_table()
        for k in [
            'by_version',
            'by_file_type',
            'by_installer',
            'by_implementation',
            'by_system',
            'by_distro',
            'by_country'
        ]:
            if k in rec and len(rec[k]) > 0:
                return False
        return True

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

    @staticmethod
    def _alpha2_to_country(alpha2):
        """
        Try to look up an alpha2 country code from the iso3166 package; return
        the returned name if available, otherwise the original value. Returns
        "unknown" (str) for None.

        :param alpha2: alpha2 country code
        :type alpha2: str
        :return: country name, or original value if not found
        :rtype: str
        """
        if alpha2 is None:
            return 'unknown'
        try:
            return countries.get(alpha2).name
        except KeyError:
            return alpha2

    @staticmethod
    def _column_value(orig_val):
        """
        Munge a BigQuery column value to what we want to store; currently
        just turns ``None`` into the String "unknown".

        :param orig_val: original field value
        :return: field value we cache/display
        :rtype: str
        """
        if orig_val is None or orig_val == 'null':
            return 'unknown'
        return orig_val

    @staticmethod
    def _compound_column_value(k1, k2):
        """
        Like :py:meth:`~._column_value` but collapses two unknowns into one.

        :param k1: first (top-level) value
        :param k2: second (bottom-level) value
        :return: display key
        :rtype: str
        """
        k1 = ProjectStats._column_value(k1)
        k2 = ProjectStats._column_value(k2)
        if k1 == 'unknown' and k2 == 'unknown':
            return 'unknown'
        return '%s %s' % (k1, k2)

    @staticmethod
    def _shorten_version(ver, num_components=2):
        """
        If ``ver`` is a dot-separated string with at least (num_components +1)
        components, return only the first two. Else return the original string.

        :param ver: version string
        :type ver: str
        :return: shortened (major, minor) version
        :rtype: str
        """
        parts = ver.split('.')
        if len(parts) <= num_components:
            return ver
        return '.'.join(parts[:num_components])

    @property
    def per_version_data(self):
        """
        Return download data by version.

        :return: dict of cache data; keys are datetime objects, values are
          dict of version (str) to count (int)
        :rtype: dict
        """
        ret = {}
        for cache_date in self.cache_dates:
            data = self._cache_get(cache_date)
            if len(data['by_version']) == 0:
                data['by_version'] = {'other': 0}
            ret[cache_date] = data['by_version']
        return ret

    @property
    def per_file_type_data(self):
        """
        Return download data by file type.

        :return: dict of cache data; keys are datetime objects, values are
          dict of file type (str) to count (int)
        :rtype: dict
        """
        ret = {}
        for cache_date in self.cache_dates:
            data = self._cache_get(cache_date)
            if len(data['by_file_type']) == 0:
                data['by_file_type'] = {'other': 0}
            ret[cache_date] = data['by_file_type']
        return ret

    @property
    def per_installer_data(self):
        """
        Return download data by installer name and version.

        :return: dict of cache data; keys are datetime objects, values are
          dict of installer name/version (str) to count (int).
        :rtype: dict
        """
        ret = {}
        for cache_date in self.cache_dates:
            data = self._cache_get(cache_date)
            ret[cache_date] = {}
            for inst_name, inst_data in data['by_installer'].items():
                for inst_ver, count in inst_data.items():
                    k = self._compound_column_value(
                        inst_name,
                        self._shorten_version(inst_ver)
                    )
                    ret[cache_date][k] = count
            if len(ret[cache_date]) == 0:
                ret[cache_date]['unknown'] = 0
        return ret

    @property
    def per_implementation_data(self):
        """
        Return download data by python impelementation name and version.

        :return: dict of cache data; keys are datetime objects, values are
          dict of implementation name/version (str) to count (int).
        :rtype: dict
        """
        ret = {}
        for cache_date in self.cache_dates:
            data = self._cache_get(cache_date)
            ret[cache_date] = {}
            for impl_name, impl_data in data['by_implementation'].items():
                for impl_ver, count in impl_data.items():
                    k = self._compound_column_value(
                        impl_name,
                        self._shorten_version(impl_ver)
                    )
                    ret[cache_date][k] = count
            if len(ret[cache_date]) == 0:
                ret[cache_date]['unknown'] = 0
        return ret

    @property
    def per_system_data(self):
        """
        Return download data by system.

        :return: dict of cache data; keys are datetime objects, values are
          dict of system (str) to count (int)
        :rtype: dict
        """
        ret = {}
        for cache_date in self.cache_dates:
            data = self._cache_get(cache_date)
            ret[cache_date] = {
                self._column_value(x): data['by_system'][x]
                for x in data['by_system']
            }
            if len(ret[cache_date]) == 0:
                ret[cache_date]['unknown'] = 0
        return ret

    @property
    def per_country_data(self):
        """
        Return download data by country.

        :return: dict of cache data; keys are datetime objects, values are
          dict of country (str) to count (int)
        :rtype: dict
        """
        ret = {}
        for cache_date in self.cache_dates:
            data = self._cache_get(cache_date)
            ret[cache_date] = {}
            for cc, count in data['by_country'].items():
                k = '%s (%s)' % (self._alpha2_to_country(cc), cc)
                ret[cache_date][k] = count
            if len(ret[cache_date]) == 0:
                ret[cache_date]['unknown'] = 0
        return ret

    @property
    def per_distro_data(self):
        """
        Return download data by distro name and version.

        :return: dict of cache data; keys are datetime objects, values are
          dict of distro name/version (str) to count (int).
        :rtype: dict
        """
        ret = {}
        for cache_date in self.cache_dates:
            data = self._cache_get(cache_date)
            ret[cache_date] = {}
            for distro_name, distro_data in data['by_distro'].items():
                if distro_name.lower() == 'red hat enterprise linux server':
                    distro_name = 'RHEL'
                for distro_ver, count in distro_data.items():
                    ver = self._shorten_version(distro_ver, num_components=1)
                    if distro_name.lower() == 'os x':
                        ver = self._shorten_version(distro_ver,
                                                    num_components=2)
                    k = self._compound_column_value(distro_name, ver)
                    ret[cache_date][k] = count
            if len(ret[cache_date]) == 0:
                ret[cache_date]['unknown'] = 0
        return ret

    @property
    def downloads_per_day(self):
        """
        Return the number of downloads per day, averaged over the past 7 days
        of data.

        :return: average number of downloads per day
        :rtype: int
        """
        count, num_days = self._downloads_for_num_days(7)
        res = ceil(count / num_days)
        logger.debug("Downloads per day = (%d / %d) = %d", count, num_days, res)
        return res

    @property
    def downloads_per_week(self):
        """
        Return the number of downloads in the last 7 days.

        :return: number of downloads in the last 7 days; if we have less than
          7 days of data, returns None.
        :rtype: int
        """
        if len(self.cache_dates) < 7:
            logger.error("Only have %d days of data; cannot calculate "
                         "downloads per week", len(self.cache_dates))
            return None
        count, _ = self._downloads_for_num_days(7)
        logger.debug("Downloads per week = %d", count)
        return count

    @property
    def downloads_per_month(self):
        """
        Return the number of downloads in the last 30 days.

        Uses :py:meth:`~._downloads_for_num_days` to retrieve the data.

        :return: number of downloads in the last 30 days; if we have less than
          30 days of data, returns None.
        :rtype: int
        """
        if len(self.cache_dates) < 30:
            logger.error("Only have %d days of data; cannot calculate "
                         "downloads per month", len(self.cache_dates))
            return None
        count, _ = self._downloads_for_num_days(30)
        logger.debug("Downloads per month = %d", count)
        return count

    def _downloads_for_num_days(self, num_days):
        """
        Given a number of days of historical data to look at (starting with
        today and working backwards), return the total number of downloads
        for that time range, and the number of days of data we had (in cases
        where we had less data than requested).

        :param num_days: number of days of data to look at
        :type num_days: int
        :return: 2-tuple of (download total, number of days of data)
        :rtype: tuple
        """
        logger.debug("Getting download total for last %d days", num_days)
        dates = self.cache_dates
        logger.debug("Cache has %d days of data", len(dates))
        if len(dates) > num_days:
            dates = dates [(-1 * num_days):]
        logger.debug("Looking at last %d days of data", len(dates))
        dl_sum = 0
        for cache_date in dates:
            data = self._cache_get(cache_date)
            dl_sum += sum(data['by_version'].values())
        logger.debug("Sum of download counts: %d", dl_sum)
        return dl_sum, len(dates)