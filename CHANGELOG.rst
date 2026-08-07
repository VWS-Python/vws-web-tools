Changelog
=========

.. towncrier release notes start

2026.08.07
----------

- Add a ``scopes`` argument to ``get_model_target_web_api_details`` so callers
  on Vuforia Enterprise accounts can request the advanced Model Target Web API
  scope alongside the standard scope, via the new
  ``MODEL_TARGET_WEB_API_ADVANCED_SCOPES`` constant.

- Add ``database_id`` to the dictionary returned by ``get_database_details``,
  and a ``VUFORIA_DATABASE_ID`` line to the ``--env-var-format`` output of
  ``show-database-details``.
  This is the ID which Cloud Targets Web API endpoints such as
  ``POST /imagetargets/databases/{database_id}/reports/recoCounts`` name in
  the request path.

2026.05.21
----------

- Add ``get_model_target_web_api_details`` to generate OAuth2 credentials
  for Model Target Web API tests.

2026.02.22.1
------------


2026.02.22
----------


2026.02.20
----------


2026.02.17.1
------------


2026.02.17
----------


2026.02.16.1
------------


2026.02.16
----------


- Renamed the ``create-vws-database`` CLI command to ``create-vws-cloud-database``.
