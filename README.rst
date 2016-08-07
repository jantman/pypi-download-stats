pypi-download-stats
========================

.. image:: https://img.shields.io/github/forks/jantman/pypi-download-stats.svg
   :alt: GitHub Forks
   :target: https://github.com/jantman/pypi-download-stats/network

.. image:: https://img.shields.io/github/issues/jantman/pypi-download-stats.svg
   :alt: GitHub Open Issues
   :target: https://github.com/jantman/pypi-download-stats/issues

.. image:: https://landscape.io/github/jantman/pypi-download-stats/master/landscape.svg
   :target: https://landscape.io/github/jantman/pypi-download-stats/master
   :alt: Code Health

.. image:: https://secure.travis-ci.org/jantman/pypi-download-stats.png?branch=master
   :target: http://travis-ci.org/jantman/pypi-download-stats
   :alt: travis-ci for master branch

.. image:: https://codecov.io/github/jantman/pypi-download-stats/coverage.svg?branch=master
   :target: https://codecov.io/github/jantman/pypi-download-stats?branch=master
   :alt: coverage report for master branch

.. image:: https://readthedocs.org/projects/pypi-download-stats/badge/?version=latest
   :target: https://readthedocs.org/projects/pypi-download-stats/?badge=latest
   :alt: sphinx documentation for latest release

.. image:: http://www.repostatus.org/badges/latest/wip.svg
   :alt: Project Status: WIP – Initial development is in progress, but there has not yet been a stable, usable release suitable for the public.
   :target: http://www.repostatus.org/#wip

Introduction
------------

This package retrieves download statistics from Google BigQuery for one or more
`PyPI <https://pypi.python.org/pypi>`_ packages, caches them locally, and then
generates some statistics (JSON and pretty HTML) as well as download count badges.
It's intended to be run on a schedule (i.e. daily) and have the results uploaded
somewhere.

It would certainly be nice to make this into a real service (and some extension
points for that have been included), but at the moment
I have neither the time to dedicate to that, the money to cover some sort
of hosting and bandwidth, nor the desire to handle how to architect this for
over 85,000 projects as opposed to my few.

**Note** this package is *very* young; I wrote it as an evening/weekend project,
hoping to only take a few days on it. Though writing this makes me want to bathe
immediately, it has no tests. If people start using it, I'll change that.

Background
----------

Sometime in February 2016, `download stats <https://bitbucket.org/pypa/pypi/issues/396/download-stats-have-stopped-working-again>`_
stopped working on pypi.python.org. As I later learned, what we currently (August 2016)
know as pypi is really the `pypi-legacy <https://github.com/pypa/pypi-legacy>`_ codebase,
and is far from a stable hands-off service. The `small team of interpid souls <https://caremad.io/2016/05/powering-pypi/>`_
who keep it running have their hands full simply keeping it online, while also working
on its replacement, `warehouse <https://github.com/pypa/warehouse>`_ (which as of August 2016 is available online
at `https://pypi.io/ <https://pypi.io/>`_). While the actual pypi.python.org web UI hasn't been
switched over to the warehouse code yet (it's still under development), the current Warehouse
service does provide full access to pypi. It's completely understandable that, given all this
and the "life support" status of the legacy pypi codebase, download stats in a legacy codebase
are their last concern.

However, current download statistics (actually the raw log information) since January 22, 2016
are `available in a Google BigQuery public dataset <https://mail.python.org/pipermail/distutils-sig/2016-May/028986.html>`_
and being updated in near-real-time. There may be download statistics functionality

Requirements
------------

* Python 2.7+ (currently tested with 2.7, 3.2, 3.3, 3.4)
* Python `VirtualEnv <http://www.virtualenv.org/>`_ and ``pip`` (recommended installation method; your OS/distribution should have packages for these)

Installation
------------

It's recommended that you install into a virtual environment (virtualenv /
venv). See the `virtualenv usage documentation <http://www.virtualenv.org/en/latest/>`_
for information on how to create a venv.

.. code-block:: bash

    pip install pypi-download-stats

Configuration
-------------

Something here.

Something about Google creds, if I can figure out how to do that again.

Usage
-----

Something else here.

Bugs and Feature Requests
-------------------------

Bug reports and feature requests are happily accepted via the `GitHub Issue Tracker <https://github.com/jantman/pypi-download-stats/issues>`_. Pull requests are
welcome. Issues that don't have an accompanying pull request will be worked on
as my time and priority allows.

Development
===========

To install for development:

1. Fork the `pypi-download-stats <https://github.com/jantman/pypi-download-stats>`_ repository on GitHub
2. Create a new branch off of master in your fork.

.. code-block:: bash

    $ virtualenv pypi-download-stats
    $ cd pypi-download-stats && source bin/activate
    $ pip install -e git+git@github.com:YOURNAME/pypi-download-stats.git@BRANCHNAME#egg=pypi-download-stats
    $ cd src/pypi-download-stats

The git clone you're now in will probably be checked out to a specific commit,
so you may want to ``git checkout BRANCHNAME``.

Guidelines
----------

* pep8 compliant with some exceptions (see pytest.ini)

Testing
-------

There isn't any right now. I'm bad. If people actually start using this, I'll
refactor and add tests, but for now this started as a one-night project.

Release Checklist
-----------------

1. Open an issue for the release; cut a branch off master for that issue.
2. Confirm that there are CHANGES.rst entries for all major changes.
3. Ensure that Travis tests passing in all environments.
4. Ensure that test coverage is no less than the last release (ideally, 100%).
5. Increment the version number in pypi-download-stats/version.py and add version and release date to CHANGES.rst, then push to GitHub.
6. Confirm that README.rst renders correctly on GitHub.
7. Upload package to testpypi:

   * Make sure your ~/.pypirc file is correct (a repo called ``test`` for https://testpypi.python.org/pypi)
   * ``rm -Rf dist``
   * ``python setup.py register -r https://testpypi.python.org/pypi``
   * ``python setup.py sdist bdist_wheel``
   * ``twine upload -r test dist/*``
   * Check that the README renders at https://testpypi.python.org/pypi/pypi-download-stats

8. Create a pull request for the release to be merged into master. Upon successful Travis build, merge it.
9. Tag the release in Git, push tag to GitHub:

   * tag the release. for now the message is quite simple: ``git tag -a X.Y.Z -m 'X.Y.Z released YYYY-MM-DD'``
   * push the tag to GitHub: ``git push origin X.Y.Z``

11. Upload package to live pypi:

    * ``twine upload dist/*``

10. make sure any GH issues fixed in the release were closed.
