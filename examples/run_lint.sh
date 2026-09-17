#!/usr/bin/env bash
# Run `skillmd-lint --strict --schema` against every skill in this gallery
# and exit non-zero on any finding. Designed to be called from CI.
#
# Usage:
#   ./run_lint.sh                       # lint examples/ relative to repo root
#   ./run_lint.sh /path/to/skillmd-lint # lint against a specific checkout
#
# Requirements:
#   - skillmd-lint installed (`pip install -e .` from the repo root, or
#     `pip install skillmd-lint` for a published release).
#   - python3 on PATH (the project requires Python >= 3.10).
#   - bash >= 4 (uses `nullglob`).
#
# Exit codes:
#   0 — every skill passed with zero findings
#   1 — at least one skill produced a finding (linter output is printed)
#   2 — setup error (skillmd-lint not installed, no skills found, etc.)

set -euo pipefail

# Resolve repo root: this script lives in examples/, so its parent is the repo.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Allow the caller to override the examples directory (CI / staging).
EXAMPLES_DIR="${1:-${SCRIPT_DIR}}"

shopt -s nullglob

# Discover skill directories (immediate children with a SKILL.md).
skills=("${EXAMPLES_DIR}"/*/SKILL.md)
if [[ ${#skills[@]} -eq 0 ]]; then
    echo "error: no SKILL.md files found under ${EXAMPLES_DIR}/" >&2
    exit 2
fi

# Pick the linter entry point. Prefer the CLI script (skillmd-lint on PATH),
# fall back to `python3 -m skillmd_lint`.
if command -v skillmd-lint >/dev/null 2>&1; then
    LINT=(skillmd-lint)
else
    LINT=(python3 -m skillmd_lint)
fi

# Confirm the linter is actually importable before we start.
if ! "${LINT[@]}" --version >/dev/null 2>&1; then
    echo "error: ${LINT[*]} --version failed; is skillmd-lint installed?" >&2
    echo "       try: pip install -e ${REPO_ROOT}" >&2
    exit 2
fi

total=0
passed=0
failed=0

for skill in "${skills[@]}"; do
    skill_dir="$(dirname "$skill")"
    skill_name="$(basename "$skill_dir")"
    total=$((total + 1))

    # Capture output; print it if the linter returned non-zero.
    if output="$("${LINT[@]}" --strict --schema "$skill_dir" 2>&1)"; then
        echo "passed: ${skill_name}"
        passed=$((passed + 1))
    else
        echo "FAILED : ${skill_name}"
        echo "${output}"
        echo "------"
        failed=$((failed + 1))
    fi
done

echo
echo "summary: ${passed}/${total} passed, ${failed} failed"

if [[ ${failed} -gt 0 ]]; then
    exit 1
fi

exit 0