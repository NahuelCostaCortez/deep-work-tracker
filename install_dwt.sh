#!/bin/bash

set -e

# Create ~/.local/bin if it doesn't exist
echo "Creating ~/.local/bin directory if needed..."
mkdir -p "$HOME/.local/bin"

# Symlink dwt to ~/.local/bin/dwt
echo "Linking dwt to ~/.local/bin/dwt..."
ln -sf "$PWD/dwt" "$HOME/.local/bin/dwt"

# Make dwt executable
echo "Making dwt executable..."
chmod +x "$PWD/dwt"

# Add ~/.local/bin to PATH if not present
PROFILE=""
if [ -n "$ZSH_VERSION" ]; then
  PROFILE="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
  PROFILE="$HOME/.bash_profile"
else
  PROFILE="$HOME/.profile"
fi

if ! grep -q 'export PATH="$HOME/.local/bin:$PATH"' "$PROFILE" 2>/dev/null; then
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$PROFILE"
  echo "Added ~/.local/bin to your PATH in $PROFILE. Please restart your terminal or run:"
  echo "  source $PROFILE"
else
  echo "~/.local/bin is already in your PATH in $PROFILE."
fi

echo "Installation complete! You can now run 'dwt' from any directory." 