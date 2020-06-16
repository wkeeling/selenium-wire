Selenium Wire
=============

Selenium Wire extends Selenium's Python bindings to give your tests access to the underlying requests made by the browser. It is a lightweight library designed for ease of use with minimal external dependencies.

With Selenium Wire, you author your tests in just the same way as you do with Selenium, but you get an additional user-friendly API for accessing things such as the request/response headers, status code and body content.

.. image:: https://travis-ci.org/wkeeling/selenium-wire.svg?branch=master
        :target: https://travis-ci.org/wkeeling/selenium-wire

.. image:: https://codecov.io/gh/wkeeling/selenium-wire/branch/master/graph/badge.svg
        :target: https://codecov.io/gh/wkeeling/selenium-wire

.. image:: https://img.shields.io/badge/python-3.4%2C%203.5%2C%203.6%2C%203.7%2C%203.8-blue.svg
        :target: https://pypi.python.org/pypi/selenium-wire

.. image:: https://img.shields.io/pypi/v/selenium-wire.svg
        :target: https://pypi.python.org/pypi/selenium-wire

.. image:: https://img.shields.io/pypi/l/selenium-wire.svg
        :target: https://pypi.python.org/pypi/selenium-wire

Simple Example
~~~~~~~~~~~~~~

.. code:: python

    from seleniumwire import webdriver  # Import from seleniumwire

    # Create a new instance of the Firefox driver
    driver = webdriver.Firefox()

    # Go to the Google home page
    driver.get('https://www.google.com')

    # Access requests via the `requests` attribute
    for request in driver.requests:
        if request.response:
            print(
                request.path,
                request.response.status_code,
                request.response.headers['Content-Type']
            )

Prints:

.. code:: bash

    https://www.google.com/ 200 text/html; charset=UTF-8
    https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_120x44dp.png 200 image/png
    https://consent.google.com/status?continue=https://www.google.com&pc=s&timestamp=1531511954&gl=GB 204 text/html; charset=utf-8
    https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png 200 image/png
    https://ssl.gstatic.com/gb/images/i2_2ec824b0.png 200 image/png
    https://www.google.com/gen_204?s=webaft&t=aft&atyp=csi&ei=kgRJW7DBONKTlwTK77wQ&rt=wsrt.366,aft.58,prt.58 204 text/html; charset=UTF-8
    ...

Features
~~~~~~~~

* Pure Python with user-friendly API
* All HTTP/HTTPS requests captured
* Access to request/response bodies
* Modify responses
* Header injection/filtering
* URL rewriting
* Proxy server support


Compatibilty
~~~~~~~~~~~~

* Python 3.4+
* Selenium 3.4.0+
* Firefox, Chrome, Safari and Edge are supported

Table of Contents
~~~~~~~~~~~~~~~~~

- `Installation`_

  * `OpenSSL`_
  * `Browser Setup`_

- `Usage`_

  * `Creating the Webdriver`_
  * `Accessing Requests`_
  * `Waiting for a Request`_
  * `Clearing Requests`_
  * `Scoping Request Capture`_

- `Request Attributes`_

- `Response Attributes`_

- `Modifying Requests`_

  * `Modifying Headers`_
  * `Rewriting URLs`_

- `Proxies`_

  * `SOCKS`_

- `Other Options`_

- `Limitations`_

- `License`_

Installation
~~~~~~~~~~~~

Install using pip:

.. code:: bash

    pip install selenium-wire

OpenSSL
-------

Selenium Wire requires OpenSSL for capturing HTTPS requests.

**Linux**

.. code:: bash

    # For apt based Linux systems
    sudo apt install openssl

    # For RPM based Linux systems
    sudo yum install openssl

**MacOS**

.. code:: bash

    brew install openssl

**Windows**

No installation is required. OpenSSL for Windows is bundled with Selenium Wire.


Browser Setup
-------------

**Firefox and Chrome**

No specific configuration should be necessary - everything should just work.

You will however need to ensure that you have downloaded the `Gecko driver`_ and `Chrome driver`_ for Firefox and Chrome to be remotely controlled - the same as if you were using Selenium directly. Once downloaded, these executables should be placed somewhere on your PATH.

.. _`Gecko driver`: https://github.com/mozilla/geckodriver/

.. _`Chrome driver`: https://sites.google.com/a/chromium.org/chromedriver/

**Safari**

There are a few `manual steps`_ that have to be carried out before you can use Safari with Selenium Wire.

.. _`manual steps`: ./safari_setup.rst

**Edge**

Like Safari, Microsoft Edge requires some `manual configuration`_ before it can be used with Selenium Wire.

.. _`manual configuration`: ./edge_setup.rst

Usage
~~~~~

Ensure that you import ``webdriver`` from the ``seleniumwire`` package:

.. code:: python

    from seleniumwire import webdriver

* For sub-packages of ``webdriver``, you should continue to import these directly from ``selenium``. For example, to import ``WebDriverWait``:

.. code:: python

    # Sub-packages of webdriver must still be imported from `selenium` itself
    from selenium.webdriver.support.ui import WebDriverWait

Creating the Webdriver
----------------------

For Firefox and Chrome, you don't need to do anything special. Just instantiate the webdriver as you would normally, passing in Selenium specific options if you have any. Selenium Wire also has it's `own options`_ that can be passed in the ``seleniumwire_options`` attribute.

.. _`own options`: #other-options

**Firefox**

.. code:: python

    driver = webdriver.Firefox()

**Chrome**

.. code:: python

    driver = webdriver.Chrome()

**Safari**

For Safari, you need to tell Selenium Wire the port number you selected when you configured the browser in `Browser Setup`_.
For example, if you chose port 12345, then you would pass it in the ``seleniumwire_options`` like this:

.. code:: python

    driver = webdriver.Safari(seleniumwire_options={'port': 12345})

**Edge**

For Edge, you need to tell Selenium Wire the port number you selected when you configured the browser in `Browser Setup`_.
For example, if you chose port 12345, then you would pass it in the ``seleniumwire_options`` like this:

.. code:: python

    driver = webdriver.Edge(seleniumwire_options={'port': 12345})

Accessing Requests
------------------

Selenium Wire captures all HTTP/HTTPS traffic made by the browser during a test.

**driver.requests**

You can retrieve all requests with the ``driver.requests`` attribute. The requests are just a list and can be iterated (like in the opening example) and indexed:

.. code:: python

    first_request = driver.requests[0]

**driver.last_request**

The list of requests held by ``driver.requests`` is in chronological order. If you want to access the most recent request, use the dedicated ``driver.last_request`` attribute:

.. code:: python

    last_request = driver.last_request

This is more efficient than using ``driver.requests[-1]``.

Waiting for a Request
---------------------

When you ask for captured requests using ``driver.requests`` or ``driver.last_request`` you have to be sure that the requests you're interested in have actually been captured. If you ask too soon, then you may find that a request is not yet present, or is present but has no associated response.

**driver.wait_for_request()**

This method will wait for a previous request with a specific path to complete before allowing the test to continue. The path can be a unique part of the URL or the full URL itself.

For example, to wait for an AJAX request to return after a button is clicked:

.. code:: python

    # Click a button that triggers a background request to https://server/api/products/12345/
    button_element.click()

    # Wait for the request/response to complete
    request = driver.wait_for_request('/api/products/12345/')

* Note that ``driver.wait_for_request()`` doesn't *make* a request, it just *waits* for a previous request made by some other action.

The ``wait_for_request()`` method will return the first *fully completed* request it finds that matches the supplied path. Fully completed meaning that the response must have returned. The method will wait up to 10 seconds by default but you can vary that with the ``timeout`` argument:

.. code:: python

    # Wait up to 30 seconds for a request/response
    request = driver.wait_for_request('/api/products/12345/', timeout=30)

If a fully completed request is not seen within the timeout period a ``TimeoutException`` is raised.

Clearing Requests
-----------------

To clear previously captured requests, use ``del``:

.. code:: python

    del driver.requests

Scoping Request Capture
-----------------------

By default, Selenium Wire will capture all requests the browser makes during a test. You may want to restrict this to particular URLs - e.g. for performance reasons.

To restrict request capture use the ``scopes`` attribute. This accepts a list of regular expressions that will match URLs to be captured.

.. code:: python

    driver.scopes = [
        '.*stackoverflow.*',
        '.*github.*'
    ]

    # Only request URLs containing "stackoverflow" or "github" will now be captured...

Request Attributes
~~~~~~~~~~~~~~~~~~

Requests have the following attributes.

``method``
    The HTTP method type such as ``GET`` or ``POST``.

``path``
    The request path.

``querystring``
    The query string.

``params``
    A dictionary of request parameters. If a parameter with the same name appears more than once in the request, it's value in the dictionary will be a list.

``headers``
    A case-insensitive dictionary of request headers. Asking for ``request.headers['user-agent']`` will return the value of the ``User-Agent`` header.

``body``
    The request body as ``bytes``. If the request has no body the value of ``body`` will be ``None``.

``response``
   The response associated with the request. This will be ``None`` if the request has no response.

Response Attributes
~~~~~~~~~~~~~~~~~~~

The response can be retrieved from a request via the ``response`` attribute. A response may be ``None`` if it was never captured, which may happen if you asked for it before it returned or if the server timed out etc. A response has the following attributes.

``status_code``
    The status code of the response such as ``200`` or ``404``.

``reason``
    The reason phrase such as ``OK`` or ``Not Found``.

``headers``
     A case-insensitive dictionary of response headers. Asking for ``response.headers['content-length']`` will return the value of the ``Content-Length`` header.

``body``
    The response body as ``bytes``. If the response has no body the value of ``body`` will be ``None``.


Modifying Requests
~~~~~~~~~~~~~~~~~~

Selenium Wire allows you to modify the request headers the browser sends as well as rewrite any part of the request URL.

Modifying Headers
-----------------

The ``driver.header_overrides`` attribute is used for modifying headers.

To add one or more new headers to a request, create a dictionary containing those headers and set it as the value of ``header_overrides``.

.. code:: python

    driver.header_overrides = {
        'New-Header1': 'Some Value',
        'New-Header2': 'Some Value'
    }

    # All subsequent requests will now contain New-Header1 and New-Header2

If a header already exists in a request it will be overwritten by the one in the dictionary. Header names are case-insensitive.

To filter out one or more headers from a request, set the value of those headers to ``None``.

.. code:: python

    driver.header_overrides = {
        'Existing-Header1': None,
        'Existing-Header2': None
    }

    # All subsequent requests will now *not* contain Existing-Header1 or Existing-Header2

To clear the header overrides that you have set, use ``del``:

.. code:: python

    del driver.header_overrides

Header overrides can also be applied on a per-URL basis, in the following format:

.. code:: python

    driver.header_overrides = [
        ('.*prod1.server.com.*', {'User-Agent': 'Test_User_Agent_String',
                                  'New-Header': 'HeaderValue'}),
        ('.*prod2.server.com.*', {'User-Agent2': 'Test_User_Agent_String2',
                                  'New-Header2': 'HeaderValue'})
    ]

    # Only requests to prod1.server.com or prod2.server.com will have their headers modified


Rewriting URLs
--------------

The ``driver.rewrite_rules`` attribute is used for rewriting request URLs.

Each rewrite rule should be specified as a 2-tuple or list, the first element containing the URL pattern to match and the second element the replacement. One or more rewrite rules can be supplied.

.. code:: python

    driver.rewrite_rules = [
        (r'(https?://)prod1.server.com(.*)', r'\1prod2.server.com\2'),
    ]

    # All subsequent requests that match http://prod1.server.com... or https://prod1.server.com...
    # will be rewritten to http://prod2.server.com... or https://prod2.server.com...

The match and replacement syntax is just Python's regex syntax. See `re.sub`_ for more information.

.. _`re.sub`: https://docs.python.org/3/library/re.html#re.sub

To clear the rewrite rules that you have set, use ``del``:

.. code:: python

    del driver.rewrite_rules

Proxies
~~~~~~~

If the site you are testing sits behind a proxy server you can tell Selenium Wire about that proxy server in the options you pass to the webdriver instance. The configuration takes the following format:

.. code:: python

    options = {
        'proxy': {
            'http': 'http://192.168.10.100:8888',
            'https': 'https://192.168.10.100:8889',
            'no_proxy': 'localhost,127.0.0.1'
        }
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

To use HTTP Basic Auth with your proxy, specify the username and password in the URL:

.. code:: python

    options = {
        'proxy': {
            'https': 'https://user:pass@192.168.10.100:8889',
        }
    }

For proxy authentication different to Basic, you can supply the full value for the ``Proxy-Authorization`` header using the ``custom_authorization`` option. For example, if your proxy used the Bearer scheme:

.. code:: python

    options = {
        'proxy': {
            'https': 'https://192.168.10.100:8889',  # No username or password used
            'custom_authorization': 'Bearer mytoken123'  # Custom Proxy-Authorization header value
        }
    }

The proxy configuration can also be loaded through environment variables called ``HTTP_PROXY``, ``HTTPS_PROXY`` and ``NO_PROXY``:

.. code:: bash

    $ export HTTP_PROXY="http://192.168.10.100:8888"
    $ export HTTPS_PROXY="https://192.168.10.100:8889"
    $ export NO_PROXY="localhost,127.0.0.1"

SOCKS
-----

Using a SOCKS proxy is the same as using an HTTP based one:

.. code:: python

    options = {
        'proxy': {
            'http': 'socks5://user:pass@192.168.10.100:8888',
            'https': 'socks5://user:pass@192.168.10.100:8889',
            'no_proxy': 'localhost,127.0.0.1'
        }
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

You can leave out the ``user`` and ``pass`` if your proxy doesn't require authentication.

As well as ``socks5``, the schemes ``socks4`` and ``socks5h`` are supported. Use ``socks5h`` when you want DNS resolution to happen on the proxy server rather than on the client.


Other Options
~~~~~~~~~~~~~

Other options that can be passed to Selenium Wire via the ``seleniumwire_options`` webdriver attribute:

``request_storage_base_dir``
    Captured requests and responses are stored in the current user's home folder by default. If you want to use a different folder, you can specify that here.

.. code:: python

    options = {
        'request_storage_base_dir': '/tmp'  # Use /tmp to store captured data
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

``connection_timeout``
    The number of seconds Selenium Wire should wait before timing out requests. The default is 5 seconds. Increase this value if you're working with a slow server that needs more time to respond. Set to ``None`` for no timeout.

.. code:: python

    options = {
        'connection_timeout': None  # Never timeout
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

``connection_keep_alive``
    Whether connections should be reused across requests. The default is ``True`` although this can be overridden on a per-request basis with a ``Connection: close`` header. Set to ``False`` to always close down connections after each request.

.. code:: python

    options = {
        'connection_keep_alive': False  # Always close connections after each request
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

``max_threads``
    The maximum allowed number threads that will be used to handle requests. The default is 9999.

.. code:: python

    options = {
        'max_threads': 3  # Allow a maximum of 3 threads to handle requests.
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

``verify_ssl``
    Whether SSL certificates should be verified. The default is ``False`` which prevents errors with self-signed certificates.

.. code:: python

    options = {
        'verify_ssl': True  # Verify SSL certificates but beware of errors with self-signed certificates.
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

``custom_response_handler``
    This function that should be passed in custom response handlers should maintain a signature that it compatible with ``CaptureRequestHandler.response_handler``, as all arguments passed to that function will in turn be passed to your function. In order to modify the response data, you will need to return it from your function (the response data for the request is given in the ``res_body`` argument).

.. code:: python

    def custom(req, req_body, res, res_body):
        print(f'res_body length: {len(res_body)}')

    options = {
        'custom_response_handler': custom
    }
    drv = webdriver.Firefox(seleniumwire_options=options)
    drv.get('https://example.com')

The code above will print something like this to the console (loading a page will almost always initiate more than one request):

.. code:: python

    res_body length: 471
    res_body length: 606

``ignore_http_methods``
    A list of HTTP methods (specified as uppercase strings) that should be ignored by Selenium Wire and not captured. The default is ``['OPTIONS']`` which ignores all OPTIONS requests. To capture all request methods, set ``ignore_http_methods`` to an empty list:

.. code:: python

    options = {
        'ignore_http_methods': []  # Capture all requests, including OPTIONS requests
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

``disable_encoding``
    Whether to disable content encoding. When set to ``True``, the ``Accept-Encoding`` header will be set to ``identity`` for all requests. This tells the server to not compress/modify the response. The default is ``False``.

.. code:: python

    options = {
        'disable_encoding': True  # Tell the server not to compress the response
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

``suppress_connection_errors``
    Whether to suppress connection related tracebacks. The default is ``True`` so that harmless errors that commonly occur at browser shutdown do not alarm users. When suppressed, the connection error message is logged at DEBUG level without a traceback. Set to ``False`` to allow exception propagation and see full tracebacks.

.. code:: python

    options = {
        'suppress_connection_errors': False  # Show full tracebacks for any connection errors
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

Limitations
~~~~~~~~~~~

* Selenium Wire will currently work with tests that run on the same machine as the browser. A distributed setup using Selenium Grid is not yet supported.
* Sites that use NTLM authentication (Windows authentication) cannot currently be tested with Selenium Wire. NTLM authentication is not supported.

License
~~~~~~~

MIT
