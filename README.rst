|Build Status| |PyPI|

VWS-Web-Tools
=============

Tools for interacting with the VWS (Vuforia Web Services) website.

Installation
------------

.. code-block:: shell

   pip install vws-web-tools

This is tested on Python |minimum-python-version|\+.

Usage
-----

.. code-block:: console

   $ export VWS_EMAIL_ADDRESS="[YOUR-EMAIL]"
   $ export VWS_PASSWORD="[YOUR-PASSWORD]"
   $ TIME="$(date +%s%N | cut -b1-13)"
   $ vws-web-tools create-vws-license --license-name "my-licence-$TIME"
   $ vws-web-tools create-vws-cloud-database --license-name "my-licence-$TIME" --database-name "my-database-$TIME"
   $ vws-web-tools show-database-details --database-name "my-database-$TIME"

Python API
----------

This project also exposes a Python API.
See the `Python API reference <https://vws-python.github.io/vws-web-tools/python-api.html>`__.

Full documentation
------------------

See the `full documentation <https://vws-python.github.io/vws-web-tools/>`__ for more information including how to contribute.

.. |Build Status| image:: https://github.com/VWS-Python/vws-web-tools/actions/workflows/ci.yml/badge.svg?branch=main
   :target: https://github.com/VWS-Python/vws-web-tools/actions
.. |PyPI| image:: https://badge.fury.io/py/VWS-Web-Tools.svg
   :target: https://badge.fury.io/py/VWS-Web-Tools
.. |minimum-python-version| replace:: 3.12
