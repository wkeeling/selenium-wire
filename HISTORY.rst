History
~~~~~~~

1.1.1 (2020-05-25)
------------------

* Handle errors occuring on websocket connections.

1.1.0 (2020-05-23)
------------------

* Allow the request storage base directory to be configurable.
* Support proxying websocket connections.
* Fix bug where attempting to filter out non-existent headers would raise an error.
* Handle possibility of zero byte captured request/response files.

1.0.12 (2020-05-16)
-------------------

* Support for SOCKS proxies.

1.0.11 (2019-12-31)
-------------------

* Fix duplication of content-length header when altering body content.

1.0.10 (2019-09-22)
-------------------

* Scope request capture.
* Apply header filtering on a per-URL basis.

1.0.9 (2019-08-25)
------------------

* Add ability to provide a custom response handler method.

1.0.8 (2019-08-01)
------------------

* Remove signal handler from AdminClient to allow running in multi-threaded environment.
* Make connection timeout configurable.

1.0.7 (2019-07-30)
------------------

* Fix bug where temporary storage cleanup would sometimes fail when running in a multi-threaded environment.
* Don't rely on signal handlers for temporary storage cleanup. Signal handlers are not compatible with multiple threads. Use driver.quit() for explicit cleanup.

1.0.6 (2019-07-14)
------------------

* Support for disabling SSL verification when using self-signed certificates.

1.0.5 (2019-06-15)
------------------

* Improve performance on Windows by explicitly closing the response output stream.
* Capture stderr leaking from openssl to the console.
* Ensure subjectAltName is added to self signed certificates.
* Refactor certificate generation code.
* More robust handling of socket errors.
* Decode response bodies at the point a client asks for them, not at the point a response is captured.

1.0.4 (2019-04-04)
------------------

* Clean up cached request directory tree on driver.quit().
* Suppress connection related errors by default.

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
