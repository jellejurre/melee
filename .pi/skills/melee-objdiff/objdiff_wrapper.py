#!/usr/bin/env python3
"""
Wrapper for objdiff-cli that formats diff output for easy AI understanding.
"""

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
OBJDIFF_CLI = Path("/home/unity/Projects/melee/objdiff-cli")


def format_data_diff(data_diffs: list) -> list[str]:
    """Format data differences."""
    lines = []
    for diff in data_diffs:
        if diff.get("kind") == "DIFF_DELETE":
            lines.append(f"    [MISSING] {diff.get('size', '?')} bytes")
        elif diff.get("kind") == "DIFF_INSERT":
            lines.append(f"    [EXTRA] {diff.get('size', '?')} bytes")
    return lines


def format_instruction_full(instr: dict, show_diff_only: bool = False) -> str | None:
    """Format a single instruction with diff info."""
    if "instruction" not in instr:
        return None
    
    inst = instr["instruction"]
    addr = inst.get("address", "?")
    formatted = inst.get("formatted", "?")
    
    # Check if this instruction has a diff
    has_diff = instr.get("diff_kind") is not None or (instr.get("left") and instr.get("right"))
    
    if show_diff_only and not has_diff:
        return None
    
    # Format with diff marker
    if has_diff:
        diff_kind = instr.get("diff_kind", "CHANGED")
        return f"  {addr}: {formatted}  <-- {diff_kind}"
    else:
        return f"  {addr}: {formatted}"


def format_diff_detail(instr: dict) -> list[str]:
    """Format detailed diff showing left vs right instructions."""
    lines = []
    
    left_inst = instr.get("left", {})
    right_inst = instr.get("right", {})
    diff_kind = instr.get("diff_kind", "UNKNOWN")
    
    if left_inst and right_inst:
        left_formatted = left_inst.get("formatted", "?")
        right_formatted = right_inst.get("formatted", "?")
        left_addr = left_inst.get("address", "?")
        right_addr = right_inst.get("address", "?")
        
        lines.append(f"      [OURS]   {left_addr}: {left_formatted}")
        lines.append(f"      [TARGET] {right_addr}: {right_formatted}")
    elif diff_kind == "DIFF_DELETE":
        # Instruction exists in target but not in ours
        if right_inst:
            right_formatted = right_inst.get("formatted", "?")
            right_addr = right_inst.get("address", "?")
            lines.append(f"      [MISSING in ours] {right_addr}: {right_formatted}")
    elif diff_kind == "DIFF_INSERT":
        # Instruction exists in ours but not in target
        if left_inst:
            left_formatted = left_inst.get("formatted", "?")
            left_addr = left_inst.get("address", "?")
            lines.append(f"      [EXTRA in ours] {left_addr}: {left_formatted}")
    
    return lines


def get_object_path(unit: str) -> Path:
    """Get the path to the object file for a unit."""
    # Unit name format: main/melee/lb/lbcommand
    # Object path: build/GALE01/obj/melee/lb/lbcommand.o (target) or build/GALE01/src/... (base)
    parts = unit.split('/')
    # Try src path first (our built object)
    obj_path = PROJECT_ROOT / "build" / "GALE01" / "src" / "/".join(parts[1:])
    obj_path = obj_path.with_suffix(".o")
    if not obj_path.exists():
        # Fall back to obj path (target object)
        obj_path = PROJECT_ROOT / "build" / "GALE01" / "obj" / "/".join(parts[1:])
        obj_path = obj_path.with_suffix(".o")
    return obj_path


def get_source_path(unit: str) -> Path | None:
    """Get the path to the source file for a unit."""
    # Unit name format: main/melee/lb/lbcommand
    # Source path: src/melee/lb/lbcommand.c
    parts = unit.split('/')
    for ext in ['.c', '.cpp', '.cp']:
        src_path = PROJECT_ROOT / "src" / "/".join(parts[1:])
        src_path = src_path.with_suffix(ext)
        if src_path.exists():
            return src_path
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: objdiff_wrapper.py <function_name> [unit_name]")
        print("")
        print("Examples:")
        print("  objdiff_wrapper.py it_802E70BC main/melee/it/items/itarwinglaser")
        print("  objdiff_wrapper.py Command_Execute main/melee/lb/lbcommand")
        sys.exit(1)

    symbol = sys.argv[1]
    unit = sys.argv[2] if len(sys.argv) > 2 else None

    # Auto-rebuild the object file if unit is specified
    if unit:
        obj_path = get_object_path(unit)
        src_path = get_source_path(unit)
        
        if src_path and obj_path.exists():
            if src_path.stat().st_mtime > obj_path.stat().st_mtime:
                print(f"Source file is newer than object, running ninja...")
                # Use relative path for ninja target
                rel_obj_path = obj_path.relative_to(PROJECT_ROOT)
                result = subprocess.run(["ninja", "-j1", str(rel_obj_path)], 
                                      cwd=PROJECT_ROOT, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"  Built: {obj_path}")
                else:
                    print(f"  Build failed: {result.stderr}")
        elif not obj_path.exists():
            print(f"Note: Object file not found: {obj_path}")
            print("  Run ninja first to build the project.")

    # Build command
    cmd = [str(OBJDIFF_CLI), "diff", "-p", str(PROJECT_ROOT), "--format", "json", "--output", "-"]
    
    if unit:
        cmd.extend(["-u", unit])
    
    cmd.append(symbol)

    print(f"Running objdiff-cli for symbol: {symbol}")
    if unit:
        print(f"Unit: {unit}")
    print("-" * 60)

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(result.returncode)

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        print(result.stdout[:500])
        sys.exit(1)

    # Parse output - symbols and sections are in "left" (target/our build)
    left = data.get("left", {})
    symbols = left.get("symbols", [])
    sections = left.get("sections", [])

    # Find matching symbols
    matching_symbols = [s for s in symbols if symbol in s.get("name", "")]

    print("\n=== SYMBOL MATCH SUMMARY ===\n")

    if not matching_symbols:
        print(f"No symbols found matching '{symbol}'")
        print("\nAvailable symbols:")
        for s in symbols[:20]:
            name = s.get("name", "?")
            match = s.get("match_percent", 0)
            status = "✓" if match == 100.0 else "✗"
            print(f"  {status} {name} ({match}%)")
        if len(symbols) > 20:
            print(f"  ... and {len(symbols) - 20} more")
    else:
        for sym in matching_symbols:
            name = sym.get("name", "?")
            match = sym.get("match_percent", 0)
            addr = sym.get("address", "?")
            size = sym.get("size", "?")
            flags = sym.get("flags", 0)
            
            sym_type = "FUNC" if flags == 1 else "DATA" if flags == 2 else "UNK"
            status = "✓" if match == 100.0 else "✗"
            
            print(f"{status} {name} [{sym_type}]")
            if addr != "?":
                print(f"   Address: 0x{addr}  Size: {size} bytes  Match: {match}%")
            else:
                print(f"   Size: {size} bytes  Match: {match}%")
            
            # Show FULL assembly for the function - crucial for understanding how to fix
            if "instructions" in sym:
                instructions = sym.get("instructions", [])
                if instructions:
                    print(f"\n   FULL ASSEMBLY ({len(instructions)} instructions):")
                    print(f"   {'-' * 50}")
                    
                    # Show all instructions, marking diffs
                    for instr in instructions:
                        line = format_instruction_full(instr, show_diff_only=False)
                        if line:
                            # Highlight mismatched instructions
                            if instr.get("diff_kind"):
                                print(f"   >>> {line}")
                            else:
                                print(f"   {line}")
                    
                    print(f"   {'-' * 50}")
            
            # Show mismatched instructions separately with detailed diff
            if match < 100.0 and "instructions" in sym:
                instructions = sym.get("instructions", [])
                mismatch_details = []
                for instr in instructions:
                    if instr.get("diff_kind"):
                        details = format_diff_detail(instr)
                        if details:
                            mismatch_details.extend(details)
                
                if mismatch_details:
                    print(f"\n   DETAILED DIFF (what we have vs what we need):")
                    for detail in mismatch_details[:30]:  # Show first 30 lines
                        print(detail)
                    if len(mismatch_details) > 30:
                        print(f"      ... and {len(mismatch_details) - 30} more mismatched instructions")
            
            # Show data diff for data symbols
            if "data_diff" in sym:
                diff_lines = format_data_diff(sym.get("data_diff", []))
                if diff_lines:
                    print("\n   Data differences:")
                    for line in diff_lines:
                        print(line)
            
            print()

    # Show section summary
    print("=== SECTION SUMMARY ===\n")
    for section in sections:
        name = section.get("name", "?")
        match = section.get("match_percent", 0)
        size = section.get("size", "?")
        status = "✓" if match == 100.0 else "✗"
        print(f"{status} {name}: {match}% matched ({size} bytes)")

    # Overall verdict
    all_complete = all(s.get("match_percent", 0) == 100.0 for s in sections)
    print("\n" + "=" * 60)
    if all_complete:
        print("✓ PERFECT MATCH - All sections are 100% matched!")
    else:
        print("✗ PARTIAL MATCH - Some sections still need work")
    print("=" * 60)


if __name__ == "__main__":
    main()
