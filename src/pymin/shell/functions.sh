#!/usr/bin/env bash

# PyMin virtual environment management functions

function _pm_activate() {
    local venv_path="${1:-env}"  # Default to 'env' if no path provided
    
    # Ensure the virtual environment exists
    if [ ! -d "$venv_path" ]; then
        echo "Virtual environment not found at: $venv_path"
        echo "Create it first with: pm venv"
        return 1
    fi
    
    # Check if already in a virtual environment
    if [ -n "$VIRTUAL_ENV" ]; then
        local current_venv="$(basename "$VIRTUAL_ENV")"
        echo "Currently in virtual environment: $current_venv"
        read -p "Switch to $venv_path? [Y/n] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            deactivate
            source "$venv_path/bin/activate"
            echo "Switched to: $venv_path"
        fi
    else
        source "$venv_path/bin/activate"
        echo "Activated: $venv_path"
    fi
}

function _pm_deactivate() {
    if [ -n "$VIRTUAL_ENV" ]; then
        local current_venv="$(basename "$VIRTUAL_ENV")"
        deactivate
        echo "Deactivated: $current_venv"
    else
        echo "No active virtual environment"
    fi
}

# Export functions
export -f _pm_activate
export -f _pm_deactivate 