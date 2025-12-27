from __future__ import annotations

import argparse
from typing import Callable

from monarch_tools.commands.hello import cmd_hello
from monarch_tools.commands.name import cmd_name
from monarch_tools.commands.help import cmd_help
from monarch_tools.commands.extract import cmd_extract

CommandFn = Callable[[argparse.Namespace], int]

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m monarch_tools",
        add_help=False,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_hello = subparsers.add_parser("hello")
    p_hello.set_defaults(_handler=cmd_hello)

    p_name = subparsers.add_parser("name")
    p_name.add_argument("name")
    p_name.set_defaults(_handler=cmd_name)

    p_help = subparsers.add_parser("help")
    p_help.set_defaults(_handler=cmd_help)

    p_extract = subparsers.add_parser("extract")
    p_extract.add_argument("account_type", choices=["chase", "amex", "citi"])
    p_extract.add_argument("account_pdf")
    p_extract.set_defaults(_handler=cmd_extract)

    return parser

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler: CommandFn = getattr(args, "_handler")
    return int(handler(args))
