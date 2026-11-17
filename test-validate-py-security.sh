#!/usr/bin/env bash
# test-validate-py-security.sh — regression tests for validate.py's template
# security rules (spec.security.risky and spec.security.volumeOwnershipCheck).
#
# The rules are template-only, so they are exercised directly against parsed
# template specs. No image pull or network access is needed.
#
# Run: modules/test-validate-py-security.sh

set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
pass=0 fail=0

check() { # check <name> <expected> <actual>
  if [[ "$2" == "$3" ]]; then
    echo "ok   - $1"; pass=$((pass + 1))
  else
    echo "FAIL - $1"; echo "       expected: '$2'"; echo "       actual:   '$3'"; fail=$((fail + 1))
  fi
}

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# security_findings <yaml-file>: prints "LEVEL [rule] message" for every
# template-only security finding the three new rules produce for that spec.
security_findings() {
  python3 -c '
import sys
sys.path.insert(0, sys.argv[1])
import yaml
import validate

with open(sys.argv[2]) as fh:
    doc = yaml.safe_load(fh) or {}
spec = doc.get("spec") or {}
findings = []
findings += validate.rule_risky_key_known(spec)
findings += validate.rule_risky_reason_length(spec)
findings += validate.rule_ownership_check_needs_fsgroup(spec)
for f in findings:
    print(f"{f.level} [{f.rule}] {f.message}")
' "$HERE" "$1"
}

write_template() { # write_template <path> <security-block-yaml>
  cat > "$1" <<EOF
apiVersion: gameplane.local/v1alpha1
kind: GameTemplate
metadata:
  name: test-module
spec:
  displayName: Test Module
  game: test-game
  version: 1.0.0
  image: alpine:latest
  security:
$2
EOF
}

LONG_REASON=$(python3 -c 'print("x" * 201)')
OK_REASON=$(python3 -c 'print("x" * 200)')

# 1. Valid risky block with all four known keys raises no risky-key error
T="$TMPDIR/risky-known.yaml"
write_template "$T" "    fsGroup: 1000
    risky:
      runAsUser:
        reason: \"The image must start as root to drop privileges; forcing a user breaks its start.\"
      runAsGroup:
        reason: \"Group is fixed by the image.\"
      fsGroup:
        reason: \"Volume group is fixed by the image.\"
      volumeOwnershipCheck:
        reason: \"Ownership check is required by the image.\""
out=$(security_findings "$T")
has=$(echo "$out" | grep -c "risky-unknown-key" || true)
check "risky block with the four known keys passes" "0" "$has"

# 2. Unknown risky key reports ERROR [risky-unknown-key]
T="$TMPDIR/risky-unknown.yaml"
write_template "$T" "    risky:
      uid:
        reason: \"Not an overridable setting.\""
out=$(security_findings "$T")
has=$(echo "$out" | grep -c "ERROR \[risky-unknown-key\] spec.security.risky.uid is not one of" || true)
check "unknown risky key reports ERROR [risky-unknown-key]" "1" "$has"

# 3. Reason of exactly 200 characters is accepted
T="$TMPDIR/risky-reason-200.yaml"
write_template "$T" "    risky:
      runAsUser:
        reason: \"$OK_REASON\""
out=$(security_findings "$T")
has=$(echo "$out" | grep -c "risky-reason-too-long" || true)
check "risky reason of 200 characters passes" "0" "$has"

# 4. Reason of 201 characters reports ERROR [risky-reason-too-long]
T="$TMPDIR/risky-reason-201.yaml"
write_template "$T" "    risky:
      runAsUser:
        reason: \"$LONG_REASON\""
out=$(security_findings "$T")
has=$(echo "$out" | grep -c "ERROR \[risky-reason-too-long\] spec.security.risky.runAsUser.reason is 201 characters" || true)
check "risky reason over 200 characters reports ERROR [risky-reason-too-long]" "1" "$has"

# 5. volumeOwnershipCheck without fsGroup reports WARN [ownership-check-without-fsgroup]
T="$TMPDIR/ownership-no-fsgroup.yaml"
write_template "$T" "    volumeOwnershipCheck: EveryStart"
out=$(security_findings "$T")
has=$(echo "$out" | grep -c "WARN \[ownership-check-without-fsgroup\]" || true)
check "volumeOwnershipCheck without fsGroup reports WARN [ownership-check-without-fsgroup]" "1" "$has"
has_err=$(echo "$out" | grep -c "^ERROR" || true)
check "volumeOwnershipCheck without fsGroup is not an ERROR" "0" "$has_err"

# 6. volumeOwnershipCheck with fsGroup raises no warning
T="$TMPDIR/ownership-with-fsgroup.yaml"
write_template "$T" "    fsGroup: 1000
    volumeOwnershipCheck: OnlyWhenWrong"
out=$(security_findings "$T")
has=$(echo "$out" | grep -c "ownership-check-without-fsgroup" || true)
check "volumeOwnershipCheck with fsGroup raises no warning" "0" "$has"

# 7. No security block raises no findings
T="$TMPDIR/no-security.yaml"
cat > "$T" <<'EOF'
apiVersion: gameplane.local/v1alpha1
kind: GameTemplate
metadata:
  name: test-module
spec:
  displayName: Test Module
  game: test-game
  version: 1.0.0
  image: alpine:latest
EOF
out=$(security_findings "$T")
check "template without security block has no security findings" "" "$out"

echo ""
echo "Summary: $pass passed, $fail failed."
if [ "$fail" -gt 0 ]; then
  exit 1
fi
exit 0
