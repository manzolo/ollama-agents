#!/bin/bash
# Update frontend version using git commit hash for cache busting
# Usage: ./update-version.sh
#   Automatically uses current git commit short hash

set -e

cd "$(dirname "$0")"
HTML_FILE="frontend/index.html"

if [ ! -f "$HTML_FILE" ]; then
    echo "Error: $HTML_FILE not found"
    exit 1
fi

# Get git short hash (7 characters)
if ! command -v git &> /dev/null; then
    echo "Error: git command not found"
    exit 1
fi

VERSION=$(git rev-parse --short=7 HEAD 2>/dev/null || echo "dev")

echo "Updating version to: $VERSION (git hash)"

# Update version in HTML file (more specific patterns)
# 1. Update app-version meta tag
sed -i.bak 's/<meta name="app-version" content="[^"]*">/<meta name="app-version" content="'"$VERSION"'">/' "$HTML_FILE"

# 2. Update CSS version
sed -i.bak 's/styles\.css?v=[^"]*"/styles.css?v='"$VERSION"'"/' "$HTML_FILE"

# 3. Update JS version
sed -i.bak 's/app\.js?v=[^"]*"/app.js?v='"$VERSION"'"/' "$HTML_FILE"

# Remove backup file
rm -f "${HTML_FILE}.bak"

echo "✓ Version updated to $VERSION in $HTML_FILE"
echo ""
echo "Changes applied:"
echo "  - Meta tag: <meta name=\"app-version\" content=\"$VERSION\">"
echo "  - CSS: styles.css?v=$VERSION"
echo "  - JS: app.js?v=$VERSION"
echo ""
echo "💡 Tip: Run 'make update-version' or add to pre-commit hook"
