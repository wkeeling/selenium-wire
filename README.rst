

Selenium Wire
=============


Selenium Wire extends Selenium's Python bindings giving your tests access to the underlying requests made by the browser. Seleniumwire is a lightweight, *pure Python* library with *no external dependencies* other than on Selenium itself.

With Selenium Wire you get a user-friendly API for accessing things such as the request/response headers, status code and body content.

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

    # Access the requests via the `requests` attribute
    for request in driver.requests:
        print(
            request.path,
            request.response.status_code,
            request.response.headers['Content-Type']
        )

Prints:

.. code:: bash

    https://www.google.com/ 200 text/html; charset=UTF-8
    https://shavar.services.mozilla.com/downloads?client=navclient-auto-ffox&appver=61.0&pver=2.2 200 application/octet-stream
    https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_120x44dp.png 200 image/png
    https://consent.google.com/status?continue=https://www.google.com&pc=s&timestamp=1531511954&gl=GB 204 text/html; charset=utf-8
    https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png 200 image/png
    https://ssl.gstatic.com/gb/images/i2_2ec824b0.png 200 image/png
    https://www.google.com/gen_204?s=webaft&t=aft&atyp=csi&ei=kgRJW7DBONKTlwTK77wQ&rt=wsrt.366,aft.58,prt.58 204 text/html; charset=UTF-8
    ...


Because Selenium Wire extends Selenium, the API is exactly the same, but with some additional attributes for accessing requests.

Features
~~~~~~~~

* No external dependencies, just the library itself
* Straightforward, user-friendly API
* HTTPS support
* Access request/response bodies
* Header injection/overrides
* URL rewriting
* Corporate proxy support

Compatibilty
~~~~~~~~~~~~

* Selenium Wire requires Python 3 and Selenium 3.0.0

Installation
~~~~~~~~~~~~

* TODO

Browser Setup
-------------

* TODO

Request API
~~~~~~~~~~~

* TODO

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
