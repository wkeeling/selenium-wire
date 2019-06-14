import os
from subprocess import PIPE, Popen
import threading
import time


def _currentdir(path):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), path)


# Path to the certificate authority key.
CAKEY = _currentdir('ca.key')

# Path to the certificate authority cert.
CACERT = _currentdir('ca.crt')

# Path to the server certificate key.
CERTKEY = _currentdir('cert.key')

# Path to the directory used to store the generated certificates.
CERTDIR = _currentdir('certs/')

# Lock used to serialize access to certificate generation.
_LOCK = threading.Lock()

# The OpenSSL extensions file used for supplying the Subject Alternate Name.
DEFAULT_OPENSSL_CONF = """
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = %s
"""


def generate(hostname, certdir):
    """Generate a self-signed certificate for the supplied
    hostname if one does not already exist.

    Args:
        hostname: The hostname of the remote server.
        certdir: The directory to store the generated certificates.
    """
    certpath = '%s/%s.crt' % (certdir.rstrip('/'), hostname)
    extpath = '%s/%s.ext' % (certdir.rstrip('/'), hostname)

    with _LOCK:
        os.makedirs(certdir, exist_ok=True)

        if not os.path.isfile(certpath):
            with open(extpath, 'w') as ext:
                ext.write(DEFAULT_OPENSSL_CONF % hostname)

            new_cert_req = ['req', '-new', '-key', CERTKEY, '-subj', '/CN=%s' % hostname]
            if os.name == 'nt':
                openssl = os.path.join(os.path.dirname(__file__), 'win', 'openssl.exe')
                new_cert_req += ['-config', os.path.join(os.path.dirname(__file__), 'win', 'openssl.cnf')]
            else:
                openssl = 'openssl'
            new_cert_req.insert(0, openssl)

            epoch = '%d' % (time.time() * 1000)
            p1 = Popen(new_cert_req, stdout=PIPE)
            p2 = Popen([openssl, 'x509', '-req', '-days', '3650', '-CA', CACERT, '-CAkey', CAKEY,
                        '-set_serial', epoch, '-out', certpath, '-extfile', extpath], stdin=p1.stdout, stderr=PIPE)
            p2.communicate()
            p1.communicate()

            try:
                os.remove(extpath)
            except OSError:
                pass

        return certpath
