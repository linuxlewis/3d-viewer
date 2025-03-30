import argparse
import logging
import os
import subprocess
import shutil

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s"
)
logger = logging.getLogger(__name__)

def run_command(command, cwd=None):
    """Runs a shell command, logs output, and checks for errors."""
    logger.info(f"Running command: {' '.join(command)}")
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            cwd=cwd,
        )
        # Log output line by line
        if process.stdout:
            for line in iter(process.stdout.readline, ""):
                logger.info(f"COLMAP: {line.strip()}")
        process.wait()
        if process.returncode != 0:
            logger.error(f"Command failed with exit code {process.returncode}: {' '.join(command)}")
            raise subprocess.CalledProcessError(process.returncode, command)
        logger.info(f"Command finished successfully: {' '.join(command)}")
    except FileNotFoundError:
        logger.error(f"Error: 'colmap' command not found. Is COLMAP installed and in your PATH?")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise

def run_colmap_pipeline(image_dir, output_dir):
    """Executes the full COLMAP reconstruction pipeline."""
    logger.info("Starting COLMAP pipeline...")
    logger.info(f"Input Image Directory: {image_dir}")
    logger.info(f"Output Directory: {output_dir}")

    # --- Define Paths ---
    # Ensure paths are absolute or relative to a known base, handling potential spaces
    base_dir = os.path.abspath(output_dir)
    image_dir_abs = os.path.abspath(image_dir) # COLMAP prefers absolute paths
    db_path = os.path.join(base_dir, "colmap.db")
    sparse_path = os.path.join(base_dir, "sparse")
    dense_path = os.path.join(base_dir, "dense")
    fused_ply_path = os.path.join(dense_path, "fused.ply")

    # --- Create Output Directories ---
    logger.info(f"Creating output directories...")
    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(sparse_path, exist_ok=True)
    os.makedirs(dense_path, exist_ok=True)

    # --- Check for COLMAP ---
    if not shutil.which("colmap"):
        logger.error("COLMAP command not found. Please install COLMAP and ensure it's in your system's PATH.")
        return False # Indicate failure

    # --- Step 1: Feature Extraction ---
    logger.info("Step 1: Extracting features...")
    cmd_feature = [
        "colmap", "feature_extractor",
        "--database_path", db_path,
        "--image_path", image_dir_abs,
        "--ImageReader.single_camera", "1", # Assuming images are from one virtual camera
        "--ImageReader.camera_model", "PINHOLE" # Simple camera model often sufficient for synthetic views
        # Add SiftExtraction options if needed, e.g.: --SiftExtraction.use_gpu=true
    ]
    run_command(cmd_feature)

    # --- Step 2: Feature Matching ---
    logger.info("Step 2: Matching features...")
    cmd_match = [
        "colmap", "exhaustive_matcher",
        "--database_path", db_path,
        # Add SiftMatching options if needed, e.g.: --SiftMatching.use_gpu=true
    ]
    run_command(cmd_match)

    # --- Step 3: Sparse Reconstruction (Mapping) ---
    logger.info("Step 3: Sparse reconstruction (mapping)...")
    cmd_map = [
        "colmap", "mapper",
        "--database_path", db_path,
        "--image_path", image_dir_abs,
        "--output_path", sparse_path,
    ]
    run_command(cmd_map)

    # --- Step 4: Image Undistortion ---
    # Undistorts images and prepares for dense reconstruction
    logger.info("Step 4: Undistorting images...")
    # Use the sparse model generated (assuming '0' is the first/main model)
    sparse_model_path = os.path.join(sparse_path, "0")
    if not os.path.exists(sparse_model_path):
         alt_sparse_model_paths = [d for d in os.listdir(sparse_path) if os.path.isdir(os.path.join(sparse_path, d))]
         if not alt_sparse_model_paths:
             logger.error(f"Error: No sparse model found in {sparse_path}. Mapping might have failed.")
             raise FileNotFoundError(f"No sparse model found in {sparse_path}")
         sparse_model_path = os.path.join(sparse_path, alt_sparse_model_paths[0]) # Use the first one found
         logger.warning(f"Sparse model '0' not found, using first available: {sparse_model_path}")

    cmd_undistort = [
        "colmap", "image_undistorter",
        "--image_path", image_dir_abs,
        "--input_path", sparse_model_path,
        "--output_path", dense_path,
        "--output_type", "COLMAP", # Specify output format explicitly
    ]
    run_command(cmd_undistort)

    # --- Step 5: Dense Stereo Matching ---
    logger.info("Step 5: Dense stereo matching...")
    cmd_stereo = [
        "colmap", "patch_match_stereo",
        "--workspace_path", dense_path,
        "--workspace_format", "COLMAP",
        "--PatchMatchStereo.geom_consistency", "true", # Often improves results
    ]
    run_command(cmd_stereo)

    # --- Step 6: Stereo Fusion ---
    logger.info("Step 6: Fusing stereo results into 3D model...")
    cmd_fuse = [
        "colmap", "stereo_fusion",
        "--workspace_path", dense_path,
        "--workspace_format", "COLMAP",
        "--input_type", "geometric", # Use geometric consistency results
        "--output_path", fused_ply_path,
    ]
    run_command(cmd_fuse)

    logger.info(f"COLMAP pipeline finished successfully. Output PLY: {fused_ply_path}")
    return True # Indicate success


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the COLMAP pipeline for 3D reconstruction from multiple views."
    )
    parser.add_argument(
        "image_dir", type=str, help="Directory containing the input image views."
    )
    parser.add_argument(
        "output_dir", type=str, help="Directory to store COLMAP intermediate and final results."
    )

    args = parser.parse_args()

    # Basic validation
    if not os.path.isdir(args.image_dir):
        logger.error(f"Input image directory not found: {args.image_dir}")
        exit(1)

    try:
        run_colmap_pipeline(args.image_dir, args.output_dir)
    except Exception as e:
        logger.error(f"COLMAP pipeline failed: {e}")
        exit(1) 
