Selenium Wire
=============

Selenium Wire extends Selenium's Python bindings to give you access to the underlying requests made by the browser. It allows you to capture requests and responses, as well as make changes to them on the fly.

.. image:: https://github.com/wkeeling/selenium-wire/workflows/build/badge.svg
        :target: https://github.com/wkeeling/selenium-wire/actions

.. image:: https://codecov.io/gh/wkeeling/selenium-wire/branch/master/graph/badge.svg
        :target: https://codecov.io/gh/wkeeling/selenium-wire

.. image:: https://img.shields.io/badge/python-3.6%2C%203.7%2C%203.8%2C%203.9-blue.svg
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
                request.url,
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

* Pure Python, user-friendly API
* HTTP and HTTPS requests captured
* Intercept requests and responses
* Modify requests on the fly
* Proxy server support

Compatibilty
~~~~~~~~~~~~

* Python 3.6+
* Selenium 3.4.0+
* Chrome, Firefox and Remote Webdriver supported

Table of Contents
~~~~~~~~~~~~~~~~~

- `Installation`_

  * `Browser Setup`_

  * `OpenSSL`_

- `Creating the Webdriver`_

- `Accessing Requests`_

- `Request Objects`_

- `Response Objects`_

- `Intercepting Requests and Responses`_

  * `Example: Add a request header`_
  * `Example: Replace an existing request header`_
  * `Example: Add a response header`_
  * `Example: Add a request parameter`_
  * `Example: Update JSON in a POST request body`_
  * `Example: Block a request`_
  * `Example: Mock a response`_
  * `Unset an interceptor`_

- `Limiting Request Capture`_

- `Proxies`_

  * `SOCKS`_

- `Backends`_

- `Certificates`_

- `All Options`_

- `License`_

Installation
~~~~~~~~~~~~

Install using pip:

.. code:: bash

    pip install selenium-wire

Browser Setup
-------------

No specific configuration should be necessary except to ensure that you have downloaded the `Chrome driver`_ and `Gecko driver`_ for Chrome and Firefox to be remotely controlled - the same as if you were using Selenium directly. Once downloaded, these executables should be placed somewhere on your PATH.

.. _`Chrome driver`: https://sites.google.com/a/chromium.org/chromedriver/

.. _`Gecko driver`: https://github.com/mozilla/geckodriver/

OpenSSL
-------

Selenium Wire requires OpenSSL for decrypting HTTPS requests. This is normally already installed on most systems, but if not you can install it with:

**Linux**

.. code:: bash

    # For apt based Linux systems
    sudo apt install openssl

    # For RPM based Linux systems
    sudo yum install openssl

    # For Linux alpine
    sudo apk add openssl

**MacOS**

.. code:: bash

    brew install openssl

**Windows**

No installation is required.

Creating the Webdriver
~~~~~~~~~~~~~~~~~~~~~~

Ensure that you import ``webdriver`` from the ``seleniumwire`` package:

.. code:: python

    from seleniumwire import webdriver

* For sub-packages of ``webdriver``, you should continue to import these directly from ``selenium``. For example, to import ``WebDriverWait``:

.. code:: python

    # Sub-packages of webdriver must still be imported from `selenium` itself
    from selenium.webdriver.support.ui import WebDriverWait

**Chrome and Firefox**

For Chrome and Firefox, you don't need to do anything special. Just instantiate the webdriver as you would normally with ``webdriver.Chrome()`` or ``webdriver.Firefox()``, passing in any Selenium specific options. Selenium Wire also has it's `own options`_ that can be passed in the ``seleniumwire_options`` attribute.

.. _`own options`: #all-options

**Remote**

Selenium Wire has limited support for using the remote webdriver client. When you create an instance of the remote webdriver, you need to specify the hostname or IP address of the machine (or container) running Selenium Wire. This allows the remote instance to communicate back to Selenium Wire with its requests and responses.

.. code:: python

    options = {
        'addr': 'hostname_or_ip'  # Address of the machine running Selenium Wire
    }
    driver = webdriver.Remote(
        command_executor='http://www.example.com',
        seleniumwire_options=options
    )

Accessing Requests
~~~~~~~~~~~~~~~~~~

Selenium Wire captures all HTTP/HTTPS traffic made by the browser :superscript:`1`.

``driver.requests``
    The list of captured requests in chronological order.

``driver.last_request``
    Convenience attribute for retrieving the most recently captured request. This is more efficient than using ``driver.requests[-1]``.

``driver.wait_for_request(path, timeout=10)``
    This method will wait for a previous request with a specific URL to complete before continuing. The ``path`` attribute can be a regex that will be matched within the request URL. Note that ``driver.wait_for_request()`` doesn't *make* a request, it just *waits* for a previous request made by some other action - and it will return the first request it finds. Also note that since ``path`` can be a regex, you must escape special characters such as question marks with a slash. A ``TimeoutException`` is raised if no match is found within the timeout period.

    For example, to wait for an AJAX request to return after a button is clicked:

    .. code:: python

        # Click a button that triggers a background request to https://server/api/products/12345/
        button_element.click()

        # Wait for the request/response to complete
        request = driver.wait_for_request('/api/products/12345/$')

``driver.request_interceptor``
    Used to set a request interceptor. See `Intercepting Requests and Responses`_.

``driver.response_interceptor``
    Used to set a response interceptor. See `Intercepting Requests and Responses`_.

**Clearing Requests**

To clear previously captured requests, use ``del``:

.. code:: python

    del driver.requests

1. Selenium Wire ignores OPTIONS requests by default, as these are typically uninteresting and just add overhead. If you want to capture OPTIONS requests, you need to set the ``ignore_http_methods`` `option`_ to ``[]``.

.. _`option`: #all-options

Request Objects
~~~~~~~~~~~~~~~

Request objects have the following attributes.

``body``
    The request body as ``bytes``. If the request has no body the value of ``body`` will be empty, i.e. ``b''``.

``date``
    The date/time the request was made.

``headers``
    A dictionary-like object of request headers. Headers are case-insensitive and duplicates are permitted. Asking for ``request.headers['user-agent']`` will return the value of the ``User-Agent`` header. If you wish to replace a header, make sure you delete the existing header first with ``del request.headers['header-name']``, otherwise you'll create a duplicate.

``method``
    The HTTP method type, e.g. ``GET`` or ``POST`` etc.

``params``
    A dictionary of request parameters. If a parameter with the same name appears more than once in the request, it's value in the dictionary will be a list.

``path``
    The request path, e.g. ``/some/path/index.html``

``querystring``
    The query string, e.g. ``foo=bar&spam=eggs``

``response``
   The response associated with the request. This will be ``None`` if the request has no response.

``url``
    The request URL, e.g. ``https://server/some/path/index.html?foo=bar&spam=eggs``

Request objects have the following methods.

``abort(error_code=403)``
    Trigger immediate termination of the request with the supplied error code. For use within request interceptors. See `Example: Block a request`_.

``create_response(status_code, headers=(), body=b'')``
    Create a response and return it without sending any data to the remote server. For use within request interceptors. See `Example: Mock a response`_.

Response Objects
~~~~~~~~~~~~~~~~

Response objects have the following attributes.

``body``
    The response body as ``bytes``. If the response has no body the value of ``body`` will be empty, i.e. ``b''``.

``date``
    The date/time the response was received.

``headers``
     A dictionary-like object of response headers. Headers are case-insensitive and duplicates are permitted. Asking for ``response.headers['content-length']`` will return the value of the ``Content-Length`` header. If you wish to replace a header, make sure you delete the existing header first with ``del response.headers['header-name']``, otherwise you'll create a duplicate.

``reason``
    The reason phrase, e.g. ``OK`` or ``Not Found`` etc.

``status_code``
    The status code of the response, e.g. ``200`` or ``404`` etc.

Intercepting Requests and Responses
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Selenium Wire allows you to modify requests and responses on the fly using interceptors. An interceptor is a function that gets invoked with requests and responses as they pass through Selenium Wire. Within an interceptor you can modify the request and response as you see fit.

You set your interceptor functions using the ``driver.request_interceptor`` and ``driver.response_interceptor`` attributes before you start using the driver. A request interceptor should accept a single argument for the request. A response interceptor should accept two arguments, one for the originating request and one for the response.

Example: Add a request header
-----------------------------

.. code:: python

    def interceptor(request):
        request.headers['New-Header'] = 'Some Value'

    driver.request_interceptor = interceptor
    driver.get(...)

    # All requests will now contain New-Header

How can I check that a header has been set correctly? You can print the headers from captured requests using ``driver.requests`` after the page has loaded, or alternatively point the webdriver at https://httpbin.org/headers which will echo the request headers back to the browser so you can view them.

Example: Replace an existing request header
-------------------------------------------

Duplicate header names are permitted in an HTTP request, so before setting the replacement header you must first delete the existing header using ``del`` like in the following example, otherwise two headers with the same name will exist (``request.headers`` is a special dictionary-like object that allows duplicates).

.. code:: python

    def interceptor(request):
        del request.headers['Referer']  # Remember to delete the header first
        request.headers['Referer'] = 'some_referer'  # Spoof the referer

    driver.request_interceptor = interceptor
    driver.get(...)

    # All requests will now use 'some_referer' for the referer

Example: Add a response header
------------------------------

.. code:: python

    def interceptor(request, response):  # A response interceptor takes two args
        if request.url == 'https://server.com/some/path':
            response.headers['New-Header'] = 'Some Value'

    driver.response_interceptor = interceptor
    driver.get(...)

    # Responses from https://server.com/some/path will now contain New-Header

Example: Add a request parameter
--------------------------------

Request parameters work differently to headers in that they are calculated when they are set on the request. That means that you first have to read them, then update them, and then write them back - like in the following example. Parameters are held in a regular dictionary, so parameters with the same name will be overwritten.

.. code:: python

    def interceptor(request):
        params = request.params
        params['foo'] = 'bar'
        request.params = params

    driver.request_interceptor = interceptor
    driver.get(...)

    # foo=bar will be added to all requests

Example: Update JSON in a POST request body
-----------------------------------------------

.. code:: python

    import json

    def interceptor(request):
        if request.method == 'POST' and request.headers['Content-Type'] == 'application/json':
            # The body is in bytes so convert to a string
            body = request.body.decode('utf-8')
            # Load the JSON
            data = json.loads(body)
            # Add a new property
            data['foo'] = 'bar'
            # Set the JSON back on the request
            request.body = json.dumps(data).encode('utf-8')
            # Update the content length
            del request.headers['Content-Length']
            request.headers['Content-Length'] = str(len(request.body))

    driver.request_interceptor = interceptor
    driver.get(...)

Example: Block a request
------------------------

You can use ``request.abort()`` to block a request and send an immediate response back to the client. An optional error code can be supplied. The default is 403 (forbidden).

.. code:: python

    def interceptor(request):
        # Block PNG, JPEG and GIF images
        if request.path.endswith(('.png', '.jpg', '.gif')):
            request.abort()

    driver.request_interceptor = interceptor
    driver.get(...)

    # Requests for PNG, JPEG and GIF images will result in a 403 Forbidden

Example: Mock a response
------------------------

You can use ``request.create_response()`` to send a custom reply back to the client. No data will be sent to the remote server.

.. code:: python

    def interceptor(request):
        if request.url == 'https://server.com/some/path':
            request.create_response(
                status_code=200,
                headers={'Content-Type': 'text/html'},  # Optional headers dictionary
                body='<html>Hello World!</html>'  # Optional body
            )

    driver.request_interceptor = interceptor
    driver.get(...)

    # Requests to https://server.com/some/path will have their responses mocked

*Have any other examples you think could be useful? Feel free to submit a PR :)*

Unset an interceptor
--------------------

To unset an interceptor, use ``del``:

.. code:: python

    del driver.request_interceptor
    del driver.response_interceptor

Limiting Request Capture
~~~~~~~~~~~~~~~~~~~~~~~~

Selenium Wire works by redirecting browser traffic through an internal proxy server it spins up in the background. As requests flow through the proxy they are intercepted and captured. Capturing requests can slow things down a little, but there are a few things you can do to restrict what gets captured.

``driver.scopes``
    This accepts a list of regular expressions that will match the hostnames of URLs to be captured. It should be set on the driver before making any requests. When empty (the default) all hosts are captured.

    .. code:: python

        driver.scopes = [
            '.*stackoverflow.*',
            '.*github.*'
        ]

        driver.get(...)  # Start making requests

        # Only request URLs containing "stackoverflow" or "github" will now be captured

    Note that even if a request is out of scope and not captured, it will still travel through Selenium Wire.

``seleniumwire_options.ignore_http_methods``
    Use this option to prevent capturing certain HTTP methods. By default, OPTIONS requests are ignored, but you might want to expand the list with other request methods.

    .. code:: python

        options = {
            'ignore_http_methods': ['HEAD', 'OPTIONS']  # Ignore all HEAD and OPTIONS requests
        }
        driver = webdriver.Firefox(seleniumwire_options=options)

    Note that even if a request is ignored and not captured, it will still travel through Selenium Wire.

``seleniumwire_options.exclude_hosts``
    Use this option to bypass Selenium Wire entirely. Any requests made to addresses listed here will go direct from the browser to the server without involving Selenium Wire. Note that if you've configured an upstream proxy then these requests will also bypass that proxy.

    .. code:: python

        options = {
            'exclude_hosts': ['host1.com', 'host2.com']  # Bypass Selenium Wire for these hosts
        }
        driver = webdriver.Firefox(seleniumwire_options=options)

``request.abort()``
    You can abort a request early by using ``request.abort()`` from within a `request interceptor`_. This will send an immediate response back to the client without the request travelling any further. You can use this mechanism to block certain types of requests (e.g. images) to improve page load performance.

    .. code:: python

        def interceptor(request):
            # Block PNG, JPEG and GIF images
            if request.path.endswith(('.png', '.jpg', '.gif')):
                request.abort()

        driver.request_interceptor = interceptor

        driver.get(...)  # Start making requests

.. _`request interceptor`: #intercepting-requests-and-responses

Proxies
~~~~~~~

If the site you are accessing sits behind a proxy server you can tell Selenium Wire about that proxy server in the options you pass to the webdriver.

The configuration takes the following format:

.. code:: python

    options = {
        'proxy': {
            'http': 'http://192.168.10.100:8888',
            'https': 'https://192.168.10.100:8888',
            'no_proxy': 'localhost,127.0.0.1'
        }
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

To use HTTP Basic Auth with your proxy, specify the username and password in the URL:

.. code:: python

    options = {
        'proxy': {
            'https': 'https://user:pass@192.168.10.100:8888',
        }
    }

For authentication other than Basic, you can supply the full value for the ``Proxy-Authorization`` header using the ``custom_authorization`` option. For example, if your proxy used the Bearer scheme:

.. code:: python

    options = {
        'proxy': {
            'https': 'https://192.168.10.100:8888',  # No username or password used
            'custom_authorization': 'Bearer mytoken123'  # Custom Proxy-Authorization header value
        }
    }

Note that the ``custom_authorization`` option is only supported by the `default backend`_.

.. _`default backend`: #backends

The proxy configuration can also be loaded through environment variables called ``HTTP_PROXY``, ``HTTPS_PROXY`` and ``NO_PROXY``:

.. code:: bash

    $ export HTTP_PROXY="http://192.168.10.100:8888"
    $ export HTTPS_PROXY="https://192.168.10.100:8888"
    $ export NO_PROXY="localhost,127.0.0.1"

SOCKS
-----

Using a SOCKS proxy is the same as using an HTTP based one:

.. code:: python

    options = {
        'proxy': {
            'http': 'socks5://user:pass@192.168.10.100:8888',
            'https': 'socks5://user:pass@192.168.10.100:8888',
            'no_proxy': 'localhost,127.0.0.1'
        }
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

You can leave out the ``user`` and ``pass`` if your proxy doesn't require authentication.

As well as ``socks5``, the schemes ``socks4`` and ``socks5h`` are supported. Use ``socks5h`` when you want DNS resolution to happen on the proxy server rather than on the client.

**Using Selenium Wire with Tor**

See `this example`_ if you want to run Selenium Wire with Tor.

.. _`this example`: https://gist.github.com/woswos/38b921f0b82de009c12c6494db3f50c5

Backends
~~~~~~~~

Selenium Wire allows you to change the backend component that performs request capture. Currently two backends are supported: the backend that ships with Selenium Wire (the default) and the mitmproxy backend.

The default backend is adequate for most purposes. However, in certain cases you may find you get better performance with the mitmproxy backend.

The mitmproxy backend relies upon the powerful open source `mitmproxy proxy server`_ being installed in your environment.

.. _`mitmproxy proxy server`: https://mitmproxy.org/

To switch to the mitmproxy backend, first install the mitmproxy package:

.. code:: bash

    pip install mitmproxy

Once installed, set the ``backend`` option in Selenium Wire's options to ``mitmproxy``:

.. code:: python

    options = {
        'backend': 'mitmproxy'
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

You can pass `mitmproxy specific options`_ to the mitmproxy backend by prefixing them with **mitm_**. For example, to change the location of the mitmproxy configuration directory which lives in your home folder by default:

.. _`mitmproxy specific options`: https://docs.mitmproxy.org/stable/concepts-options/#available-options

.. code:: python

    options = {
        'backend': 'mitmproxy',
        'mitm_confdir': '/tmp/.mitmproxy'  # Switch the location to /tmp
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

Mitmproxy includes options that can help with performance such as ``mitm_stream_large_bodies``. Setting this to a low value (e.g. '1k') has been shown to improve performance, in conjunction with the use of ``driver.scopes``.

*Note that the mitmproxy backend won't work with upstream SOCKS proxies.*

Certificates
~~~~~~~~~~~~

Selenium Wire uses it's own CA certificate to decrypt HTTPS traffic. It is not normally necessary for the browser to trust this certificate because Selenium Wire tells the browser to add it as an exception. This will allow the browser to function normally, but it will display a "Not Secure" message in the address bar. If you wish to get rid of this message you can install the CA certificate manually.

For the default backend, you can download the CA certificate `here`_. Once downloaded, navigate to "Certificates" in your browser settings and import the certificate in the "Authorities" section.

.. _`here`: https://github.com/wkeeling/selenium-wire/raw/master/seleniumwire/ca.crt

If you are using the mitmproxy backend, you can follow `these instructions`_ to install the CA certificate.

.. _`these instructions`: https://docs.mitmproxy.org/stable/concepts-certificates/#installing-the-mitmproxy-ca-certificate-manually

All Options
~~~~~~~~~~~

A summary of all options that can be passed to Selenium Wire via the ``seleniumwire_options`` webdriver attribute.

``addr``
    The IP address or hostname of the machine running Selenium Wire. This defaults to 127.0.0.1. You may want to change this to the public IP of the machine (or container) if you're using the `remote webdriver`_.

.. code:: python

    options = {
        'addr': '192.168.0.10'  # Use the public IP of the machine
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

.. _`remote webdriver`: #creating-the-webdriver

``auto_config``
    Whether Selenium Wire should auto-configure the browser for request capture. ``True`` by default.

``backend``
    The backend component that Selenium Wire will use to capture requests. The currently supported values are ``default`` (same as not specifying) or ``mitmproxy``.

.. code:: python

    options = {
        'backend': 'mitmproxy'  # Use the mitmproxy backend (see limitations above)
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

``exclude_hosts``
    A list of addresses for which Selenium Wire should be bypassed entirely. Note that if you have configured an upstream proxy then requests to excluded hosts will also bypass that proxy.

.. code:: python

    options = {
        'exclude_hosts': ['google-analytics.com']  # Bypass these hosts
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

``disable_encoding``
    Whether to disable content encoding. When set to ``True``, the ``Accept-Encoding`` header will be set to ``identity`` for all requests. This tells the server to not compress/modify the response. The default is ``False``.

.. code:: python

    options = {
        'disable_encoding': True  # Tell the server not to compress the response
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

``ignore_http_methods``
    A list of HTTP methods (specified as uppercase strings) that should be ignored by Selenium Wire and not captured. The default is ``['OPTIONS']`` which ignores all OPTIONS requests. To capture all request methods, set ``ignore_http_methods`` to an empty list:

.. code:: python

    options = {
        'ignore_http_methods': []  # Capture all requests, including OPTIONS requests
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

``port``
    The port number that Selenium Wire's backend listens on. You don't normally need to specify a port as a random port number is chosen automatically.

.. code:: python

    options = {
        'port': 9999  # Tell the backend to listen on port 9999 (not normally necessary to set this)
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

``proxy``
    The upstream proxy server configuration (if you're using a proxy).

.. code:: python

    options = {
        'proxy': {
            'http': 'http://user:pass@192.168.10.100:8888',
            'https': 'https://user:pass@192.168.10.100:8889',
            'no_proxy': 'localhost,127.0.0.1'
        }
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

``request_storage_base_dir``
    Captured requests and responses are stored in the current user's home folder by default. You might want to change this if you're running in an environment where you don't have access to the user's home folder.

.. code:: python

    options = {
        'request_storage_base_dir': '/tmp'  # Use /tmp to store captured data
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

``suppress_connection_errors``
    Whether to suppress connection related tracebacks. The default is ``True`` so that harmless errors that commonly occur at browser shutdown do not alarm users. When suppressed, the connection error message is logged at DEBUG level without a traceback. Set to ``False`` to allow exception propagation and see full tracebacks.
    *Applies to the default backend only.*

.. code:: python

    options = {
        'suppress_connection_errors': False  # Show full tracebacks for any connection errors
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

``verify_ssl``
    Whether SSL certificates should be verified. The default is ``False`` which prevents errors with self-signed certificates.

.. code:: python

    options = {
        'verify_ssl': True  # Verify SSL certificates but beware of errors with self-signed certificates
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

License
~~~~~~~

MIT
