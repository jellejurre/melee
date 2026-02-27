---
name: melee-objdiff
description: Runs objdiff-cli on a function, compiles the source, and displays match percentage, compiler errors, and mismatches. Use when checking if a decompiled function matches the original binary.
---

# Melee objdiff Skill

This skill runs the `objdiff-cli` tool to compare your decompiled C code against the original binary. It **automatically builds the source file first** and shows any compiler errors before displaying the diff results.

## Setup

No setup required. The skill uses:
- `objdiff-cli` binary at `/home/unity/Projects/melee/objdiff-cli`
- Project's `objdiff.json` configuration
- `ninja` build system (auto-invoked to compile before diffing)

**Auto-build:** The skill always tries to compile the unit first. If compilation fails, it shows the **compiler errors** so you can fix them before checking the match.

## Usage

Provide a function name and optionally a unit name to diff:

### Recommended: With Unit Name (precise)
```bash
skill:melee-objdiff it_802E70BC main/melee/it/items/itarwinglaser
skill:melee-objdiff Command_Execute main/melee/lb/lbcommand
```

### Basic Usage (function name only - may pick wrong unit)
```bash
skill:melee-objdiff it_802E70BC
```

### How to Find the Unit Name
Unit names are in `objdiff.json` under the `units` array, formatted as:
- `main/melee/lb/lbcommand` (for `src/melee/lb/lbcommand.c`)
- `main/melee/it/items/itarwinglaser` (for `src/melee/it/items/itarwinglaser.c`)

Or ask me to find the unit for a given source file.

## Output Format

The skill displays outputs in this order:

### 1. Compiler Errors (if any)
If the build fails, you'll see:
```
=== COMPILATION FAILED ===

Error: identifier 'function_name' redeclared
  was declared as: 'void (struct HSD_GObj *)'
  now declared as: 'long (struct HSD_GObj *)'

Error: illegal use of incomplete struct/union/class 'struct HSD_GObj'
  -> Add proper #include for the type

Fix these errors and run objdiff again.
```

### 2. Symbol Match Summary
Each function with:
- ✓ or ✗ status icon
- Function name and type (FUNC/DATA)
- Address and size
- Match percentage
- **FULL ASSEMBLY listing** - All instructions with diff markers

### 3. Section Summary
Overall match per section (.text, .data, etc.)

### 4. Final Verdict
Perfect match or partial match indicator

### Example Output
```
=== SYMBOL MATCH SUMMARY ===

✗ it_802E70BC [FUNC]
   Address: 0x2E70BC  Size: 548 bytes  Match: 0%

   FULL ASSEMBLY (137 instructions):
   --------------------------------------------------
     ?: mflr r0
     4: li r4, 0x0
   >>> 8: stw r0, 0x4(r1)  <-- DIFF_ARG_MISMATCH
     12: stwu r1, -0x68(r1)
   ...

=== SECTION SUMMARY ===

✗ .text: 0.27% matched (5840 bytes)
...

============================================================
✗ PARTIAL MATCH - Some sections still need work
============================================================
```

### Diff Markers

- `>>>` prefix = instruction has a mismatch
- ` <-- DIFF_*` suffix = type of mismatch:
  - `DIFF_ARG_MISMATCH` - Argument difference (fix register usage)
  - `DIFF_DELETE` - Instruction missing in our code
  - `DIFF_INSERT` - Extra instruction in our code
  - `DIFF_REPLACE` - Different instruction

## Common Compiler Errors & Fixes

### "identifier redeclared"
```
Error: identifier 'it_802E8418' redeclared
  was declared as: 'int (struct HSD_GObj *)'
  now declared as: 'long (struct HSD_GObj *)'
```
**Fix:** Check header file for duplicate declarations. Remove scaffold-generated `UNK_PARAMS` declarations that conflict with existing ones. Ensure `bool` vs `s32` types match between `.h` and `.c`.

### "incomplete struct/union"
```
Error: illegal use of incomplete struct/union 'struct HSD_GObj'
```
**Fix:** Add proper `#include` headers. For `Item*` access, you may need:
- `#include <melee/it/item.h>`
- `#include "it/types.h"`

### "too many errors"
The compiler stops after first error. Fix errors one at a time, starting from the top of the file.

## Tips

- **Compiler errors first!** Always fix build errors before analyzing the diff
- **100% match** means your decompilation is complete and correct
- **<100% match** - read the full assembly to understand what the target does
- Use the assembly to reverse-engineer the correct C code structure
- Pay attention to:
  - Register assignments (r3-r10 are function args/return)
  - Stack frame setup (stwu, stfd patterns)
  - Function calls (bl instructions)
  - Floating point operations (fadds, fmuls, fcmpo, etc.)
  - Branch conditions (ble, bge, beq, bne, etc.)

## Finding Unit Names

If you don't know the unit name:
1. Look in `objdiff.json` for your source file
2. The `name` field is the unit name (e.g., `"main/melee/lb/lbcommand"`)
3. Or just provide the function name - the tool will search all units

## Workflow

1. **Decompile** function with `tools/decomp.py`
2. **Replace** placeholder in `.c` file with decompiled code
3. **Update** header with correct signature
4. **Run objdiff** - this skill will:
   - Try to compile
   - Show errors if build fails
   - Show diff if build succeeds
5. **Iterate** - fix errors, adjust code, run objdiff again
6. **Use permuter** at 90-99% match: If only register/scheduling differences remain, use `skill:melee-permuter` to auto-find the optimal C code

## Match Percentage Guide

| Match % | What it means | What to do |
|---------|---------------|------------|
| 0-50% | Wrong logic or types | Check assembly, fix struct types |
| 50-70% | Major type issues | Verify ItemVars struct, check field sizes |
| 70-90% | Type/scheduling mix | Fix types first, then consider permuter |
| 90-99% | Register/scheduling only | Use `skill:melee-permuter` |
| 100% | Perfect match! | Done! |

## Next Steps After 90%+ Match

If you're at 90%+ match with only register differences:

```bash
# Use the permuter to find optimal register allocation
skill:melee-permuter itArwinglaser_UnkMotion2_Anim main/melee/it/items/itarwinglaser
```

The permuter will automatically try different C code variations until it finds one that matches 100%.

## See Also
- `skill:melee-decomp-replace` - Replace functions with decompiled output
- `skill:melee-permuter` - Auto-optimize C code for 100% match
- `skill:melee-scaffold` - Add function declarations
