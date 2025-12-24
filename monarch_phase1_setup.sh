#!/usr/bin/env bash
set -euo pipefail

# MONARCH PHASE 1 - Directory Structure and Setup
# Per prompt: src/ layout, .venv, pytest, PyCharm-first.

PROJECT_NAME="monarch-tools"
PKG_NAME="monarch_tools"

bold() { printf "\033[1m%s\033[0m\n" "$*"; }
hr()   { printf "\n%s\n\n" "----------------------------------------"; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "ERROR: missing required command: $1"; exit 1; }
}

py_ok() {
  "$1" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3,12) else 1)
PY
}

choose_python() {
  if command -v python3.12 >/dev/null 2>&1 && py_ok python3.12; then
    echo "python3.12"; return 0
  fi
  if command -v python3 >/dev/null 2>&1 && py_ok python3; then
    echo "python3"; return 0
  fi
  return 1
}

hr
bold "🦋 MONARCH-TOOLS — PHASE 1 (from scratch, clean setup)"
echo "Repo folder (must be current dir): $(pwd)"
hr

need_cmd git

if [[ ! -d .git ]]; then
  echo "ERROR: This folder is not a git repo yet."
  echo "Per your prompt, first:"
  echo "  1) Create an EMPTY repo on GitHub: jkeiththomson/monarch-tools"
  echo "  2) Clone via HTTPS into /Users/keith/dev/mon"
  echo ""
  echo "Example:"
  echo "  cd /Users/keith/dev/mon"
  echo "  git clone https://github.com/jkeiththomson/monarch-tools.git"
  echo "  cd monarch-tools"
  exit 1
fi

PYBIN="$(choose_python || true)"
if [[ -z "${PYBIN}" ]]; then
  echo "ERROR: Python 3.12+ not found."
  echo "Install Python 3.12 (Homebrew):"
  echo "  brew install python@3.12"
  exit 1
fi

bold "Using Python: ${PYBIN}"
"${PYBIN}" -V

hr
bold "1) Writing pyproject.toml"
cat > pyproject.toml <<'TOML'
[project]
name = "monarch-tools"
version = "0.1.0"
description = "Python tools for customizing Monarch Money"
requires-python = ">=3.12"

[tool.black]
line-length = 88
TOML

hr
bold "2) Creating src/ layout package: src/monarch_tools/"
mkdir -p "src/${PKG_NAME}"

cat > "src/${PKG_NAME}/__init__.py" <<'PY'
"""monarch-tools: Python tools for customizing Monarch Money."""
__all__ = []
PY

cat > "src/${PKG_NAME}/__main__.py" <<'PY'
from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
PY

cat > "src/${PKG_NAME}/cli.py" <<'PY'
from __future__ import annotations

import argparse

def cmd_extract(_: argparse.Namespace) -> int:
    print("extract: stub (Phase 1)")
    return 0

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m monarch_tools")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_extract = sub.add_parser("extract", help="Extract transactions from a statement PDF (stub for now)")
    p_extract.set_defaults(func=cmd_extract)

    return p

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
PY

hr
bold "3) Creating tests/test_basic.py"
mkdir -p tests
cat > tests/test_basic.py <<'PY'
def test_sanity():
    assert 1 + 1 == 2
PY

hr
bold "4) Writing .gitignore (as specified)"
cat > .gitignore <<'GIT'
.venv/
__pycache__/
.pytest_cache/
.idea/
.DS_Store/
.egg-info/
*.egg-info/
GIT

hr
bold "5) Creating .venv and installing pytest"
rm -rf .venv
"${PYBIN}" -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install pytest
python -m pip install -e .

hr
bold "6) Generating PyCharm Run Config XML under .idea/runConfigurations/"
mkdir -p .idea/runConfigurations

cat > .idea/runConfigurations/pytest_all.xml <<'XML'
<component name="ProjectRunConfigurationManager">
  <configuration default="false" name="pytest (all)" type="tests" factoryName="py.test">
    <module name="monarch-tools" />
    <option name="PARENT_ENVS" value="true" />
    <envs />
    <option name="SDK_HOME" value="$PROJECT_DIR$/.venv/bin/python" />
    <option name="WORKING_DIRECTORY" value="$PROJECT_DIR$" />
    <option name="TEST_TYPE" value="TEST_FOLDER" />
    <option name="FOLDER_NAME" value="$PROJECT_DIR$/tests" />
    <method v="2" />
  </configuration>
</component>
XML

cat > .idea/runConfigurations/monarch_extract_stub.xml <<'XML'
<component name="ProjectRunConfigurationManager">
  <configuration default="false" name="monarch_tools: extract (stub)" type="PythonConfigurationType" factoryName="Python">
    <module name="monarch-tools" />
    <option name="SDK_HOME" value="$PROJECT_DIR$/.venv/bin/python" />
    <option name="WORKING_DIRECTORY" value="$PROJECT_DIR$" />
    <option name="IS_MODULE_SDK" value="false" />
    <option name="PARAMETERS" value="-m monarch_tools extract" />
    <method v="2" />
  </configuration>
</component>
XML

hr
bold "7) Sanity checks"
python -c "import monarch_tools; print('monarch_tools import OK:', monarch_tools.__file__)"
python -m pytest -q

hr
bold "✅ Phase 1 complete"
echo "Next (PyCharm):"
echo "  - Set Interpreter to: $PROJECT_DIR$/.venv/bin/python"
echo "  - Right-click tests/ -> Run pytest (green check)"
echo ""
echo "CLI stub:"
echo "  python -m monarch_tools extract"
