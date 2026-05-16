#!/bin/bash
# LOQ Control Setup Script
# This script sets up the terminal shortcut and ensures the wrapper is executable.

PROJECT_DIR=$(pwd)
WRAPPER="$PROJECT_DIR/loq-control-wrapper.sh"

echo "🛸 LOQ Control Center: Setting up terminal shortcut..."

# Make wrapper executable
chmod +x "$WRAPPER"

# Try to create symlink
echo "Requesting sudo permissions to create symlink in /usr/local/bin..."
sudo ln -sf "$WRAPPER" /usr/local/bin/loq-control

if [ $? -eq 0 ]; then
    echo "✅ Success! You can now run the app by simply typing 'loq-control' in your terminal."
else
    echo "❌ Failed to create symlink. You can manually create it by running:"
    echo "sudo ln -sf $WRAPPER /usr/local/bin/loq-control"
fi
