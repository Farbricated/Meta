#!/usr/bin/env bash
# =============================================================================
# apply_fixes.sh — Meta v3.2 fix script
# Run from the REPO ROOT:  bash apply_fixes.sh
#
# What this does:
#   1. Deletes all .bak files and dev artifacts
#   2. Patches server/Meta_environment.py (tk2 title + reward clamp)
#   3. Replaces expert_tasks.py with widened revenue tolerance
#   4. Replaces tests/test_environment.py with full 24-task coverage
#   5. Replaces README.md with novelty comparison table
# =============================================================================

set -e
REPO="$(pwd)"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  Meta v3.2 — Applying all fixes             ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── STEP 1: Remove dev artifacts and .bak files ─────────────────────────────
echo "▶ Step 1: Removing dev artifacts..."

FILES_TO_DELETE=(
  "apply_patches.py"
  "patch_notes.py"
  "baseline.py.bak"
  "inference.py.bak"
  "openenv.yaml.bak"
  "server/Meta_environment.py.bak"
  "server/app.py.bak"
  "server/gradio_ui.py.bak"
)

for f in "${FILES_TO_DELETE[@]}"; do
  if [ -f "$REPO/$f" ]; then
    rm "$REPO/$f"
    echo "  ✓ deleted $f"
  else
    echo "  ⟳ $f not found (already clean)"
  fi
done

echo ""
echo "▶ Step 2: Patching server/Meta_environment.py..."

ENV_FILE="$REPO/server/Meta_environment.py"

# Fix 2a: Clarify tk2 ticket description so it's unambiguously a frontend bug
python3 - <<'PYEOF'
import sys
path = "server/Meta_environment.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

old = '{"id": "tk2", "title": "Wrong currency symbol shown for EU customers",      "type": "bug",            "team": "frontend", "priority_rank": 3},'
new = '{"id": "tk2", "title": "EU checkout renders \'$\' instead of \'€\' — frontend display-layer bug", "type": "bug", "team": "frontend", "priority_rank": 3},'

if old in src:
    src = src.replace(old, new, 1)
    print("  ✓ Fixed tk2 ticket description")
else:
    print("  ⚠  tk2 old string not found — may already be patched or text differs")

# Fix 2b: Clamp _compute_reward output to [0.0, 1.0]
old_reward = "        return round(base, 3)"
new_reward = "        # Clamp to [0.0, 1.0] — reward shaping must never breach this\n        return round(max(0.0, min(1.0, base)), 3)"

if old_reward in src:
    # Only replace inside _compute_reward, not anywhere else
    idx = src.find("def _compute_reward")
    end_idx = src.find("def step", idx)
    method_src = src[idx:end_idx]
    if old_reward in method_src:
        method_src = method_src.replace(old_reward, new_reward, 1)
        src = src[:idx] + method_src + src[end_idx:]
        print("  ✓ Fixed _compute_reward clamping")
    else:
        print("  ⚠  reward clamp pattern not found in _compute_reward body")
else:
    print("  ⚠  reward clamp: 'return round(base, 3)' not found — may already be patched")

# Fix 2c: Update the ticket_triage_medium instruction to match new tk2 title
old_instr = "  'Wrong currency symbol shown' → frontend (it's a display/rendering bug)\n"
new_instr = "  'EU checkout renders $ instead of € — frontend display-layer bug' → frontend\n"
if old_instr in src:
    src = src.replace(old_instr, new_instr, 1)
    print("  ✓ Fixed ticket_triage_medium instruction for tk2")
else:
    print("  ⚠  tk2 instruction old string not found — may already be patched")

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
PYEOF

echo ""
echo "▶ Step 3: Replacing expert_tasks.py..."
cp "$(dirname "$0")/expert_tasks.py" "$REPO/expert_tasks.py"
echo "  ✓ expert_tasks.py replaced (widened revenue tolerance, p3 keywords expanded)"

echo ""
echo "▶ Step 4: Replacing tests/test_environment.py..."
cp "$(dirname "$0")/tests/test_environment.py" "$REPO/tests/test_environment.py"
echo "  ✓ tests/test_environment.py replaced (80+ tests, all 24 tasks, reward clamping)"

echo ""
echo "▶ Step 5: Replacing README.md..."
cp "$(dirname "$0")/README.md" "$REPO/README.md"
echo "  ✓ README.md replaced (novelty table, frontier scores, comparison table)"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  All fixes applied. Run verification:       ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  pytest tests/ -v                           ║"
echo "║  python inference.py                        ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
