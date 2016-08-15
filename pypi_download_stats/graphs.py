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
from datetime import datetime
from copy import deepcopy

from bokeh.charts import Area, TimeSeries, output_file, defaults, save
from bokeh.models import (PanTool, BoxZoomTool, WheelZoomTool, SaveTool,
                          ResetTool, ResizeTool, HoverTool, GlyphRenderer)
from bokeh.models.annotations import Legend
from bokeh.plotting import ColumnDataSource
from bokeh.models.glyphs import Line, Patches
from bokeh.embed import components

logger = logging.getLogger(__name__)


class FancyAreaGraph(object):
    """
    Wrapper around bokeh.charts.Area to make it look and work nicer.
    """

    def __init__(self, identifier, title, data, labels):
        """
        Initialize a wrapper around :py:class:`bokeh.charts.Area` that handles
        our data format, makes it look nice, and makes
        :py:class:`bokeh.models.HoverTool` work right with a stacked Area chart.

        :param identifier: URL-safe graph identifier
        :type identifier: str
        :param title: Human-readable graph title
        :type title: str
        :param data: dictionary of data; keys are series names, values are lists
          of download counts
        :type data: dict
        :param labels: X-axis labels (dates), :py:class:`datetime.datetime`
        :type labels: list
        """
        logger.debug('Initializing graph for %s ("%s")', identifier, title)
        self._graph_id = identifier
        self._title = title
        self._data = data
        self._labels = labels
        self._y_series_names = [k for k in data.keys()]
        # set our Date and FmtDate elements - x axis keys, and HoverTool text
        data['Date'] = labels
        data['FmtDate'] = [x.strftime('%Y-%m-%d') for x in labels]

    def generate_graph(self):
        """
        Generate the graph; return a 2-tuple of strings, script to place in the
        head of the HTML document and div content for the graph itself.

        :return: 2-tuple (script, div)
        :rtype: tuple
        """
        logger.debug('Generating graph for %s', self._graph_id)
        defaults.width = 1000
        defaults.height = 800
        # tools to use
        tools = [
            PanTool(),
            BoxZoomTool(),
            WheelZoomTool(),
            SaveTool(),
            ResetTool(),
            ResizeTool()
        ]

        print(self._data)
        print(self._y_series_names)
        # generate the stacked area graph
        g = Area(self._data, x='Date', y=self._y_series_names,
                 title="Downloads by Version", legend="top_left",
                 stack=True, xlabel='Date', ylabel='Downloads', tools=tools)

        lines = []
        # add a line at the top of each Patch (stacked area) for hovertool
        for renderer in g.select(GlyphRenderer):
            if not isinstance(renderer.glyph, Patches):
                continue
            series_name = renderer.data_source.data['series'][0]
            logger.debug('Adding line for Patches %s (series: %s)', renderer,
                         series_name)
            line = self._line_for_patches(self._data, g, renderer, series_name)
            if line is not None:
                lines.append(line)
        logger.debug("Lines for patches: %s", lines)

        # add the Hovertool, specifying only our line glyphs
        g.add_tools(
            HoverTool(
                tooltips=[
                    ('Version', '@SeriesName'),
                    ('Date', '@FmtDate'),
                    ('Downloads', '@Downloads'),
                ],
                renderers=lines,
                line_policy='nearest'
            )
        )
        return components(g)

    def _line_for_patches(self, data, chart, renderer, series_name):
        """
        Add a line along the top edge of a Patch in a stacked Area Chart; return
        the new Glyph for addition to HoverTool.

        :param data: original data for the graph
        :type data: dict
        :param chart: Chart to add the line to
        :type chart: bokeh.charts.chart.Chart
        :param renderer: GlyphRenderer containing one Patches glyph, to draw
          the line for
        :type renderer: bokeh.models.renderers.GlyphRenderer
        :param series_name: the data series name this Patches represents
        :type series_name: str
        :return:
        :rtype:
        """
        # get the original x and y values, and color
        xvals = deepcopy(renderer.data_source.data['x_values'][0])
        yvals = deepcopy(renderer.data_source.data['y_values'][0])
        line_color = renderer.glyph.fill_color

        # save original values for logging if needed
        orig_xvals = [x for x in xvals]
        orig_yvals = [y for y in yvals]

        # get a list of the values
        new_xvals = [x for x in xvals]
        new_yvals = [y for y in yvals]

        # so when a Patch is made, the first point is (0,0); trash it
        xvals = new_xvals[1:]
        yvals = new_yvals[1:]

        # then, we can tell the last point in the "top" line because it will be
        # followed by a point with the same x value and a y value of 0.
        last_idx = None
        for idx, val in enumerate(xvals):
            if yvals[idx+1] == 0 and xvals[idx+1] == xvals[idx]:
                last_idx = idx
                break

        if last_idx is None:
            logger.error('Unable to find top line of patch (x_values=%s '
                         'y_values=%s', orig_xvals, orig_yvals)
            return None

        # truncate our values to just what makes up the top line
        xvals = xvals[:last_idx+1]
        yvals = yvals[:last_idx+1]

        # Currently (bokeh 0.12.1) HoverTool won't show the tooltip for the last
        # point in our line. As a hack for this, add a point with the same Y value
        # and an X slightly before it.
        lastx = xvals[-1]
        xvals[-1] = lastx - 1000  # 1000 nanoseconds
        xvals.append(lastx)
        yvals.append(yvals[-1])
        # get the actual download counts from the original data
        download_counts = [data[series_name][y] for y in range(0, len(yvals) - 1)]
        download_counts.append(download_counts[-1])

        # create a ColumnDataSource for the new overlay line
        data2 = {
            'x': xvals,  # Date/x values are numpy.datetime64
            'y': yvals,
            # the following are hacks for data that we want in the HoverTool tooltip
            'SeriesName': [series_name for _ in yvals],
            # formatted date
            'FmtDate': [
                datetime.utcfromtimestamp(x.astype(int) * 1e-9).strftime('%Y-%m-%d') for x in xvals
            ],
            # to show the exact value, not where the pointer is
            'Downloads': download_counts
        }
        # set the formatted date for our hacked second-to-last point to the
        # same value as the last point
        data2['FmtDate'][-2] = data2['FmtDate'][-1]

        # create the CloumnDataSource, then the line for it, then the Glyph
        line_ds = ColumnDataSource(data2)
        line = Line(x='x', y='y', line_color=line_color)
        lineglyph = chart.add_glyph(line_ds, line)
        print(type(lineglyph))
        return lineglyph
