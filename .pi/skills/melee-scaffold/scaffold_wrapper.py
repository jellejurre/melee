#!/usr/bin/env python3
"""
Wrapper script for scaffold.py that automatically includes the matching .h file
when a .c file is provided.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[3]  # Go back to project root from .pi/skills/melee-scaffold/
Scaffold_SCRIPT = ROOT / "tools" / "scaffold.py"


def main():
    if len(sys.argv) < 2:
        print("Usage: scaffold_wrapper.py <file1> [file2] ...")
        print("  If a .c file is provided, the matching .h file will also be scaffolded.")
        sys.exit(1)

    files_to_scaffold = []

    for arg in sys.argv[1:]:
        p = Path(arg)
        files_to_scaffold.append(str(p))

        # If it's a .c file, check for matching .h and add it
        if p.suffix == ".c":
            h_file = p.with_suffix(".h")
            if h_file.exists():
                print(f"  Found matching header: {h_file}")
                files_to_scaffold.append(str(h_file))
            else:
                print(f"  Note: No matching .h file found for {p}")

    cmd = [sys.executable, str(Scaffold_SCRIPT)] + files_to_scaffold
    print(f"Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, cwd=ROOT)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
