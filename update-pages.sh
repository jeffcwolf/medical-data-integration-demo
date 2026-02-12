#!/bin/bash
# Update both GitHub and Codeberg Pages

# Make sure we're on main and everything is committed
echo "🔍 Checking for uncommitted changes..."
if [[ -n $(git status -s) ]]; then
    echo "⚠️  You have uncommitted changes. Commit them first:"
    git status -s
    exit 1
fi

git checkout main

echo "📊 Updating GitHub Pages..."
git checkout gh-pages
git checkout main -- dashboard/index.html
cp dashboard/index.html index.html
git add index.html
git commit -m "docs: Update dashboard"
git push origin gh-pages

echo "📊 Updating Codeberg Pages..."
git checkout pages
git checkout main -- dashboard/index.html
cp dashboard/index.html index.html
git add index.html
git commit -m "docs: Update dashboard"
git push codeberg pages

echo "✅ Switching back to main..."
git checkout main

echo "🎉 Done! Pages updated."
echo ""
echo "Wait 2-3 minutes for GitHub Pages: https://jeffcwolf.github.io/medical-data-integration-demo/"
echo "Wait 10-15 minutes for Codeberg Pages: https://research_coder.codeberg.page/medical-data-integration-demo/"
