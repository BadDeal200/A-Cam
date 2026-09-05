#!/bin/bash
# view-links.sh - View all cloud links

echo "☁️ tempfile.org Links - All Uploaded Files"
echo "=========================================="
echo ""

if [ -f "cloud_links.txt" ]; then
    cat cloud_links.txt
else
    echo "📭 No cloud links yet. Run the server and receive files first."
fi

echo ""
echo "📋 To check cloud links while server is running:"
echo "   curl http://localhost:5000/cloud-links"