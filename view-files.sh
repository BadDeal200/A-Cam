#!/bin/bash
# view-files.sh - View received files

echo "📂 Received Files:"
echo "=================="

if [ -d "gift_videos" ]; then
    cd gift_videos
    ls -la --time-style=long-iso | grep -v "^total" | while read line; do
        echo "   $line"
    done
    echo ""
    echo "📁 Total files: $(ls -1 | wc -l)"
    echo ""
    echo "📂 Full path: $(pwd)"
else
    echo "❌ No files received yet. Directory doesn't exist."
fi
