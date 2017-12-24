Changelog
=========

Unreleased Changes
------------------

* Stop testing and supporting py33; start testing py36.
* Stop testing and supporting py34, as we rely on ``pandas`` that doesn't support 3.4.
* Many fixes for pep8/flakes and docs build.

0.2.1 (2016-09-18)
------------------

* Fix example cron S3 upload script in README.

0.2.0 (2016-09-18)
------------------

* Fix packaging bug where HTML templates weren't included in package (making
  this entire tool pretty useless)
* Fix unicode output error.

0.1.0 (2016-08-28)
------------------

* Initial release
