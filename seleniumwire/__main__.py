import argparse
from argparse import RawDescriptionHelpFormatter
import logging

from seleniumwire.proxy import client, util

logging.basicConfig(level=logging.INFO, format='%(message)s')


if __name__ == '__main__':
    commands = {
        'extractcert': util.extract_cert,
        # Note that standalone will ultimately start a ProxyManager instance
        # The 'standalone' attribute could be dropped from create_proxy()
        'standalone': lambda: client.AdminClient().create_proxy(standalone=True)
    }
    parser = argparse.ArgumentParser(description='\n\nsupported commands: \n  %s'
                                                 % '\n  '.join(sorted(commands)),
                                     formatter_class=RawDescriptionHelpFormatter,
                                     usage='python -m seleniumwire <command>')
    parser.add_argument('command', help='The command name')

    args = parser.parse_args()

    try:
        commands[args.command]()
    except KeyError:
        print("Unsupported command '{}' (use --help for list of commands)".format(args.command))
