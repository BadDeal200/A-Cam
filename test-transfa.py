#!/usr/bin/env python3
"""
Test transfa upload - Debug version to see what's available
"""

import sys

print("☁️ Testing transfa installation...")
print(f"🐍 Python version: {sys.version}")
print("")

try:
    import transfa
    print("✅ transfa imported successfully")
    print(f"📋 Available attributes: {dir(transfa)}")
    print("")
    
    # Check for upload functions
    if hasattr(transfa, 'upload'):
        print("✅ transfa.upload() exists")
    else:
        print("❌ transfa.upload() does NOT exist")
    
    if hasattr(transfa, 'upload_file'):
        print("✅ transfa.upload_file() exists")
    else:
        print("❌ transfa.upload_file() does NOT exist")
    
    if hasattr(transfa, 'send'):
        print("✅ transfa.send() exists")
    else:
        print("❌ transfa.send() does NOT exist")
        
    print("")
    print("📋 All functions:")
    for attr in dir(transfa):
        if not attr.startswith('_'):
            print(f"   - {attr}")
            
except ImportError as e:
    print(f"❌ transfa import error: {e}")
    print("")
    print("📥 To install transfa:")
    print("   pip install transfa")
    print("   Or: pip install transfa-client")
    print("   Or: pip install requests (for fallback method)")
    
except Exception as e:
    print(f"❌ Error: {e}")