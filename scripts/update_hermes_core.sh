#!/bin/bash
set -e

cd /Users/bookid/workspace/hermes-agent

echo "=== 1. Resolving merge conflicts inside python files ==="
/Users/bookid/workspace/hermes-agent/venv_314/bin/python -c '
import re

for path in ["hermes_cli/kanban_decompose.py", "hermes_cli/kanban_specify.py"]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if "<<<<<<< Updated upstream" in content:
            # Replace conflict block
            content = re.sub(
                r"<<<<<<< Updated upstream\r?\n([ \t]*)with kb\.connect_closing\(\) as conn:\r?\n=======\r?\n[ \t]*with contextlib\.closing\(kb\.connect\(\)\) as conn:\r?\n>>>>>>> Stashed changes",
                r"\1with kb.connect_closing() as conn:",
                content
            )
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  ✓ Resolved conflicts in {path}")
        else:
            print(f"  - No conflict markers found in {path}")
    except Exception as e:
        print(f"  \u2717 Error processing {path}: {e}")

# 2. Patch pyproject.toml to support Python 3.14
try:
    with open("pyproject.toml", "r", encoding="utf-8") as f:
        pt = f.read()
    if "requires-python = \">=3.11,<3.14\"" in pt:
        pt = pt.replace("requires-python = \">=3.11,<3.14\"", "requires-python = \">=3.11,<3.15\"")
        with open("pyproject.toml", "w", encoding="utf-8") as f:
            f.write(pt)
        print("  ✓ Patched pyproject.toml")
    else:
        print("  - pyproject.toml is already patched or up to date")
except Exception as e:
    print(f"  \u2717 Error patching pyproject.toml: {e}")
'

echo "=== 2. Staging resolved files ==="
/usr/bin/git add hermes_cli/kanban_decompose.py hermes_cli/kanban_specify.py

echo "=== 3. Reinstalling Python dependencies ==="
/Users/bookid/workspace/hermes-agent/venv_314/bin/pip install -e .[all]

echo "=== 4. Rebuilding Web UI ==="
if [ -d "web" ]; then
  cd web
  npm install
  npm run build
fi

echo "=== Update completed successfully ==="
