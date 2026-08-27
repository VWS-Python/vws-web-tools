Changelog
=========

.. towncrier release notes start

2026.08.27
----------

- Support database, license and target names which contain apostrophes.
  Such names previously produced invalid XPath expressions, so looking them
  up in the target manager failed.

- Support database, license and target names which contain both an
  apostrophe and a quotation mark, by building a ``concat()`` XPath
  expression for them.

- Raise a descriptive error, rather than an ``IndexError``, when
  ``get_vumark_target_id`` is asked for a target which the target manager
  has not yet rendered as a link.

- Make ``get_vumark_target_id`` wait for the target manager to render a
  target's name as a link, rather than failing as soon as the name appears
  as plain text while the target is still processing.

- Make ``delete_license`` wait for the licenses page to load, rather than
  acting on whichever page a stale session redirects to.

- Make ``navigate_to_license`` wait for the licenses page to load, rather
  than acting on whichever page a stale session redirects to.

- Make ``navigate_to_database`` wait for the target manager to load, rather
  than acting on whichever page a stale session redirects to.

- Add a ``model_target_web_api_details`` context manager, which yields the
  same details as ``get_model_target_web_api_details`` and deletes the
  OAuth2 client credential it creates when the ``with`` block is left.

- Add a ``show-model-target-web-api-details`` command, which creates and
  shows Model Target Web API credentials, in YAML or in
  ``--env-var-format``.

- Add a ``delete-model-target-web-api-credentials`` command, which deletes
  one Model Target Web API OAuth2 client credential by its client ID.

- Shell-quote the values which ``--env-var-format`` prints, so that output
  for a name containing a space or another character which is special to
  the shell can be used with ``eval`` or ``source``.

- Make ``upload_vumark_template`` return the ID of the target it uploaded.
  It now waits for VWS to finish processing the target, which takes longer
  than waiting for the target to appear in the targets table.

- Raise an error, rather than searching nested objects, when a Vuforia
  credentials API response has the wanted key at the top level but with
  an empty value.

- Chain the underlying ``requests`` exception onto the ``RuntimeError``
  raised when a call to the Vuforia credentials API fails, so that a
  traceback shows what went wrong at the network level.

- Stop swallowing every ``WebDriverException`` raised by the second,
  retried click on the add-database button, so that a real browser
  failure there is reported rather than turning into a later timeout.

- Raise an error from ``create_cloud_database``, rather than silently using
  the first match, when more than one license in the drop-down has the
  requested name.

- Make ``navigate_to_database`` wait for the target manager's search
  filter to have been applied before clicking a row, rather than
  clicking a row from the unfiltered table which is about to be
  replaced.

- Make ``delete_license`` wait for the licenses table's search filter to
  have been applied before clicking a row, rather than clicking a row
  from the unfiltered table which is about to be replaced.

- Raise an error from ``get_vumark_target_id`` when the last path
  segment of a target's link is not a target ID, rather than returning
  whatever the segment was.

- Add a ``cad_data_url`` argument to
  ``get_model_target_web_api_details``, and make the URL it defaults to
  public as ``MODEL_TARGET_WEB_API_CAD_DATA_URL``, so that callers can
  use a different model without waiting for a release of this package.

- Set Chrome's page load strategy to ``eager``, so that navigation does not
  wait for images and third-party scripts which no operation in this
  package needs.

- Send cookies which the browser holds for the Vuforia developer portal
  itself, and so have no domain attribute of their own, with requests to
  the Vuforia credentials API.

- Say what was received, rather than "unexpected shape", when the Vuforia
  credentials API returns something which is not JSON.

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
