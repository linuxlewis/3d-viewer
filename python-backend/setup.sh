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
#uv venv
#. .venv/bin/activate

# --- Install Python Dependencies ---
echo "Installing Python dependencies using uv..."
#uv sync

# --- Install COLMAP (Debian/Ubuntu) ---
echo "Checking for COLMAP..."
if ! command -v colmap &> /dev/null
then
    echo "COLMAP not found. Attempting installation using apt (requires sudo)."
    # Update package list and install colmap
    # The -y flag automatically confirms the installation
    apt-get update &&  apt-get install -y colmap
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

# --- Install Xvfb (Virtual Framebuffer for headless GPU) ---
echo "Checking for Xvfb..."
if ! command -v xvfb-run &> /dev/null
then
    echo "Xvfb (xvfb-run) not found. Attempting installation using apt (requires sudo)."
    apt-get update && apt-get install -y xvfb
    echo "Verifying Xvfb installation after apt install..."
    if ! command -v xvfb-run &> /dev/null
    then
        echo "Xvfb installation via apt failed or command still not found."
        echo "GPU acceleration for COLMAP in headless mode might not work."
        # Don't exit, as the rest might still work without GPU COLMAP
    else
        echo "Xvfb (xvfb-run) successfully installed via apt."
    fi
else
    echo "Xvfb found: $(command -v xvfb-run)"
fi

# --- Install Node.js and npm ---
echo "Checking for Node.js and npm..."
NODE_MAJOR=20 # Specify the desired major Node.js version (e.g., 20 for LTS)
MIN_NODE_VERSION="v${NODE_MAJOR}."
NODE_INSTALLED=$(command -v node &> /dev/null && node -v || echo "none")

if [[ "$NODE_INSTALLED" == "none" || ! $(node -v | grep -q "^${MIN_NODE_VERSION}") ]]; then
    if [[ "$NODE_INSTALLED" != "none" ]]; then
        echo "Existing Node.js version $(node -v) is older than required (${MIN_NODE_VERSION}). Upgrading..."
    else
        echo "Node.js not found. Attempting installation using NodeSource (requires sudo)."
    fi

    # Install required packages for NodeSource script
    apt-get update && apt-get install -y ca-certificates curl gnupg

    # --- Add removal step for old/conflicting packages ---
    echo "Attempting to remove potentially conflicting old Node.js packages..."
    apt-get remove -y nodejs npm libnode-dev || echo "Old packages not found or already removed."
    apt-get autoremove -y # Clean up dependencies if any were removed

    # Add NodeSource GPG key
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg

    # Add NodeSource repository
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list

    # Update package list and install Node.js (which includes npm)
    apt-get update && apt-get install nodejs -y

    echo "Verifying Node.js and npm installation after NodeSource setup..."
    if ! command -v node &> /dev/null || ! command -v npm &> /dev/null
    then
        echo "Node.js or npm installation via NodeSource failed."
        echo "Please check the NodeSource documentation or install manually: https://nodejs.org/"
        exit 1 # Exit if installation fails
    else
        echo "Node.js and npm successfully installed/updated via NodeSource."
        node -v
        npm -v
    fi
else
    echo "Node.js version $(node -v) meets the requirement (${MIN_NODE_VERSION})."
    echo "npm found: $(npm -v)"
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
