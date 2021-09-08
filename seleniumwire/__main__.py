import argparse
import logging
import signal
from argparse import RawDescriptionHelpFormatter
from typing import Callable, Dict

from seleniumwire import backend, utils

logging.basicConfig(level=logging.DEBUG, format='%(message)s')


def standalone_proxy(port=0, addr='127.0.0.1'):
    b = backend.create(
        port=int(port),
        addr=addr,
        options={
            'standalone': True,
            'verify_ssl': False,
        },
    )

    # Configure shutdown handlers
    signal.signal(signal.SIGTERM, lambda *_: b.shutdown())
    signal.signal(signal.SIGINT, lambda *_: b.shutdown())


# Mapping of command names to the command callables
COMMANDS: Dict[str, Callable] = {'extractcert': utils.extract_cert, 'standaloneproxy': standalone_proxy}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='\n\nsupported commands: \n  %s' % '\n  '.join(sorted(COMMANDS)),
        formatter_class=RawDescriptionHelpFormatter,
        usage='python -m seleniumwire <command>',
    )
    parser.add_argument('command', help='The command name')
    parser.add_argument(
        'args',
        nargs='*',
        help='Optional list of space separated positional and keyword arguments, e.g. arg1 arg2 kwarg1=12345',
        default=None,
    )

    args = parser.parse_args()
    pargs = [arg for arg in args.args if '=' not in arg and arg is not args.command]
    kwargs: Dict[str, str] = dict([arg.split('=') for arg in args.args if '=' in arg])

    try:
        COMMANDS[args.command](*pargs, **kwargs)
    except KeyError:
        print("Unsupported command '{}' (use --help for list of commands)".format(args.command))
    except TypeError as e:
        if 'unexpected' in str(e):
            print(
                'Unrecognised arguments: {} {}'.format(
                    ' '.join(pargs), ' '.join('{}={}'.format(k, v) for k, v in kwargs.items())
                )
            )
        elif 'missing' in str(e):
            print('Missing arguments')
        else:
            print(str(e))
