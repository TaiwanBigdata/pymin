#!/usr/bin/env bash

# PyMin shell wrapper for virtual environment management

function _pm_activate() {
    local venv_path="$1"
    
    # If no path provided, use default
    if [ -z "$venv_path" ]; then
        venv_path="env"
    fi
    
    # Check if already in a virtual environment
    if [ -n "$VIRTUAL_ENV" ]; then
        local current_venv="$(basename "$VIRTUAL_ENV")"
        echo "Currently in virtual environment: $current_venv"
        read -p "Do you want to switch to $venv_path? [Y/n] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            deactivate
            source "$venv_path/bin/activate"
        fi
    else
        source "$venv_path/bin/activate"
    fi
}

# Export the function so it's available in the shell
export -f _pm_activate 