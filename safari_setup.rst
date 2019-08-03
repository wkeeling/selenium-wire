Safari Setup
------------

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
