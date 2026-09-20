#!/usr/bin/env bash
# Apply mcp-kraken's GitFlow rulesets to the GitHub repository.
#
# Requires the gh CLI authenticated against the repo with admin scope.
#
# Usage:
#   ./docs/contributing/rulesets/apply.sh              # XavierBeheydt/mcp-kraken
#   ./docs/contributing/rulesets/apply.sh owner/repo   # other repo

set -euo pipefail

REPO="${1:-XavierBeheydt/mcp-kraken}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Idempotent: a ruleset that already exists under the same name is updated
# in place, so re-running the script never leaves duplicates behind.
existing="$(gh api "repos/${REPO}/rulesets" --paginate)"

for ruleset in main dev release-hotfix tags; do
    file="${SCRIPT_DIR}/${ruleset}.json"
    name="$(jq -r .name "${file}")"
    id="$(jq -r --arg name "${name}" \
        'map(select(.name == $name)) | first | .id // empty' <<< "${existing}")"
    echo "Applying ruleset: ${name} (from ${ruleset}.json)"
    if [[ -n "${id}" ]]; then
        gh api -X PUT "repos/${REPO}/rulesets/${id}" \
            -H "Accept: application/vnd.github+json" \
            --input "${file}" \
            > /dev/null
        echo "  -> updated (id ${id})"
    else
        gh api -X POST "repos/${REPO}/rulesets" \
            -H "Accept: application/vnd.github+json" \
            --input "${file}" \
            > /dev/null
        echo "  -> created"
    fi
done

echo
echo "Confirm in the GitHub UI:"
echo "  https://github.com/${REPO}/settings/rules"
echo
echo "No bypass actor is needed: no workflow pushes to main. It advances"
echo "only through a reviewed pull request, and release.yml refuses a"
echo "final vX.Y.Z tag that is not contained in main."
