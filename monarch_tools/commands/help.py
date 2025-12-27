import argparse

def cmd_help(args: argparse.Namespace) -> int:
    from monarch_tools.console import build_parser
    parser = build_parser()
    parser.print_help()
    return 0
