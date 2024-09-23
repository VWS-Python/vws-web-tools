|Build Status| |codecov| |PyPI| |Documentation Status|

VWS-Web-Tools
=============

Tools for interacting with the VWS (Vuforia Web Services) website.

Installation
------------

.. code-block:: shell

   pip install vws-web-tools

This is tested on Python 3.12+.

Usage
-----

.. code-block:: console

   export VWS_EMAIL_ADDRESS="[YOUR-EMAIL]"
   export VWS_PASSWORD="[YOUR-PASSWORD]"
   TIME=$(date +%s%N | cut -b1-13)

   $ vws-web-tools create-vws-license --license-name "my-licence-$TIME"
   $ vws-web-tools create-vws-database --license-name "my-licence-$TIME" --database-name "my-database-$TIME"
   $ vws-web-tools show-database-details --database-name "my-database-$TIME"

.. |Build Status| image:: https://github.com/VWS-Python/vws-web-tools/actions/workflows/ci.yml/badge.svg?branch=main
   :target: https://github.com/VWS-Python/vws-web-tools/actions
.. |codecov| image:: https://codecov.io/gh/VWS-Python/vws-web-tools/branch/main/graph/badge.svg
   :target: https://codecov.io/gh/VWS-Python/vws-web-tools
.. |Documentation Status| image:: https://readthedocs.org/projects/vws-web-tools/badge/?version=latest
   :target: https://vws-web-tools.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status
.. |PyPI| image:: https://badge.fury.io/py/VWS-Web-Tools.svg
   :target: https://badge.fury.io/py/VWS-Web-Tools
