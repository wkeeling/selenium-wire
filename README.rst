

Selenium Wire
=============


Selenium Wire extends Selenium's Python bindings to give you access to the underlying requests made by the browser. It is a lightweight library designed for ease of use with minimal external dependencies.

With Selenium Wire, you author your tests in just the same way as you do with Selenium, but you get an additional user-friendly API for accessing things such as the request/response headers, status code and body content.

.. image:: https://img.shields.io/badge/python-3.5%2C%203.6%2C%203.7-blue.svg
    :target: https://pypi.python.org/pypi/selenium-wire

.. image:: https://img.shields.io/pypi/v/selenium-wire.svg
        :target: https://pypi.python.org/pypi/selenium-wire

.. image:: https://travis-ci.org/wkeeling/selenium-wire.svg?branch=master
        :target: https://travis-ci.org/wkeeling/selenium-wire

.. image:: https://readthedocs.org/projects/selenium-wire/badge/?version=latest
        :target: https://selenium-wire.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

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


Because Selenium Wire extends Selenium it can be used as a drop-in replacement. Just ensure that you import from ``seleniumwire`` when importing ``webdriver``:

.. code:: python

    from seleniumwire import webdriver

Features
~~~~~~~~

* Straightforward, user-friendly API
* HTTPS support
* Access request/response bodies
* Header injection/overrides
* URL rewriting
* Proxy server support

Compatibilty
~~~~~~~~~~~~

* Selenium Wire requires Python 3 and Selenium 3.0.0

Installation
~~~~~~~~~~~~

* TODO

Browser Setup
-------------

* TODO

Accessing Requests
~~~~~~~~~~~~~~~~~~
Selenium Wire captures all HTTP requests a browser makes as a test runs. Accessing captured requests is straightforward.

You can retrieve all requests with the ``driver.requests`` attribute.

.. code:: python

    all_requests = driver.requests

The requests are just a list and can be iterated (like in the opening example) and indexed:

.. code:: python

    first_request = driver.requests[0]

If you want to access the most recent request, use the dedicated ``driver.last_request`` attribute:

.. code:: python

    last_request = driver.last_request

This is more efficient than using ``driver.requests[-1]``.

Waiting for a request
---------------------

When you ask for captured requests using ``driver.requests`` or ``driver.last_request`` you have to be sure that the requests you're interested in have actually been captured. If you ask too soon, then you may find that a request is not yet present, or is present but has no associated response.

For this you can use Selenium's existing `implicit or explicit waits`_ to wait for the DOM to change. For example:

.. code:: python

    # Click a button that triggers a background request
    button_element.click()

    # Wait for an element to appear, implying request complete
    element = WebDriverWait(ff, 10).until(EC.presence_of_element_located((By.ID, "some-element")))

    # Now check the completed request
    self.assertEqual(driver.last_request.response.status_code, 200)

Alternatively, Selenium Wire provides ``driver.wait_for_request()``. This method takes a path (actually any part of the full URL) and will wait for a request with this path to complete before continuing.

For example, to wait for an AJAX request to return after a button is clicked:

.. code:: python

    # Click a button that triggers a background request
    button_element.click()

    # Wait for the request/response to complete
    request = driver.wait_for_request('/api/products/12345/')

The ``wait_for_request()`` method will return the first *fully completed* request it finds that matches the supplied path. Fully completed meaning that the response must have returned. The method will wait up to 10 seconds by default, but you can vary that with the ``timeout`` argument:

.. code:: python

    # Wait up to 30 seconds for a request/response
    request = driver.wait_for_request('/api/products/12345/', timeout=30)

If a fully completed request is not seen within the timeout period, a ``TimeoutException`` is raised.

The ``wait_for_request()`` method does a substring match on the path, so you can pass just the part that uniquely identifies the request:

.. code:: python

    # Pass just the unique part of the path
    request = driver.wait_for_request('/12345/')

Or alternatively you can pass the full URL itself:

.. code:: python

    # Match the full URL
    request = driver.wait_for_request('https://server/api/products/12345/')

.. _`implicit or explicit waits`: https://www.seleniumhq.org/docs/04_webdriver_advanced.jsp

Clearing requests
-----------------

To clear previously captured requests, just use ``del``:

.. code:: python

    del driver.requests

This can be useful if you're only interested in capturing requests that occur when a specific action is performed, for example, the AJAX requests associated with a button click. In this case, you can clear out any previous requests with ``del`` before you click the button.

Request attributes
~~~~~~~~~~~~~~~~~~

Requests that you retrieve using ``driver.requests`` or one of the other mechanisms have the following attributes.

* ``method``
    The HTTP method type such as ``GET`` or ``POST``.

* ``path``
    The request path.

* ``headers``
    A case-insensitive dictionary of request headers. Asking for ``request.headers['user-agent']`` will return the value of the ``'User-Agent'`` header.

* ``body``
    The request body as ``bytes``. This is lazily evaluated and the binary data will be retrieved the first time this attribute is accessed. If the request has no body, the value of ``body`` will be ``None``.

* ``response``
   The response associated with the request. This will be ``None`` if the request has no response.

Response attributes
~~~~~~~~~~~~~~~~~~~

The response can be retrieved from a request via the ``response`` attribute. A response may be ``None`` if it was never captured, which may happen if you asked for it before it returned, or if the server timed out etc. A response has the following attributes.

* ``status_code``
    The status code of the response such as ``200`` or ``404``.

* ``reason``
    The reason phrase such as ``OK`` or ``Not Found``.

* ``headers``
     A case-insensitive dictionary of response headers. Asking for ``response.headers['content-length']`` will return the value of the ``'Content-Length'`` header.

* ``body``
    The response body as ``bytes``. This is lazily evaluated and the binary data will be retrieved the first time this attribute is accessed. If the response has no body, the value of ``body`` will be ``None``.

HTTPS
~~~~~

* TODO

Modifying Requests
~~~~~~~~~~~~~~~~~~

* TODO

Proxies
~~~~~~~

* TODO


License
-------

MIT


Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
