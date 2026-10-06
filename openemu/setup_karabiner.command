#!/bin/zsh
# One-time setup: installs Karabiner's virtual keyboard driver and builds the
# bridge the bot uses to press keys in OpenEmu. Needs Xcode and Homebrew.
set -e
cd "$(dirname "$0")"
HERE="$PWD"
SRC="$HERE/karabiner_bridge/Karabiner-DriverKit-VirtualHIDDevice"

echo "1/4 Downloading Karabiner-DriverKit-VirtualHIDDevice..."
rm -rf "$SRC"
git clone --depth 1 https://github.com/pqrs-org/Karabiner-DriverKit-VirtualHIDDevice.git "$SRC"

echo "2/4 Installing the driver (asks for your Mac password)..."
PKG=$(ls "$SRC"/dist/Karabiner-DriverKit-VirtualHIDDevice-*.pkg | sort -V | tail -1)
sudo installer -pkg "$PKG" -target /
/Applications/.Karabiner-VirtualHIDDevice-Manager.app/Contents/MacOS/Karabiner-VirtualHIDDevice-Manager activate
echo "   If macOS shows 'System Extension Blocked', open System Settings > Privacy & Security,"
echo "   click Allow, and restart if asked. Then run this file again."

echo "3/4 Building the key bridge..."
command -v xcodegen >/dev/null || brew install xcodegen
EX="$SRC/examples/virtual-hid-device-service-client"
cp "$HERE/karabiner_bridge/kbd_bridge.cpp" "$EX/src/main.cpp"
sed -i '' '/-Werror/d' "$EX/project.yml"
(cd "$EX" && make)
cp "$EX/build/Release/virtual-hid-device-service-client" "$HERE/karabiner_bridge/kbd_bridge"

echo "4/4 Done. Now double-click UniversalDudley.command and choose OpenEmu."
read "?Press Enter to close."
