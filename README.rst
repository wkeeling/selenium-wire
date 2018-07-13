

Selenium Wire
=============


Selenium Wire extends Selenium's Python bindings to give your tests access to the underlying requests made by the browser. With Selenium Wire you get a user-friendly API for accessing things such as the request/response headers, status code and body content.

## Simple Example

```
from seleniumwire import webdriver

driver = webdriver.Firefox()
driver.get("http://www.google.com")

for request in driver.requests:
    print()



```

Other than the minor change to the `webdriver` import, you use the webdriver in just the same way as if you were using Selenium itself.



.. image:: https://img.shields.io/pypi/v/selenium-wire.svg

        :target: https://pypi.python.org/pypi/selenium-wire

.. image:: https://travis-ci.org/wkeeling/selenium-wire.svg?branch=master
        :target: https://travis-ci.org/wkeeling/selenium-wire

.. image:: https://readthedocs.org/projects/selenium-wire/badge/?version=latest
        :target: https://selenium-wire.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status


Features
--------

* TODO



License
-------

MIT


Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
