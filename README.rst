|Build Status| |codecov| |PyPI| |Documentation Status|

VWS-Web-Tools
=============

Tools for interacting with the VWS (Vuforia Web Services) website.

Installation
------------

.. code:: sh

   pip install vws-web-tools

This is tested on Python 3.10+.

Usage
-----

.. code:: sh

   export VWS_EMAIL_ADDRESS=[YOUR-EMAIL]
   export VWS_PASSWORD=[YOUR-PASSWORD]

   vws-web-tools \
       create-vws-license \
       --license-name my-licence-0001

   vws-web-tools \
       create-vws-database \
       --license-name my-licence-0001  \
       --database-name my-database-0001

   vws-web-tools show-database-details \
       --database-name my-database-0001

.. |Build Status| image:: https://github.com/VWS-Python/vws-web-tools/workflows/CI/badge.svg
   :target: https://github.com/VWS-Python/vws-web-tools/actions
.. |codecov| image:: https://codecov.io/gh/VWS-Python/vws-web-tools/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/VWS-Python/vws-web-tools
.. |Documentation Status| image:: https://readthedocs.org/projects/vws-web-tools/badge/?version=latest
   :target: https://vws-web-tools.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status
.. |PyPI| image:: https://badge.fury.io/py/VWS-Web-Tools.svg
   :target: https://badge.fury.io/py/VWS-Web-Tools
