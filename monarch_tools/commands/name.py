import argparse

def cmd_name(args: argparse.Namespace) -> int:
    print(f"name: {args.name}")
    return 0
