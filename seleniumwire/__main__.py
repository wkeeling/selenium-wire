import argparse
from argparse import RawDescriptionHelpFormatter
from seleniumwire.proxy import util


if __name__ == '__main__':
    commands = {
        'extractcert': util.extract_cert
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
