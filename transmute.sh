#!/usr/bin/env bash
# transmute.sh — Prepare a target .o and run Transmuter for a given function
#
# Usage:
#   ./transmute.sh <function_name> [extra transmuter flags...]
#
# Examples:
#   ./transmute.sh ftCo_800BF458
#   ./transmute.sh it_2725_Logic107_Reflected
#   ./transmute.sh Stage_Init --max-iterations 5000

set -euo pipefail

TRANSMUTER="node tools/transmuter/packages/cli/dist/index.js"
ASSEMBLER="build/binutils/powerpc-eabi-as"
PRELUDE="nonmatchings/prelude_ppc.inc"
TARGET_DIR="build/transmuter"

# ── Argument parsing ──────────────────────────────────────────────

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <function_name> [extra transmuter flags...]"
  echo ""
  echo "Examples:"
  echo "  $0 ftCo_800BF458"
  echo "  $0 it_2725_Logic107_Reflected"
  exit 1
fi

FUNC_NAME="$1"
shift
EXTRA_FLAGS=("$@")

# ── Validate inputs ──────────────────────────────────────────────

if [[ ! -f "$ASSEMBLER" ]]; then
  echo "Error: Assembler not found: $ASSEMBLER"
  echo "Have you built the project toolchain?"
  exit 1
fi

# ── Find the asm file containing the function ────────────────────

echo "── Searching for '$FUNC_NAME' in asm files..."

ASM_FILE=$(grep -rl "$FUNC_NAME" build/GALE01/asm/ --include='*.s' | head -1)

if [[ -z "$ASM_FILE" ]]; then
  echo "Error: No .s file contains '$FUNC_NAME' under build/GALE01/asm/"
  exit 1
fi

echo "  Found in: $ASM_FILE"

# ── Derive source file from asm path ────────────────────────────

# build/GALE01/asm/melee/ft/ftcommon.c/ftCo_800BF458.s
#                 → src/melee/ft/ftcommon.c
REL_PATH="${ASM_FILE#build/GALE01/asm/}"   # melee/it/items/itpikachutjoltair.s
DIR_PATH="${REL_PATH%/*}"                  # melee/it/items
FILE_NAME="$(basename "$ASM_FILE" .s)"     # itpikachutjoltair

SRC_FILE="src/${DIR_PATH}/${FILE_NAME}.c"

if [[ ! -f "$SRC_FILE" ]]; then
  echo "Error: Derived source file not found: $SRC_FILE"
  echo "  (derived from $ASM_FILE)"
  exit 1
fi

echo "  Source:   $SRC_FILE"

# ── Build the target .o ──────────────────────────────────────────

mkdir -p "$TARGET_DIR"

TARGET_ASM="$TARGET_DIR/${FUNC_NAME}.s"
TARGET_OBJ="$TARGET_DIR/${FUNC_NAME}.o"

echo ""
echo "── Preparing target object ─────────────────────────────"
echo "  Function:  $FUNC_NAME"
echo "  Source:    $SRC_FILE"
echo "  ASM:       $ASM_FILE"
echo "  Target .o: $TARGET_OBJ"
echo ""

cat > "$TARGET_ASM" <<EOF
.include "${PRELUDE}"
.syntax unified
.text
.include "${ASM_FILE}"
EOF

"$ASSEMBLER" -I build/GALE01/include  -mgekko "$TARGET_ASM" -o "$TARGET_OBJ"

echo "  ✓ Assembled target object"
echo ""

# ── Run Transmuter ────────────────────────────────────────────────

echo "── Running Transmuter ──────────────────────────────────"
echo "  $TRANSMUTER match $SRC_FILE --target $TARGET_OBJ --function $FUNC_NAME ${EXTRA_FLAGS[*]:-}"
echo ""

exec $TRANSMUTER match \
  "$SRC_FILE" \
  --target "$TARGET_OBJ" \
  --function "$FUNC_NAME" \
  "${EXTRA_FLAGS[@]}"
