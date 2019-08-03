Edge Setup
----------

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
