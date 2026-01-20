#!/usr/bin/env python3
"""
Setup script to create a portable Mac .app bundle
Run this to create a standalone application.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

APP_NAME = "EPUB to PDF Converter"
BUNDLE_ID = "com.converter.epub-to-pdf"

def create_app_bundle():
    """Create a macOS .app bundle"""
    
    script_dir = Path(__file__).parent.absolute()
    dist_dir = script_dir / "dist"
    app_dir = dist_dir / f"{APP_NAME}.app"
    contents_dir = app_dir / "Contents"
    macos_dir = contents_dir / "MacOS"
    resources_dir = contents_dir / "Resources"
    
    # Clean previous build
    if app_dir.exists():
        shutil.rmtree(app_dir)
    
    # Create directory structure
    macos_dir.mkdir(parents=True)
    resources_dir.mkdir(parents=True)
    
    # Create Info.plist
    info_plist = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>{BUNDLE_ID}</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>{APP_NAME}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>CFBundleDocumentTypes</key>
    <array>
        <dict>
            <key>CFBundleTypeExtensions</key>
            <array>
                <string>epub</string>
            </array>
            <key>CFBundleTypeName</key>
            <string>EPUB Document</string>
            <key>CFBundleTypeRole</key>
            <string>Viewer</string>
            <key>LSHandlerRank</key>
            <string>Alternate</string>
        </dict>
    </array>
</dict>
</plist>'''
    
    (contents_dir / "Info.plist").write_text(info_plist)
    
    # Create launcher script
    launcher_script = '''#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
RESOURCES="$DIR/../Resources"

# Set library path for Homebrew libraries (needed for WeasyPrint)
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_LIBRARY_PATH"
export PATH="/opt/homebrew/bin:$PATH"

# Use the bundled venv if it exists, otherwise use system Python
if [ -d "$RESOURCES/venv" ]; then
    PYTHON="$RESOURCES/venv/bin/python"
else
    # Check for Homebrew Python 3 first
    if [ -x "/opt/homebrew/bin/python3" ]; then
        PYTHON=/opt/homebrew/bin/python3
    elif command -v python3 &> /dev/null; then
        PYTHON=python3
    elif command -v python &> /dev/null; then
        PYTHON=python
    else
        osascript -e 'display alert "Python Required" message "Python 3 is required to run this application. Please install Python from Homebrew (brew install python3)."'
        exit 1
    fi
    
    # Create venv if needed
    if ! $PYTHON -c "import ebooklib, weasyprint" 2>/dev/null; then
        osascript -e 'display notification "Setting up environment..." with title "EPUB to PDF Converter"'
        $PYTHON -m venv "$RESOURCES/venv"
        "$RESOURCES/venv/bin/pip" install --quiet ebooklib weasyprint beautifulsoup4 lxml Pillow
        PYTHON="$RESOURCES/venv/bin/python"
    fi
fi

cd "$RESOURCES"
exec $PYTHON app.py "$@"
'''
    
    launcher_path = macos_dir / "launcher"
    launcher_path.write_text(launcher_script)
    os.chmod(launcher_path, 0o755)
    
    # Copy Python files to Resources
    for py_file in ["app.py", "converter.py"]:
        src = script_dir / py_file
        if src.exists():
            shutil.copy(src, resources_dir / py_file)
    
    # Copy requirements
    req_file = script_dir / "requirements.txt"
    if req_file.exists():
        shutil.copy(req_file, resources_dir / "requirements.txt")
    
    # Copy venv if it exists
    venv_dir = script_dir / "venv"
    if venv_dir.exists():
        print("📦 Copying virtual environment...")
        shutil.copytree(venv_dir, resources_dir / "venv", symlinks=True)
    
    # Create a simple icon (you can replace this with a real icon)
    create_app_icon(resources_dir)
    
    print(f"✅ Created app bundle at: {app_dir}")
    print(f"\nTo run the app:")
    print(f"  open \"{app_dir}\"")
    print(f"\nOr double-click '{APP_NAME}.app' in Finder")
    
    return app_dir


def create_app_icon(resources_dir: Path):
    """Create a basic app icon"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Create icon at various sizes
        sizes = [16, 32, 64, 128, 256, 512, 1024]
        iconset_dir = resources_dir / "AppIcon.iconset"
        iconset_dir.mkdir(exist_ok=True)
        
        for size in sizes:
            img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Background - rounded rectangle effect with gradient
            padding = size // 8
            
            # Draw background gradient (dark blue to purple)
            for i in range(size):
                r = int(26 + (i / size) * 10)
                g = int(26 + (i / size) * 15)
                b = int(46 + (i / size) * 30)
                draw.line([(0, i), (size, i)], fill=(r, g, b, 255))
            
            # Draw book icon (simplified)
            book_size = int(size * 0.5)
            book_x = (size - book_size) // 2
            book_y = int((size - book_size) / 2.2)
            
            # Book shape
            draw.rounded_rectangle(
                [book_x, book_y, book_x + book_size, book_y + book_size],
                radius=size // 16,
                fill=(233, 69, 96, 255)  # Accent red
            )
            
            # Arrow pointing down (PDF output)
            arrow_size = int(size * 0.2)
            arrow_x = size // 2
            arrow_y = int(size * 0.72)
            draw.polygon([
                (arrow_x, arrow_y + arrow_size // 2),
                (arrow_x - arrow_size // 2, arrow_y - arrow_size // 2),
                (arrow_x + arrow_size // 2, arrow_y - arrow_size // 2)
            ], fill=(0, 217, 165, 255))  # Success green
            
            # Save icons
            img.save(iconset_dir / f"icon_{size}x{size}.png")
            if size <= 512:
                img_2x = img.resize((size * 2, size * 2), Image.LANCZOS)
                img_2x.save(iconset_dir / f"icon_{size}x{size}@2x.png")
        
        # Create .icns file using iconutil
        icns_path = resources_dir / "AppIcon.icns"
        result = subprocess.run(
            ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(icns_path)],
            capture_output=True
        )
        
        if result.returncode == 0:
            # Clean up iconset
            shutil.rmtree(iconset_dir)
            print("✅ Created app icon")
        else:
            print("⚠️  Could not create .icns file, using iconset instead")
            
    except ImportError:
        print("⚠️  Pillow not available for icon generation")
    except Exception as e:
        print(f"⚠️  Could not create icon: {e}")


if __name__ == "__main__":
    create_app_bundle()
