#!/bin/bash
# view-links.sh - View all transfa links

echo "☁️ transfa Links - All Uploaded Files"
echo "======================================"
echo ""

if [ -f "transfa_links.txt" ]; then
    cat transfa_links.txt
else
    echo "📭 No transfa links yet. Run the server and receive files first."
fi

echo ""
echo "📋 To check transfa links while server is running:"
echo "   curl http://localhost:5000/transfa-links"