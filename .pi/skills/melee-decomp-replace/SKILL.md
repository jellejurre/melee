# melee-decomp-replace

Replaces a function header in a header file and the function implementation in a C file with decompiled output from decomp.py.

## Quick Start

1. Run `tools/decomp.py --no-copy <function_name>` to get decompiled output
2. Update the header with the correct function signature
3. Replace the C function with decompiled output
4. Build with `ninja` and fix any errors
5. Run objdiff to verify match percentage

## Example

For function `it_802ADEF0` in `src/melee/it/items/itfoxblaster.*`:

**Header:**
```c
/* 2ADEF0 */ void it_802ADEF0(HSD_GObj* item_gobj);
```

**C file:**
```c
void it_802ADEF0(void)
{
    it_802ADF10();
}
```

## Common Issues and Fixes

### Scaffold Duplicates
After running scaffold, you'll see:
```c
/* 2E79C8 */ UNK_RET it_802E79C8(UNK_PARAMS);
```

**Fix:** Remove these and replace with actual signatures. Watch for duplicates!

### Type Mismatches
- `bool` vs `s32` - m2c returns `s32`, original may use `bool`
- Match types between `.h` and `.c` files

### Incomplete Struct Errors
```
Error: illegal use of incomplete struct 'struct HSD_GObj'
```
**Fix:** Add proper `#include` headers for types being accessed.

---

# Item Decompilation Guide

## Understanding Item Structures

Items use a union for item-specific variables at offset `0xDD4`:

```c
struct Item {
    // ... common fields (0x000 - 0xDD3)
    union Item_ItemVars {
        itFoxLaser_ItemVars foxlaser;
        itArwingLaser_ItemVars arwinglaser;
        itFoxBlaster_ItemVars foxblaster;
        // ... 80+ item-specific structs
    } xDD4_itemVar;
};
```

## Step-by-Step Item Decompilation

### Step 1: Identify the Correct ItemVars Struct

1. **Check the union** in `src/melee/it/types.h`:
   ```bash
   grep -n "arwinglaser\|foxlaser" src/melee/it/types.h
   ```

2. **Find the struct definition** in `itCharItems.h` or `itCommonItems.h`:
   ```bash
   grep -A 10 "typedef struct itFoxLaser_ItemVars" src/melee/it/itCharItems.h
   ```

3. **If missing, create it** - see "Creating New ItemVars Structs" below

### Step 2: Determine Offsets from Assembly

When m2c uses wrong struct members (e.g., `foxblaster` for arwing laser):

1. **View the assembly**:
   ```bash
   cat build/GALE01/asm/melee/it/items/itarwinglaser.s | grep -A 30 "itArwinglaser_UnkMotion2_Anim"
   ```

2. **Extract offsets** from instructions:
   - `lwz r4, 0xe18(r31)` → offset 0xE18 from Item pointer
   - `sth r0, 0xe30(r31)` → offset 0xE30, 16-bit store

3. **Calculate union offset**: `0xE18 - 0xDD4 = 0x44` (68 bytes into union)

4. **Build the struct** with fields at correct offsets

### Step 3: Required Includes for Item Files

Standard include pattern (copy from `itfoxlaser.c`):

```c
#include "itarwinglaser.h"

#include "it/inlines.h"        // GET_ITEM macro
#include "it/it_2725.h"        // Helper functions
#include "it/itCharItems.h"    // ItemVars structs  
#include "it/types.h"          // Full Item struct

#include <platform.h>
#include <baselib/gobj.h>
#include <melee/it/item.h>
```

### Step 4: Accessing Item Data

```c
Item* item = GET_ITEM(arg0);  // arg0 is Item_GObj*

// Access union member:
item->xDD4_itemVar.arwinglaser.xE18

// DON'T trust m2c's struct choice - verify with assembly!
```

### Step 5: Required Includes for Item Files

Item files need specific includes to access Item structures:

```c
#include "itarwinglaser.h"

#include "it/inlines.h"        // For GET_ITEM macro
#include "it/it_2725.h"        // For helper functions (it_80272C6C, etc.)
#include "it/itCharItems.h"    // For ItemVars structs
#include "it/types.h"          // For full Item struct definition

#include <platform.h>
#include <baselib/gobj.h>
#include <melee/it/item.h>     // Item function declarations
```

**Key pattern**: Look at working files like `src/melee/it/items/itfoxlaser.c` for include patterns.

## Creating New ItemVars Structs

### When to Create a New Struct

- Your item doesn't have a struct in the union
- m2c uses wrong struct (e.g., `foxblaster` for unrelated item)
- Assembly accesses offsets that don't match existing structs

### How to Create One

1. **Find the union position** in `types.h`:
   ```c
   // Count bytes of earlier members to find offset
   itFoxLaser_ItemVars foxlaser;      // ~24 bytes
   itArwingLaser_ItemVars arwinglaser; // ← Add here
   itFreeze_ItemVars freeze;
   ```

2. **Add to `itCharItems.h`** (or `itCommonItems.h`):
   ```c
   typedef struct itArwingLaser_ItemVars {
       /*  +0 ip+DD4 */ u8 x0_pad[0x44];   // Padding to reach first used offset
       /* +44 ip+E18 */ s32 xE18;
       /* +48 ip+E1C */ s32 xE1C;
       /* +4C ip+E20 */ s32 xE20;
       /* +50 ip+E24 */ s32 xE24;
       /* +54 ip+E28 */ s32 xE28;
       /* +58 ip+E2C */ s32 xE2C;
       /* +5C ip+E30 */ s16 xE30;          // s16 for 'sth' instruction
       /* +5E ip+E32 */ s16 xE32_pad;      // Alignment
   } itArwingLaser_ItemVars;
   ```

3. **Add to union** in `types.h`:
   ```c
   union Item_ItemVars {
       // ...
       itFoxLaser_ItemVars foxlaser;
       itArwingLaser_ItemVars arwinglaser;  // ← Add this
       itFreeze_ItemVars freeze;
       // ...
   };
   ```

### Offset Naming Convention

Use the full offset from Item struct start:
- `xE18` means offset 0xE18 from `Item*`
- This equals offset `0xE18 - 0xDD4 = 0x44` in the union
- Makes it easy to verify against assembly

## Matching Compiler Output

### Stack Frame Size

Compare `stwu r1, -0xXX(r1)`:
- Target: `stwu r1, -0x18(r1)`
- Yours: `stwu r1, -0x20(r1)` ← Too many locals!

**Fix:** Reduce temporary variables, reuse values directly.

### Register Allocation

Study instruction order:
```
Target: lwz r4, 0xe18(r31)  ← Load to r4
        lwz r0, 0xe1c(r31)  ← Load to r0  
        stw r4, 0xe24(r31)  ← Store r4
        stw r0, 0xe28(r31)  ← Store r0
```

If your output stores immediately after each load, the compiler isn't optimizing the same way.

### Data Types from Instructions

| Instruction | Type | Use |
|-------------|------|-----|
| `lwz`/`stw` | `s32`/`u32` | 32-bit load/store |
| `lfs`/`stfs` | `f32` | Float |
| `lfd`/`stfd` | `f64` | Double |
| `lhz`/`sth` | `s16`/`u16` | 16-bit |
| `lbz`/`stb` | `s8`/`u8` | 8-bit |

## Common Item Helper Functions

| Function | Header | Purpose |
|----------|--------|---------|
| `it_80272C6C(gobj)` | `it/it_2725.h` | Check ground/air state |
| `it_80273130(gobj)` | `it/it_2725.h` | Common return/cleanup |
| `it_8026E9A4(...)` | `it/it_26B1.h` | Collision check |
| `Item_80268E5C(gobj, msid, flags)` | `item.h` | Change motion state |
| `Item_802694CC(gobj)` | `item.h` | Update animation |
| `GET_ITEM(gobj)` | `it/inlines.h` | Cast Item_GObj* → Item* |

## Reference Files to Study

| File | Teaches |
|------|---------|
| `itfoxlaser.c` | Simple laser, position tracking |
| `itgreatfoxlaser.c` | Similar to arwing laser |
| `itfoxblaster.c` | Complex state machine |
| `itcapsule.c` | Standard item pattern |
| `it_27CF.c` | Generic struct usage |

## Debugging Workflow

1. **70-90% match**: Type/struct issues
   - Verify correct union member
   - Check s16 vs s32
   - Compare assembly diffs

2. **90-99% match**: Scheduling/register issues
   - Study instruction order
   - Reduce temporaries
   - Try accessing in different order

3. **100% match but wrong behavior**: Logic error
   - Check conditionals
   - Verify bitfield sizes
   - Review branch conditions

## Full Example

```c
#include "itarwinglaser.h"
#include "it/inlines.h"
#include "it/it_2725.h"
#include "it/itCharItems.h"
#include "it/types.h"
#include <platform.h>
#include <baselib/gobj.h>
#include <melee/it/item.h>

s32 itArwinglaser_UnkMotion2_Anim(Item_GObj* arg0)
{
    Item* item;

    item = GET_ITEM(arg0);
    
    // Copy: xE18→xE24, xE1C→xE28, xE20→xE2C
    item->xDD4_itemVar.arwinglaser.xE24 = item->xDD4_itemVar.arwinglaser.xE18;
    item->xDD4_itemVar.arwinglaser.xE28 = item->xDD4_itemVar.arwinglaser.xE1C;
    item->xDD4_itemVar.arwinglaser.xE2C = item->xDD4_itemVar.arwinglaser.xE20;
    
    // Conditional flag (sth = 16-bit store)
    if (it_80272C6C(arg0) == 0) {
        item->xDD4_itemVar.arwinglaser.xE30 = 1;
    }
    
    return it_80273130(arg0);
}
```

## See Also
- `skill:melee-objdiff` - Check match and see compiler errors
- `skill:melee-scaffold` - Add declarations to new files
