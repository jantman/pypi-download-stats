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
import re
import os
import json
from datetime import datetime, timedelta

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client.client import GoogleCredentials

logger = logging.getLogger(__name__)


class DataQuery(object):

    _PROJECT_ID = 'the-psf'
    _DATASET_ID = 'pypi'
    _table_re = re.compile(r'^downloads([0-9]{8})$')

    def __init__(self, project_id, project_names, cache_instance):
        """
        Initialize the class to query BigQuery data for the specified projects.

        :param project_id: the Project ID for the user you're authenticating as;
          if omitted will attempt to find this in the JSON file at the path
          specified by the ``GOOGLE_APPLICATION_CREDENTIALS`` environment
          variable.
        :type project_id: str
        :param project_names: list of string project names to query for
        :type project_names: list
        :param cache_instance: DataCache instance
        :type cache_instance: :py:class:`~.DiskDataCache`
        """
        logger.info('Initializing DataQuery for projects: %s',
                    ', '.join(project_names))
        self.project_id = project_id
        if project_id is None:
            self.project_id = self._get_project_id()
        logger.debug('project_id to run queries from: %s', self.project_id)
        self.cache = cache_instance
        self.projects = project_names
        self.service = self._get_bigquery_service()

    def _dict_for_projects(self):
        """
        Return a dict whose keys are each project name we're querying for, and
        values are empty dicts.

        :return: dict with project name keys and empty dict values
        :rtype: dict
        """
        d = {}
        for p in self.projects:
            d[p] = {}
        return d

    def _get_project_id(self):
        """
        Get our projectId from the ``GOOGLE_APPLICATION_CREDENTIALS`` creds
        JSON file.

        :return: project ID
        :rtype: str
        """
        fpath = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', None)
        if fpath is None:
            raise Exception('ERROR: No project ID specified, and '
                            'GOOGLE_APPLICATION_CREDENTIALS env var is not set')
        fpath = os.path.abspath(os.path.expanduser(fpath))
        logger.debug('Reading credentials file at %s to get project_id', fpath)
        with open(fpath, 'r') as fh:
            cred_data = json.loads(fh.read())
        return cred_data['project_id']

    def _get_bigquery_service(self):
        """
        Connect to the BigQuery service.

        Calling ``GoogleCredentials.get_application_default`` requires that
        you either be running in the Google Cloud, or have the
        ``GOOGLE_APPLICATION_CREDENTIALS`` environment variable set to the path
        to a credentials JSON file.

        :return: authenticated BigQuery service connection object
        :rtype: `googleapiclient.discovery.Resource <http://google.github.io/\
google-api-python-client/docs/epy/googleapiclient.discovery.\
Resource-class.html>`_
        """
        logger.debug('Getting Google Credentials')
        credentials = GoogleCredentials.get_application_default()
        logger.debug('Building BigQuery service instance')
        bigquery_service = build('bigquery', 'v2', credentials=credentials)
        return bigquery_service

    def _get_download_table_ids(self):
        """
        Get a list of PyPI downloads table (sharded per day) IDs.

        :return: list of table names (strings)
        :rtype: list
        """
        all_table_names = []  # matching per-date table names
        logger.info('Querying for all tables in dataset')
        tables = self.service.tables()
        request = tables.list(projectId=self._PROJECT_ID,
                              datasetId=self._DATASET_ID)
        while request is not None:
            response = request.execute()
            for table in response['tables']:
                if table['type'] != 'TABLE':
                    logger.debug('Skipping %s (type=%s)',
                                 table['tableReference']['tableId'],
                                 table['type'])
                    continue
                if not self._table_re.match(table['tableReference']['tableId']):
                    logger.debug('Skipping table with non-matching name: %s',
                                 table['tableReference']['tableId'])
                    continue
                all_table_names.append(table['tableReference']['tableId'])
            request = tables.list_next(previous_request=request,
                                       previous_response=response)
        return sorted(all_table_names)

    def _datetime_for_table_name(self, table_name):
        """
        Return a :py:class:`datetime.datetime` object for the date of the
        data in the specified table name.

        :param table_name: name of the table
        :type table_name: str
        :return: datetime that the table holds data for
        :rtype: datetime.datetime
        """
        m = self._table_re.match(table_name)
        dt = datetime.strptime(m.group(1), '%Y%m%d')
        return dt

    def _table_name_for_datetime(self, dt):
        """
        Return the table name for a given datetime.

        :param dt: datetime to get table name for
        :type dt: datetime.datetime
        :return: table name
        :rtype: str
        """
        return 'downloads%s' % dt.strftime('%Y%m%d')

    def _run_query(self, query):
        """
        Run one query against BigQuery and return the result.

        :param query: the query to run
        :type query: str
        :return: list of per-row response dicts (key => value)
        :rtype: list
        """
        query_request = self.service.jobs()
        logger.debug('Running query: %s', query)
        start = datetime.now()
        resp = query_request.query(
            projectId=self.project_id, body={'query': query}
        ).execute()
        duration = datetime.now() - start
        logger.debug('Query response (in %s): %s', duration, resp)
        if not resp['jobComplete']:
            logger.error('Error: query reported job not complete!')
        if int(resp['totalRows']) == 0:
            return []
        if int(resp['totalRows']) != len(resp['rows']):
            logger.error('Error: query reported %s total rows, but only '
                         'returned %d', resp['totalRows'], len(resp['rows']))
        data = []
        fields = [f['name'] for f in resp['schema']['fields']]
        for row in resp['rows']:
            d = {}
            for idx, val in enumerate(row['f']):
                d[fields[idx]] = val['v']
            data.append(d)
        return data

    def _from_for_table(self, table_name):
        """
        Construct a FROM clause for the specified table name.

        :param table_name: name of the table to select data FROM
        :type table_name: str
        :return: BigQuery FROM clause
        :rtype: str
        """
        return 'FROM [%s:%s.%s]' % (
            self._PROJECT_ID, self._DATASET_ID, table_name
        )

    @property
    def _where_for_projects(self):
        """
        Construct a WHERE clause for the project names we're querying for.

        :return: BigQuery WHERE clause for specified project names
        :rtype: str
        """
        stmts = ["file.project = '%s'" % p for p in self.projects]
        return "WHERE (%s)" % ' OR '.join(stmts)

    def _get_newest_ts_in_table(self, table_name):
        """
        Return the timestamp for the newest record in the given table.

        :param table_name: name of the table to query
        :type table_name: str
        :return: timestamp of newest row in table
        :rtype: int
        """
        logger.debug('Querying for newest timestamp in table %s',
                    table_name)
        q = "SELECT TIMESTAMP_TO_SEC(MAX(timestamp)) AS max_ts %s;" % (
            self._from_for_table(table_name))
        res = self._run_query(q)
        ts = int(res[0]['max_ts'])
        logger.debug('Newest timestamp in table %s: %s', table_name, ts)
        return ts

    def _query_by_version(self, table_name):
        """
        Query for download data broken down by version, for one day.

        :param table_name:
        :type table_name:
        :return: dict of download information by version; keys are project
          name, values are a dict of version to download count
        :rtype: dict
        """
        logger.info('Querying for downloads by version in table %s',
                    table_name)
        q = "SELECT file.project, file.version, COUNT(*) as dl_count " \
            "%s " \
            "%s " \
            "GROUP BY file.project, file.version;" % (
            self._from_for_table(table_name),
            self._where_for_projects
        )
        res = self._run_query(q)
        result = self._dict_for_projects()
        for row in res:
            result[row['file_project']][row['file_version']] = int(
                row['dl_count'])
        return result

    def _query_by_file_type(self, table_name):
        """
        Query for download data broken down by file type, for one day.

        :param table_name:
        :type table_name:
        :return: dict of download information by file type; keys are project
          name, values are a dict of file type to download count
        :rtype: dict
        """
        logger.info('Querying for downloads by file type in table %s',
                    table_name)
        q = "SELECT file.project, file.type, COUNT(*) as dl_count " \
            "%s " \
            "%s " \
            "GROUP BY file.project, file.type;" % (
            self._from_for_table(table_name),
            self._where_for_projects
        )
        res = self._run_query(q)
        result = self._dict_for_projects()
        for row in res:
            result[row['file_project']][row['file_type']] = int(
                row['dl_count'])
        return result

    def _query_by_installer(self, table_name):
        """
        Query for download data broken down by installer, for one day.

        :param table_name:
        :type table_name:
        :return: dict of download information by installer; keys are project
          name, values are a dict of installer names to dicts of installer
          version to download count.
        :rtype: dict
        """
        logger.info('Querying for downloads by installer in table %s',
                    table_name)
        q = "SELECT file.project, details.installer.name, " \
            "details.installer.version, COUNT(*) as dl_count " \
            "%s " \
            "%s " \
            "GROUP BY file.project, details.installer.name, " \
            "details.installer.version;" % (
            self._from_for_table(table_name),
            self._where_for_projects
        )
        res = self._run_query(q)
        result = self._dict_for_projects()
        # iterate through results
        for row in res:
            # pointer to the per-project result dict
            proj = result[row['file_project']]
            # grab the name and version; change None to 'unknown'
            iname = row['details_installer_name']
            iver = row['details_installer_version']
            if iname not in proj:
                proj[iname] = {}
            if iver not in proj[iname]:
                proj[iname][iver] = 0
            proj[iname][iver] += int(row['dl_count'])
        return result

    def _query_by_implementation(self, table_name):
        """
        Query for download data broken down by Python implementation, for one
        day.

        :param table_name:
        :type table_name:
        :return: dict of download information by implementation; keys are
          project name, values are a dict of implementation names to dicts of
          implementation version to download count.
        :rtype: dict
        """
        logger.info('Querying for downloads by Python implementation in table '
                    '%s', table_name)
        q = "SELECT file.project, details.implementation.name, " \
            "details.implementation.version, COUNT(*) as dl_count " \
            "%s " \
            "%s " \
            "GROUP BY file.project, details.implementation.name, " \
            "details.implementation.version;" % (
            self._from_for_table(table_name),
            self._where_for_projects
        )
        res = self._run_query(q)
        result = self._dict_for_projects()
        # iterate through results
        for row in res:
            # pointer to the per-project result dict
            proj = result[row['file_project']]
            # grab the name and version; change None to 'unknown'
            iname = row['details_implementation_name']
            iver = row['details_implementation_version']
            if iname not in proj:
                proj[iname] = {}
            if iver not in proj[iname]:
                proj[iname][iver] = 0
            proj[iname][iver] += int(row['dl_count'])
        return result

    def _query_by_system(self, table_name):
        """
        Query for download data broken down by system, for one day.

        :param table_name:
        :type table_name:
        :return: dict of download information by system; keys are project name,
          values are a dict of system names to download count.
        :rtype: dict
        """
        logger.info('Querying for downloads by system in table %s',
                    table_name)
        q = "SELECT file.project, details.system.name, COUNT(*) as dl_count " \
            "%s " \
            "%s " \
            "GROUP BY file.project, details.system.name;" % (
            self._from_for_table(table_name),
            self._where_for_projects
        )
        res = self._run_query(q)
        result = self._dict_for_projects()
        for row in res:
            system = row['details_system_name']
            result[row['file_project']][system] = int(
                row['dl_count'])
        return result

    def _query_by_distro(self, table_name):
        """
        Query for download data broken down by OS distribution, for one day.

        :param table_name:
        :type table_name:
        :return: dict of download information by distro; keys are project name,
          values are a dict of distro names to dicts of distro version to
          download count.
        :rtype: dict
        """
        logger.info('Querying for downloads by distro in table %s', table_name)
        q = "SELECT file.project, details.distro.name, " \
            "details.distro.version, COUNT(*) as dl_count " \
            "%s " \
            "%s " \
            "GROUP BY file.project, details.distro.name, " \
            "details.distro.version;" % (
            self._from_for_table(table_name),
            self._where_for_projects
        )
        res = self._run_query(q)
        result = self._dict_for_projects()
        # iterate through results
        for row in res:
            # pointer to the per-project result dict
            proj = result[row['file_project']]
            # grab the name and version; change None to 'unknown'
            dname = row['details_distro_name']
            dver = row['details_distro_version']
            if dname not in proj:
                proj[dname] = {}
            if dver not in proj[dname]:
                proj[dname][dver] = 0
            proj[dname][dver] += int(row['dl_count'])
        return result

    def _query_by_country_code(self, table_name):
        """
        Query for download data broken down by country code, for one day.

        :param table_name:
        :type table_name:
        :return: dict of download information by country code; keys are project
          name, values are a dict of country code to download count.
        :rtype: dict
        """
        logger.info('Querying for downloads by country code in table %s',
                    table_name)
        q = "SELECT file.project, country_code, COUNT(*) as dl_count " \
            "%s " \
            "%s " \
            "GROUP BY file.project, country_code;" % (
            self._from_for_table(table_name),
            self._where_for_projects
        )
        res = self._run_query(q)
        result = self._dict_for_projects()
        for row in res:
            result[row['file_project']][row['country_code']] = int(
                row['dl_count'])
        return result

    def query_one_table(self, table_name):
        """
        Run all queries for the given table name (date) and update the cache.

        :param table_name: table name to query against
        :type table_name: str
        """
        table_date = self._datetime_for_table_name(table_name)
        logger.info('Running all queries for date table: %s (%s)', table_name,
                    table_date.strftime('%Y-%m-%d'))
        final = self._dict_for_projects()
        try:
            data_timestamp = self._get_newest_ts_in_table(table_name)
        except HttpError as exc:
            try:
                content = json.loads(exc.content.decode('utf-8'))
                if content['error']['message'].startswith('Not found: Table'):
                    logger.error("Table %s not found; no data for that day",
                                 table_name)
                    return
            except:
                pass
            raise exc
        # data queries
        # note - ProjectStats._is_empty_cache_record() needs to know keys
        for name, func in {
            'by_version': self._query_by_version,
            'by_file_type': self._query_by_file_type,
            'by_installer': self._query_by_installer,
            'by_implementation': self._query_by_implementation,
            'by_system': self._query_by_system,
            'by_distro': self._query_by_distro,
            'by_country': self._query_by_country_code
        }.items():
            tmp = func(table_name)
            for proj_name in tmp:
                final[proj_name][name] = tmp[proj_name]
        # add to cache
        for proj_name in final:
            self.cache.set(proj_name, table_date, final[proj_name],
                           data_timestamp)

    def _have_cache_for_date(self, dt):
        """
        Return True if we have cached data for all projects for the specified
        datetime. Return False otherwise.

        :param dt: datetime to find cache for
        :type dt: datetime.datetime
        :return: True if we have cache for all projects for this date, False
          otherwise
        :rtype: bool
        """
        for p in self.projects:
            if self.cache.get(p, dt) is None:
                return False
        return True

    def backfill_history(self, num_days, available_table_names):
        """
        Backfill historical data for days that are missing.

        :param num_days: number of days of historical data to backfill,
          if missing
        :type num_days: int
        :param available_table_names: names of available per-date tables
        :type available_table_names: list
        """
        if num_days == -1:
            # skip the first date, under the assumption that data may be incomplete
            logger.info('Backfilling all available history')
            start_table = available_table_names[1]
        else:
            logger.info('Backfilling %d days of history', num_days)
            start_table = available_table_names[-1 * num_days]
        start_date = self._datetime_for_table_name(start_table)
        end_table = available_table_names[-3]
        end_date = self._datetime_for_table_name(end_table)
        logger.debug('Backfilling history from %s (%s) to %s (%s)', start_table,
                     start_date.strftime('%Y-%m-%d'), end_table,
                     end_date.strftime('%Y-%m-%d'))
        for days in range( (end_date - start_date).days + 1):
            backfill_dt = start_date + timedelta(days=days)
            if self._have_cache_for_date(backfill_dt):
                logger.info('Cache present for all projects for %s; skipping',
                            backfill_dt.strftime('%Y-%m-%d'))
                continue
            backfill_table = self._table_name_for_datetime(backfill_dt)
            logger.info('Backfilling %s (%s)', backfill_table,
                        backfill_dt.strftime('%Y-%m-%d'))
            self.query_one_table(backfill_table)

    def run_queries(self, backfill_num_days=7):
        """
        Run the data queries for the specified projects.

        :param backfill_num_days: number of days of historical data to backfill,
          if missing
        :type backfill_num_days: int
        """
        available_tables = self._get_download_table_ids()
        logger.debug('Found %d available download tables: %s',
                     len(available_tables), available_tables)
        today_table = available_tables[-1]
        yesterday_table = available_tables[-2]
        self.query_one_table(today_table)
        self.query_one_table(yesterday_table)
        self.backfill_history(backfill_num_days, available_tables)
