

Selenium Wire
=============


Selenium Wire extends Selenium's Python bindings to give your tests access to the underlying requests made by the browser. Selenium Wire is a lightweight, *pure Python* library with *no external dependencies* other than on Selenium itself.

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

* No external dependencies, just the library itself
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

Accessing requests
~~~~~~~~~~~~~~~~~~
Selenium Wire provides a number of ways to access captured browser requests.

You can retrieve all requests with the ``driver.requests`` attribute.

.. code:: python

    all_requests = driver.requests:

The requests are just a list and can be iterated (as in the opening example) and indexed normally:

.. code:: python

    first_request = driver.requests[0]

If you want to access just the most recent request, then you can use the dedicated ``driver.last_request`` attribute:

.. code:: python

    last_request = driver.last_request

This is more efficient than using ``driver.requests[-1]``.

To clear previously captured requests, just use ``del``:

.. code:: python

    del driver.requests

This can be useful if you're only interested in capturing the requests that occur when a specific action is performed, for example, the AJAX requests associated with a button click. In this case, you can clear out any previous requests with ``del`` before you perform the action.

When you ask for captured requests using ``driver.requests`` or ``driver.last_request`` you have to be sure that the requests you're interested in have actually been captured. If your test asks too soon, then you may find that the request is not yet present, or it is present but it has no associated response.

One way aroun
To help with this, Selenium Wire provides


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
