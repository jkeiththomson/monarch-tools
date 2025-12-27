# Phase 1 Invariants (Monarch Tools)

This document is the Phase 1 contract for the Monarch Tools project.
If any invariant fails, we do NOT patch random files.
We fix the generator and regenerate the tree until these invariants pass again.

## Phase 1 Goal

Phase 1 exists to prove the CLI scaffolding is stable:
- A working command dispatcher
- A predictable layout
- Zero third-party dependencies
- Commands run from a clean checkout with no setup tricks

No PDF parsing. No data extraction logic.

## Project Identity Invariants

- Project name: monarch-tools
- Import root: monarch_tools

## Layout Invariants

Required files:
- monarch_tools/__init__.py
- monarch_tools/__main__.py
- monarch_tools/console.py
- monarch_tools/commands/hello.py
- monarch_tools/commands/name.py
- monarch_tools/commands/help.py
- monarch_tools/commands/extract.py

No src/ layout in Phase 1.

## Execution Invariants

These must work from repo root:

python3 -m monarch_tools hello
python3 -m monarch_tools name Keith
python3 -m monarch_tools help
python3 -m monarch_tools extract chase sample.statement.pdf
