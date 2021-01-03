History
~~~~~~~

3.0.1 (2021-01-03)
------------------

* Create a new event loop if current event loop is closed.

3.0.0 (2021-01-02)
------------------

* Inroduce request and response interceptors.
* Run mitmproxy backend in a thread rather than subprocess.
* Drop internal HTTP admin API.
* Drop support for Python 3.4 and 3.5.
* Add support for remote webdriver client.
* Add support for duplicate request and response headers.
* Fixed issue where Proxy-Connection header was being propagated.
* Fixed issue where desired capabilities could not be reused outside of Selenium Wire due to addition of proxy config.
* Deprecation of header_overrides, param_overrides, querystring_overrides, rewrite_urls, custom_response_handler

2.1.2 (2020-11-14)
------------------

* Prevent Chrome from bypassing Selenium Wire for localhost addresses.

2.1.1 (2020-08-10)
------------------

* Automatic port number selection for mitmproxy backend.

2.1.0 (2020-07-21)
------------------

* Support regular expressions in driver.wait_for_request().

2.0.0 (2020-07-14)
------------------

* Introduce the mitmproxy backend
* Support for modifying response headers
* Support for modifying request parameters and the query string
* Breaking API changes:
    * the request.path attribute now returns the path rather than the full URL. To retrieve the URL, use request.url.
    * empty request and response bodies are now returned as empty bytes `b''` rather than `None`.

1.2.3 (2020-06-19)
------------------

* Disable connection persistence by default due to side effects in certain cases.

1.2.2 (2020-06-12)
------------------

* Close connection on error rather than send 502 response to permit browser retry.

1.2.1 (2020-06-09)
------------------

* Use SHA256 digest when creating site certificates to fix Chrome HSTS security errors.

1.2.0 (2020-06-07)
------------------

* Add properties to allow easy retrieval of the query string and request parameters.
* Don't verify SSL by default.
* Allow configurable number of request threads.
* Use connection persistance (keep-alive) by default. Make configurable.

1.1.2 (2020-05-27)
------------------

* Fix bug where request thread would spin after websocket closure.


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
