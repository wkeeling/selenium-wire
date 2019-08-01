Selenium Wire
=============

Selenium Wire extends Selenium's Python bindings to give your tests access to the underlying requests made by the browser. It is a lightweight library designed for ease of use with minimal external dependencies.

With Selenium Wire, you author your tests in just the same way as you do with Selenium, but you get an additional user-friendly API for accessing things such as the request/response headers, status code and body content.

.. image:: https://travis-ci.org/wkeeling/selenium-wire.svg?branch=master
        :target: https://travis-ci.org/wkeeling/selenium-wire

.. image:: https://codecov.io/gh/wkeeling/selenium-wire/branch/master/graph/badge.svg
        :target: https://codecov.io/gh/wkeeling/selenium-wire

.. image:: https://img.shields.io/badge/python-3.4%2C%203.5%2C%203.6%2C%203.7-blue.svg
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

* Straightforward, user-friendly API
* All HTTP/HTTPS requests captured
* Access to request/response bodies
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

  * `Using Self-Signed Certificates`_
  * `Accessing Requests`_
  * `Waiting for a Request`_
  * `Clearing Requests`_

- `Request Attributes`_

- `Response Attributes`_

- `Modifying Requests`_

  * `Modifying Headers`_
  * `Rewriting URLs`_

- `Proxies`_

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

You will however need to ensure that you have downloaded the `Gecko driver`_ and `Chrome driver`_ for Firefox and Chrome to be remotely controlled - the same as if you were using Selenium directly. Once downloaded, these executables should be placed somewhere on the system path.

.. _`Gecko driver`: https://github.com/mozilla/geckodriver/

.. _`Chrome driver`: https://sites.google.com/a/chromium.org/chromedriver/

**Safari**

There are a few manual steps that have to be carried out before you can use Safari with Selenium Wire.

#. You must allow Safari to be remotely controlled by selecting "Allow Remote Automation" from Safari's "Develop" menu.

#. You must install Selenium Wire's root certificate into your Mac's keystore by following these steps:

   * First extract the certificate with ``python -m seleniumwire extractcert``. You should see a file called ``ca.crt`` in your current working directory.

   * Now open your Mac's Keychain Access utility (located in Applications > Utilities).

   * From the "File" menu, select "Import Items".

   * Browse to the ``ca.crt`` file you just extracted and import it.

   * Click on "Certificates" in the left hand side of the Key Chain Access utility and you should now see the Selenium Wire CA certificate listed.

   * Double-click the certificate in the right hand pane to open its properties.

   * At the top of the properties window that opens, expand the "Trust" section and select "Always Trust" in the top drop down menu.

   * Close the properties window (you may be prompted to enter your password).

   * Quit the Keychain Access utility.

#. You need to tell Safari to use a proxy server for its HTTP and HTTPS traffic.

   * From Safari's "Safari" menu, open "Preferences".

   * Click the "Advanced" tab at the top.

   * Click the "Change Settings..." button for the "Proxies" option.

   * Check the "Web Proxy (HTTP)" checkbox and enter "localhost" in the server box, and a port (e.g. 12345) in the box next to it.

   * Check the "Secure Web Proxy (HTTPS)" checkbox and repeat the previous step for server and port.

   * Click "OK" on the proxies window, and then "Apply" on the network window before closing it.

**Edge**

Like Safari, Microsoft Edge requires some manual configuration before it can be used with Selenium Wire.

#. You must install `Microsoft's WebDriver`_ so that Edge can be remotely controlled - the same as if you were using Selenium directly.

#. You must install Selenium Wire's root certificate into your PC's certificate store by following these steps:

   * First extract the certificate with ``python -m seleniumwire extractcert``. You should see a file called ``ca.crt`` in your current working directory.

   * Open Internet Options (you can search for it using Cortana on Windows 10).

   * Click the "Content" tab and then the "Certificates" button.

   * Press the "Import..." button to open the Certificate Import Wizard, then press "Next".

   * Browse to the ``ca.crt`` you just extracted and press "Next".

   * Select the "Place all certficates in the following store" option and browse to "Trusted Root Certification Authorities", press "OK" and then "Next".

   * Press "Finish" on the final screen of the wizard, and then "OK" on all open windows.

#. You need to tell Edge to use a proxy server for its HTTP and HTTPS traffic.

   * Open Internet Options (you can search for it from the Windows 10 start menu).

   * Click the "Connections" tab and then the "LAN settings" button.

   * Tick the box that says "Use a proxy server for your LAN...".

   * In the "Address" box enter "localhost" and in the "Port" box a port number (e.g. 12345).

   * Click "OK" and then "OK" on the Internet Options window.

.. _`Microsoft's WebDriver`: http://go.microsoft.com/fwlink/?LinkId=619687

Usage
~~~~~

Ensure that you import ``webdriver`` from the ``seleniumwire`` package:

.. code:: python

    from seleniumwire import webdriver

For sub-packages of ``webdriver``, you can continue to import these directly from ``selenium``. For example, to import ``WebDriverWait``:

.. code:: python

    # Sub-packages of webdriver must still be imported from `selenium` itself
    from selenium.webdriver.support.ui import WebDriverWait

Then it's just a matter of creating a new driver instance.

For Firefox and Chrome, you don't need to pass any Selenium Wire specific options (you can still pass any of your own webdriver specific options however).

**Firefox**

.. code:: python

    driver = webdriver.Firefox()

**Chrome**

.. code:: python

    driver = webdriver.Chrome()

**Safari**

For Safari, you need to tell Selenium Wire the port number you selected when you configured the browser in **Browser Setup**.
For example, if you chose port 12345, then you would pass it like this:

.. code:: python

    options = {
        'port': 12345
    }
    driver = webdriver.Safari(seleniumwire_options=options)

**Edge**

For Edge, you need to tell Selenium Wire the port number you selected when you configured the browser in **Browser Setup**.
For example, if you chose port 12345, then you would pass it like this:

.. code:: python

    options = {
        'port': 12345
    }
    driver = webdriver.Edge(seleniumwire_options=options)

Using Self-Signed Certificates
------------------------------

If the site you are testing uses a self-signed certificate then you must set the ``verify_ssl`` option to ``False`` in the ``seleniumwire_options``:

.. code:: python

    options = {
        'verify_ssl': False
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

This this will need to be done regardless of the type of browser you are using.

Accessing Requests
------------------

Selenium Wire captures all HTTP/HTTPS traffic made by the browser during a test. Accessing captured requests is straightforward.

You can retrieve all requests with the ``driver.requests`` attribute.

.. code:: python

    all_requests = driver.requests

The requests are just a list and can be iterated (like in the opening example) and indexed:

.. code:: python

    first_request = driver.requests[0]

The list of requests is in chronological order. If you want to access the most recent request, use the dedicated ``driver.last_request`` attribute:

.. code:: python

    last_request = driver.last_request

This is more efficient than using ``driver.requests[-1]``.

Waiting for a Request
---------------------

When you ask for captured requests using ``driver.requests`` or ``driver.last_request`` you have to be sure that the requests you're interested in have actually been captured. If you ask too soon, then you may find that a request is not yet present, or is present but has no associated response.

**Using implicit or explicit waits**

One way to achieve this is to use Selenium's existing `implicit or explicit waits`_ to wait for the DOM to change. For example:

.. code:: python

    # Click a button that triggers a background request
    button_element.click()

    # Wait for an element to appear, implying request complete
    element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "some-element")))

    # Now check the completed request
    assert driver.last_request.response.status_code == 200

**Using driver.wait_for_request()**

Alternatively, Selenium Wire provides ``driver.wait_for_request()``. This method will wait for a previous request with a specific path to complete before allowing the test to continue.

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

The ``wait_for_request()`` method does a substring match on the path so you can pass just the part that uniquely identifies the request:

.. code:: python

    # Pass just the unique part of the path
    request = driver.wait_for_request('/12345/')

Or alternatively you can pass the full URL itself:

.. code:: python

    # Match the full URL
    request = driver.wait_for_request('https://server/api/products/12345/')

.. _`implicit or explicit waits`: https://www.seleniumhq.org/docs/04_webdriver_advanced.jsp

Clearing Requests
-----------------

To clear previously captured requests, just use ``del``:

.. code:: python

    del driver.requests

This can be useful if you're only interested in capturing requests that occur when a specific action is performed, for example, the AJAX requests associated with a button click. In this case you can clear out any previous requests with ``del`` before you click the button.

Request Attributes
~~~~~~~~~~~~~~~~~~

Requests that you retrieve using ``driver.requests`` or one of the other mechanisms have the following attributes.

``method``
    The HTTP method type such as ``GET`` or ``POST``.

``path``
    The request path.

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

To clear the header overrides that you have set, just use ``del``:

.. code:: python

    del driver.header_overrides

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

To clear the rewrite rules that you have set, just use ``del``:

.. code:: python

    del driver.rewrite_rules

Proxies
~~~~~~~

Selenium Wire captures requests by using its own proxy server under the covers. This means you cannot use the webdriver's ``DesiredCapabilities`` API to configure your own proxy, like you might when using Selenium directly.

If the site you are testing sits behind a proxy server you can tell Selenium Wire about that proxy server in the options you pass to the webdriver instance.

The configuration for the proxy server should be specified as a URL in the format ``http://username:password@server:port``. The username and password are optional and can be specified when a proxy server requires authentication. Basic authentication is used by default.

You can configure a proxy for the http and https protocols and optionally set a value for ``no_proxy`` - which should be a comma separated list of hostnames where the proxy should be bypassed. For example:

.. code:: python

    options = {
        'proxy': {
            'http': 'http://username:password@host:port',
            'https': 'https://username:password@host:port',
            'no_proxy': 'localhost,127.0.0.1,dev_server:8080'
        }
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

The proxy configuration can also be loaded through environment variables called ``http``, ``https`` and ``no_proxy``. The proxy configuration in the options passed to the webdriver instance will take precedence over environment variable configuration if both are specified.

**Proxy authentication other than Basic**

Basic authentication is used by default when supplying a username and password in the URL - as described above. If you are connecting to an upstream proxy server that uses an authentication scheme different to Basic, then you can supply the full value for the ``Proxy-Authorization`` header using the ``custom_authorization`` option. For example, if your proxy used the Bearer scheme:

.. code:: python

    options = {
        'proxy': {
            'http': 'http://host:port',
            'https': 'https://host:port',
            'no_proxy': 'localhost,127.0.0.1,dev_server:8080',
            'custom_authorization': 'Bearer mytoken123'  # Custom Proxy-Authorization header value
        }
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

Other Options
~~~~~~~~~~~~~

Other options that can be passed to Selenium Wire via the ``seleniumwire_options`` webdriver attribute:

``connection_timeout``
    The number of seconds Selenium Wire should wait before timing out requests. The default is 5 seconds. Increase this value if you're working with a slow server that needs more time to respond. Set to ``None`` for no timeout.

.. code:: python

    options = {
        'connection_timeout': None  # Never timeout
    }
    driver = webdriver.Firefox(seleniumwire_options=options)

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
