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

for ruleset in main develop release-hotfix; do
    file="${SCRIPT_DIR}/${ruleset}.json"
    name="$(jq -r .name "${file}")"
    echo "Applying ruleset: ${name} (from ${ruleset}.json)"
    gh api -X POST "repos/${REPO}/rulesets" \
        -H "Accept: application/vnd.github+json" \
        --input "${file}" \
        > /dev/null
    echo "  -> created"
done

echo
echo "Confirm in the GitHub UI:"
echo "  https://github.com/${REPO}/settings/rules"
echo
echo "Manual follow-up: add 'github-actions[bot]' as a bypass actor on"
echo "the 'main protection' ruleset so release.yml's fast-forward-main"
echo "step can push to main without manual review."
echo "  Settings -> Rules -> 'main protection' -> Bypass list -> Add"
echo "  bypass -> github-actions[bot] -> Always"
