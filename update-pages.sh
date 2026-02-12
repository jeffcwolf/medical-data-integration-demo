#!/bin/bash
# Update both GitHub and Codeberg Pages

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