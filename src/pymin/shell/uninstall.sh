#!/usr/bin/env bash

# PyMin shell integration uninstaller

PYMIN_HOME="$HOME/.pymin"
CONFIG_FILE="$PYMIN_HOME/.config"

# Function to clean up RC file
clean_rc_file() {
    local rc_file="$1"
    local tmp_file
    
    # Create a temporary file
    tmp_file=$(mktemp)
    
    # Remove PyMin configuration block
    sed '/# PyMin Configuration/,+2d' "$rc_file" > "$tmp_file"
    
    # Replace content while preserving permissions
    cat "$tmp_file" > "$rc_file"
    rm "$tmp_file"
}

# Get RC file from saved config
if [ -f "$CONFIG_FILE" ]; then
    RC_FILE=$(cat "$CONFIG_FILE")
    if [ ! -f "$RC_FILE" ]; then
        echo "Warning: Config file points to non-existent RC file: $RC_FILE"
        echo "Will try to detect RC file..."
    fi
else
    echo "Warning: Config file not found: $CONFIG_FILE"
    echo "Will try to detect RC file..."
fi

# If RC file not found or invalid, try to detect it
if [ ! -f "$RC_FILE" ]; then
    # First check .zshrc
    if [ -f "$HOME/.zshrc" ]; then
        RC_FILE="$HOME/.zshrc"
    else
        # Fallback to current shell
        SHELL_TYPE="$(basename "$SHELL")"
        case "$SHELL_TYPE" in
            "bash")
                RC_FILE="$HOME/.bashrc"
                ;;
            "zsh")
                RC_FILE="$HOME/.zshrc"
                ;;
            *)
                echo "Error: Unsupported shell: $SHELL_TYPE"
                echo "Currently only bash and zsh are supported"
                exit 1
                ;;
        esac
    fi
fi

# Check if PyMin configuration exists in RC file
if [ ! -f "$RC_FILE" ]; then
    echo "Warning: RC file not found: $RC_FILE"
else
    if grep -q "PyMin Configuration" "$RC_FILE"; then
        # Check if file is a symlink
        if [ -L "$RC_FILE" ]; then
            # Get the target file
            TARGET_FILE=$(readlink "$RC_FILE")
            clean_rc_file "$TARGET_FILE"
            echo "Removed PyMin configuration from: $TARGET_FILE (via symlink $RC_FILE)"
        else
            clean_rc_file "$RC_FILE"
            echo "Removed PyMin configuration from: $RC_FILE"
        fi
    else
        echo "No PyMin configuration found in: $RC_FILE"
    fi
fi

# Remove PyMin directory if it exists
if [ -d "$PYMIN_HOME" ]; then
    rm -rf "$PYMIN_HOME"
    echo "Removed PyMin directory: $PYMIN_HOME"
else
    echo "PyMin directory not found: $PYMIN_HOME"
fi

echo "PyMin shell integration uninstalled successfully!"
echo "Please restart your shell or run:"
echo "  source $RC_FILE" 