import argparse
from argparse import RawDescriptionHelpFormatter
import logging
import os

from seleniumwire.proxy import client, util

logging.basicConfig(level=logging.DEBUG, format='%(message)s')


def standalone_proxy(port):
    port = int(port)
    http_proxy = os.environ.get('http_proxy')
    https_proxy = os.environ.get('https_proxy')
    no_proxy = os.environ.get('no_proxy')

    proxy_config = {}

    if http_proxy:
        proxy_config['http'] = http_proxy
    if https_proxy:
        proxy_config['https'] = https_proxy
    if no_proxy:
        proxy_config['no_proxy'] = no_proxy

    c = client.AdminClient()
    c.create_proxy(port=port, proxy_config=proxy_config, standalone=True)


if __name__ == '__main__':
    commands = {
        'extractcert': util.extract_cert,
        'standaloneproxy': standalone_proxy
    }
    parser = argparse.ArgumentParser(description='\n\nsupported commands: \n  %s'
                                                 % '\n  '.join(sorted(commands)),
                                     formatter_class=RawDescriptionHelpFormatter,
                                     usage='python -m seleniumwire <command>')
    parser.add_argument('command', help='The command name')
    parser.add_argument('args', nargs='*', help='Optional list of space separated positional and keyword arguments, '
                                                'e.g. arg1 arg2 kwarg1=12345', default=None)

    args = parser.parse_args()
    pargs = [arg for arg in args.args if '=' not in arg and arg is not args.command]
    kwargs = dict([tuple(arg.split('=')) for arg in args.args if '=' in arg])

    try:
        commands[args.command](*pargs, **kwargs)
    except KeyError:
        print("Unsupported command '{}' (use --help for list of commands)".format(args.command))
    except TypeError as e:
        if 'unexpected' in str(e):
            print('Unrecognised arguments: {} {}'.format(' '.join(pargs), ' '.join('{}={}'.format(k, v)
                                                                                   for k, v in kwargs.items())))
        elif 'missing' in str(e):
            print('Missing arguments')
