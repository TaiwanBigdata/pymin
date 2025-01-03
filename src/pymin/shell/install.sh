#!/usr/bin/env bash

# PyMin shell integration installer

PYMIN_HOME="$HOME/.pymin"
SHELL_TYPE="$(basename "$SHELL")"

# Find appropriate RC file
find_rc_file() {
    local shell_type="$1"
    
    # First check if .zshrc exists, regardless of current shell
    if [ -f "$HOME/.zshrc" ]; then
        echo "$HOME/.zshrc"
        return 0
    fi
    
    # Then check shell-specific files
    local rc_files=(
        "$HOME/.${shell_type}rc"
        "$HOME/.${shell_type}_profile"
        "$HOME/.profile"
    )
    
    # For bash, also check bash_profile
    if [ "$shell_type" = "bash" ]; then
        rc_files+=("$HOME/.bash_profile")
    fi
    
    # Return the first existing file
    for file in "${rc_files[@]}"; do
        if [ -f "$file" ]; then
            echo "$file"
            return 0
        fi
    done
    
    # If .zshrc doesn't exist but zsh is available, create and use .zshrc
    if command -v zsh >/dev/null 2>&1; then
        touch "$HOME/.zshrc"
        echo "$HOME/.zshrc"
        return 0
    fi
    
    # Default to current shell's rc
    echo "$HOME/.${shell_type}rc"
}

# Determine shell configuration file
case "$SHELL_TYPE" in
    "bash"|"zsh")
        RC_FILE=$(find_rc_file "$SHELL_TYPE")
        ;;
    *)
        echo "Unsupported shell: $SHELL_TYPE"
        echo "Currently only bash and zsh are supported"
        exit 1
        ;;
esac

# Check if already configured
if grep -q "PyMin Configuration" "$RC_FILE"; then
    echo "PyMin shell integration already installed in: $RC_FILE"
    exit 0
fi

# Get functions.sh path
FUNCTIONS_SH="$(dirname "$0")/functions.sh"
if [ ! -f "$FUNCTIONS_SH" ]; then
    echo "Error: Required file not found: $FUNCTIONS_SH"
    exit 1
fi

# Create PyMin directories
mkdir -p "$PYMIN_HOME/bin"
mkdir -p "$PYMIN_HOME/env"

# Create marker file for pip uninstall hook
echo "$RC_FILE" > "$PYMIN_HOME/.config"

# Install shell functions
cp "$FUNCTIONS_SH" "$PYMIN_HOME/env/"

# Create shell wrapper
cat > "$PYMIN_HOME/bin/pm" << 'EOF'
#!/usr/bin/env bash

# Source PyMin functions
source "$HOME/.pymin/env/functions.sh"

# Execute command
case "$1" in
    "activate")
        shift
        _pm_activate "$@"
        ;;
    "deactivate")
        _pm_deactivate
        ;;
    *)
        # For other commands, pass to Python CLI
        command pm "$@"
        ;;
esac
EOF

# Make wrapper executable
chmod +x "$PYMIN_HOME/bin/pm"

# Add to PATH and source functions
PYMIN_CONFIG="
# PyMin Configuration
export PATH=\"\$HOME/.pymin/bin:\$PATH\"
source \"\$HOME/.pymin/env/functions.sh\"
"

# Install configuration
echo "$PYMIN_CONFIG" >> "$RC_FILE"
echo "PyMin shell integration installed successfully in: $RC_FILE"
echo "Please restart your shell or run:"
echo "  source $RC_FILE" 