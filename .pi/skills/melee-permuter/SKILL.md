# melee-permuter

Use `decomp-permuter` to automatically find register allocation and instruction scheduling variations that better match the target binary. Use when you're at 90-99% match and the remaining differences are only in register usage or instruction order.

## Quick Start

```bash
# From project root, with venv activated
source .venv/bin/activate
./permute.sh it/items/itarwinglaser itArwinglaser_UnkMotion2_Anim
```

That's it! The script will import the function and start permuting automatically.

## When to Use

✅ **Use the permuter when:**
- Your function is **90-99% matched** in objdiff
- Differences are **only register allocation** (e.g., `lwz r4` vs `lwz r0`)
- Differences are **instruction scheduling** (load/store order)
- Logic is correct but compiler generates slightly different code

❌ **Don't use the permuter when:**
- Match is <90% (fix types/structs first)
- Wrong logic or incorrect C code
- Missing/wrong function calls
- Function doesn't compile

## Usage

### Step 1: Ensure Build Works First

The function must compile cleanly before using the permuter:

```bash
ninja
# Must succeed before continuing
```

### Step 2: Run the Permuter Script

```bash
cd /home/unity/Projects/melee/meleeDecomp
source .venv/bin/activate

# Run the permute.sh script
./permute.sh it/items/itarwinglaser itArwinglaser_UnkMotion2_Anim
```

The script will:
1. Import the function into `nonmatchings/<function_name>/`
2. Start permuting with `-j64` (64 threads)
3. Run in background, looking for improvements

### Step 3: Monitor for Results

The permuter outputs progress like:

```
Loading...
nonmatchings/itArwinglaser_UnkMotion2_Anim/base.c (itArwinglaser_UnkMotion2_Anim)
Base score: 8.88 (92.12% matched)
Iteration 1234: new high score! 6.66 (94.04% matched)
  Saved to nonmatchings/itArwinglaser_UnkMotion2_Anim/best.c
Iteration 5678: PERFECTION! (100% matched)
```

### Step 4: When to Stop

**Stop and apply results when:**
- You see `PERFECTION! (100% matched)`
- You see a good improvement that's stable

**Give up and move on when:**
- Import fails with struct redefinition errors
- Permuter can't compile `base.c`
- **No improvements after 5 minutes** (set a timer!)
- You've tried manual fixes and still stuck

## If the Permuter Fails

### Import Errors (Common)

If you see errors like:
```
Error: struct/union/enum/class tag 'ftNess_YoyoVars' redefined
Warning: failed to compile .c file.
```

**This means:** The import script included too many headers with conflicting definitions.

**Solution:** **Give up on the permuter for this function** and continue to the next function. The permuter import process is fragile and doesn't work for all files.

```bash
# Just clean up and move on
rm -rf nonmatchings/itArwinglaser_UnkMotion2_Anim

# Continue with your next function
# Don't waste time fighting the permuter import system
```

### Alternative: Manual Fixes

For register allocation issues, you can often fix manually:

**Pattern 1: Load both values before storing**
```c
// Target does: load xE18, load xE1C, store xE24, store xE28
// Add temporaries to force two registers:
s32 v1 = item->xDD4_itemVar.arwinglaser.xE18;
s32 v2 = item->xDD4_itemVar.arwinglaser.xE1C;
item->xDD4_itemVar.arwinglaser.xE24 = v1;
item->xDD4_itemVar.arwinglaser.xE28 = v2;
```

**Pattern 2: Use union for temporaries**
```c
union { s32 vals[6]; } temp;
temp.vals[0] = item->xDD4_itemVar.arwinglaser.xE18;
temp.vals[1] = item->xDD4_itemVar.arwinglaser.xE1C;
item->xDD4_itemVar.arwinglaser.xE24 = temp.vals[0];
item->xDD4_itemVar.arwinglaser.xE28 = temp.vals[1];
```

**Note:** Even at 95-99% match, it's worth trying the permuter for just 5 minutes - it might find that final tweak to reach 100%!

## Using the Results

If the permuter finds an improvement:

1. **Stop the permuter** (Ctrl+C)

2. **Review the best.c file**:
   ```bash
   cat nonmatchings/itArwinglaser_UnkMotion2_Anim/best.c | head -50
   ```

3. **Apply the changes**:
   - Copy the function body (skip typedef headers)
   - Replace your function in the source file
   - Build and verify

4. **Verify with objdiff**:
   ```bash
   skill:melee-objdiff itArwinglaser_UnkMotion2_Anim main/melee/it/items/itarwinglaser
   ```

## Complete Workflow Example

```bash
# 1. Check current match
skill:melee-objdiff itArwinglaser_UnkMotion2_Anim main/melee/it/items/itarwinglaser
# Output: 92% matched, register differences only

# 2. Ensure build works
ninja
# Must succeed

# 3. Try the permuter
source .venv/bin/activate
./permute.sh it/items/itarwinglaser itArwinglaser_UnkMotion2_Anim

# SCENARIO A: Permuter starts successfully
# Wait for improvements, then apply best.c when satisfied

# SCENARIO B: Import fails with struct errors
rm -rf nonmatchings/itArwinglaser_UnkMotion2_Anim
# Move on to next function - don't fight the permuter

# 4. If permuter worked, verify result
skill:melee-objdiff itArwinglaser_UnkMotion2_Anim main/melee/it/items/itarwinglaser
```

## Decision Flowchart

```
At 90-99% match?
    │
    ├─ NO → Fix types/structs first (skill:melee-decomp-replace)
    │
    └─ YES → Register/scheduling differences?
                │
                ├─ NO → Fix logic/assembly analysis
                │
                └─ YES → Try permuter (set 5-min timer!)
                            │
                            ├─ 100% in <5 min → SUCCESS! Apply and verify
                            ├─ Some improvement → Continue up to 5 min total
                            ├─ No improvement after 5 min → GIVE UP, move on
                            └─ FAIL (import errors) → GIVE UP immediately, move on
```

## Common Issues

| Issue | Solution |
|-------|----------|
| "struct redefined" error | **Give up** - import is broken for this file |
| No improvements after 5 min | **Give up** - set a timer and stick to it |
| Permuter crashes | Try `-j16` instead of `-j64` |
| At 95-99% match | **Still try!** - permuter might find the last 1-5% in under 5 min |

## Tips

1. **Set a 5-minute timer:** When it goes off, evaluate - if no progress, move on
2. **Don't fight import errors:** The permuter import is fragile; many files won't work
3. **95-99% is still worth trying:** A quick 5-minute permuter run might find 100%
4. **Batch your permuting:** Start multiple permuters in background, check every 5 min
5. **Know when to quit:** If import fails immediately, the permuter won't work for that file

## See Also
- `skill:melee-objdiff` - Check match percentage and decide if permuter is worth trying
- `skill:melee-decomp-replace` - Main workflow for decompiling functions
- `skill:melee-scaffold` - Add function declarations to new files
