#!/bin/bash
set -e  # Exit on error

echo "========================================"
echo "TrailCam Animal ID - macOS Build Script"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="TrailCam Animal ID"
VERSION="1.0.0"
PYTHON_VERSION="3.14.2"

# Check Python version
echo "${YELLOW}[1/9] Checking Python version...${NC}"
python3 --version | grep -q "Python 3" || {
    echo "${RED}Error: Python 3.9+ required${NC}"
    exit 1
}
echo "${GREEN}✓ Python OK${NC}"
echo ""

# Clean previous builds
echo "${YELLOW}[2/9] Cleaning previous builds...${NC}"
rm -rf build dist *.egg-info
rm -f assets/icon.icns
echo "${GREEN}✓ Clean complete${NC}"
echo ""

# Create application icon
echo "${YELLOW}[3/9] Creating application icon...${NC}"
mkdir -p assets/icon.iconset

# Generate icon sizes using sips (built-in macOS tool)
sips -z 16 16     assets/logo.png --out assets/icon.iconset/icon_16x16.png > /dev/null 2>&1
sips -z 32 32     assets/logo.png --out assets/icon.iconset/icon_16x16@2x.png > /dev/null 2>&1
sips -z 32 32     assets/logo.png --out assets/icon.iconset/icon_32x32.png > /dev/null 2>&1
sips -z 64 64     assets/logo.png --out assets/icon.iconset/icon_32x32@2x.png > /dev/null 2>&1
sips -z 128 128   assets/logo.png --out assets/icon.iconset/icon_128x128.png > /dev/null 2>&1
sips -z 256 256   assets/logo.png --out assets/icon.iconset/icon_128x128@2x.png > /dev/null 2>&1
sips -z 256 256   assets/logo.png --out assets/icon.iconset/icon_256x256.png > /dev/null 2>&1
sips -z 512 512   assets/logo.png --out assets/icon.iconset/icon_256x256@2x.png > /dev/null 2>&1
sips -z 512 512   assets/logo.png --out assets/icon.iconset/icon_512x512.png > /dev/null 2>&1
sips -z 1024 1024 assets/logo.png --out assets/icon.iconset/icon_512x512@2x.png > /dev/null 2>&1

# Convert to .icns
iconutil -c icns assets/icon.iconset -o assets/icon.icns
rm -rf assets/icon.iconset
echo "${GREEN}✓ Icon created: assets/icon.icns${NC}"
echo ""

# Install build dependencies
echo "${YELLOW}[4/9] Installing build dependencies...${NC}"
pip install --upgrade pyinstaller > /dev/null 2>&1
echo "${GREEN}✓ Build tools ready${NC}"
echo ""

# Build using unified spec (includes both GUI and backend)
echo "${YELLOW}[5/9] Building unified macOS application...${NC}"
pyinstaller --clean --noconfirm unified.spec

echo "${GREEN}✓ App bundle created: dist/${APP_NAME}.app${NC}"
echo "${GREEN}✓ Backend included: dist/${APP_NAME}.app/Contents/MacOS/trailcam_backend${NC}"
echo ""

# Sign the entire application bundle for macOS Gatekeeper
echo "${YELLOW}[6/9] Signing application bundle...${NC}"
APP_BUNDLE_PATH="dist/${APP_NAME}.app"
SIGNING_IDENTITY="-" # Ad-hoc signature, no developer account needed

# Use --deep to recursively sign the entire bundle. This is the most effective
# way to resolve "Team ID" mismatches with bundled frameworks like Python.
codesign --force --deep --sign "${SIGNING_IDENTITY}" "${APP_BUNDLE_PATH}"

echo "${GREEN}✓ Application bundle signed${NC}"
echo ""

# Create DMG installer
echo "${YELLOW}[7/9] Creating DMG installer...${NC}"
DMG_NAME="TrailCam_Animal_ID_v${VERSION}.dmg"
DMG_TMP="dist/tmp.dmg"

# Create temporary DMG
hdiutil create -volname "${APP_NAME}" -srcfolder "dist/${APP_NAME}.app" -ov -format UDZO "${DMG_TMP}" > /dev/null 2>&1

# Convert to final DMG (compressed)
hdiutil convert "${DMG_TMP}" -format UDZO -o "dist/${DMG_NAME}" > /dev/null 2>&1
rm -f "${DMG_TMP}"

echo "${GREEN}✓ DMG created: dist/${DMG_NAME}${NC}"
echo ""

# Create ZIP archive
echo "${YELLOW}[8/9] Creating ZIP archive...${NC}"
ZIP_NAME="TrailCam_Animal_ID_v${VERSION}.zip"
cd dist
zip -r -q "${ZIP_NAME}" "${APP_NAME}.app"
cd ..

echo "${GREEN}✓ ZIP created: dist/${ZIP_NAME}${NC}"
echo ""

# Summary
echo "${YELLOW}[9/9] Build complete!${NC}"
echo ""
echo "========================================"
echo "Build Summary"
echo "========================================"
echo "App Bundle:  dist/${APP_NAME}.app"
echo "DMG File:    dist/${DMG_NAME} ($(du -h "dist/${DMG_NAME}" | cut -f1))"
echo "ZIP File:    dist/${ZIP_NAME} ($(du -h "dist/${ZIP_NAME}" | cut -f1))"
echo ""
echo "${GREEN}Installation Instructions (DMG):${NC}"
echo "1. Open dist/${DMG_NAME}"
echo "2. Drag '${APP_NAME}' to Applications folder"
echo "3. Launch from Applications or Spotlight"
echo ""
echo "${GREEN}Installation Instructions (ZIP):${NC}"
echo "1. Unzip dist/${ZIP_NAME}"
echo "2. Drag '${APP_NAME}.app' to Applications folder"
echo "3. Launch from Applications or Spotlight"
echo ""
echo "${YELLOW}Note: First launch may require:${NC}"
echo "  Right-click → Open (to bypass Gatekeeper)"
echo "========================================"
