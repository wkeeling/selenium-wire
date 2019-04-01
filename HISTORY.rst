History
~~~~~~~

1.0.3 (2019-04-01)
------------------

* Responses are no longer sent chunk by chunk where they are missing a Content-Type header.
* Ensure delayed responses don't cause errors when server is not explicitly shutdown.

1.0.2 (2019-03-10)
------------------

* Support for authentication when using http based proxies.
* Fix bug where JSON response bodies were being decoded rather than being sent through as bytes.

1.0.1 (2019-02-07)
------------------

* Support PATCH requests

1.0.0 (2018-12-31)
------------------

* Ensure stored response body is always retrieved as bytes when asked for by the test.
* Updates to README.
* Use reverse chronological ordering of HISTORY.

0.10.0 (2018-10-30)
-------------------

* Fix issue where ignoring OPTIONS requests would trigger AttributeError.
* Allow proxy settings to be explicitly set to None.

0.9.0 (2018-10-28)
------------------

* Ignore OPTIONS requests by default, and allow list of methods to be configurable via the ignore_http_methods option.
* Move default Selenium Wire request storage from system temp to user home to prevent permission collisions.

0.8.0 (2018-09-20)
------------------

* Fix issue where new headers were not being added to the request when using driver.header_overrides.

0.7.0 (2018-08-29)
------------------

* README and doc updates.

0.6.0 (2018-08-21)
------------------

* Bundle openssl.cnf for Windows.

0.5.0 (2018-08-19)
------------------

* Clearer README instructions.

0.4.0 (2018-08-19)
------------------

* OpenSSL for Windows now bundled.
* Setup instructions for Edge.

0.3.0 (2018-08-07)
------------------

* Fix remote proxy basic authentication.
* Updates to README.

0.2.0 (2018-08-04)
------------------

* Load proxy settings from env variables.
* Support disabling of content encoding.
* Updates to README.

0.1.0 (2018-06-19)
------------------

* First release on PyPI.
