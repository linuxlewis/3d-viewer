#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Starting project setup..."

# --- Install uv ---
echo "Installing uv..."
# Download and run the official uv installer script
curl -LsSf https://astral.sh/uv/install.sh | sh

# --- Add uv to PATH for this script's execution ---
# The installer script will print instructions on how to add uv to your PATH permanently.
# For this script to find uv immediately after installation, we add common install locations to the PATH.
# Adjust this if uv is installed elsewhere on your system.
export PATH="$HOME/.cargo/bin:$PATH"  # Common location if installed via rust/cargo
export PATH="$HOME/.local/bin:$PATH" # Common location for pipx or direct installs

# Verify uv installation
echo "Verifying uv installation..."
uv --version

# --- Create Virtual Environment ---
echo "Creating virtual environment (.venv)..."
uv venv .venv

# --- Install Python Dependencies ---
echo "Installing Python dependencies using uv..."
# Use the Python interpreter from the created virtual environment
# Installs PyTorch, OpenCV, and NumPy
uv pip install -p .venv/bin/python torch opencv-python numpy

# --- Install COLMAP (Debian/Ubuntu) ---
echo "Checking for COLMAP..."
if ! command -v colmap &> /dev/null
then
    echo "COLMAP not found. Attempting installation using apt (requires sudo)."
    # Update package list and install colmap
    # The -y flag automatically confirms the installation
    sudo apt-get update && sudo apt-get install -y colmap
    echo "Verifying COLMAP installation after apt install..."
    if ! command -v colmap &> /dev/null
    then
        echo "COLMAP installation via apt failed or command still not found."
        echo "Please install COLMAP manually: https://colmap.github.io/install.html"
        exit 1 # Exit if installation fails
    else
        echo "COLMAP successfully installed via apt."
    fi
else
    echo "COLMAP found: $(command -v colmap)"
fi

echo ""
echo "--------------------"
echo "Setup complete!"
echo "--------------------"
echo ""
echo "To activate the virtual environment, run:"
echo "source .venv/bin/activate"
echo ""
echo "You can then run the Python scripts, e.g.:"
echo "python python-backend/midas_depth.py <input_image> <output_depth>"
echo "python python-backend/generate_views.py <input_image> <depth_map> <views_dir>"
echo "python python-backend/run_colmap.py <views_dir> <colmap_output_dir>"
echo "" 
