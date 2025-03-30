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

def run_command(command, cwd=None, use_xvfb=False):
    """Runs a shell command, logs output, and checks for errors."""
    # Prepend xvfb-run if requested
    if use_xvfb:
        final_command = ["xvfb-run", "-a"] + command
    else:
        final_command = command

    logger.info(f"Running command: {' '.join(final_command)}")
    try:
        # Popen inherits the current environment by default
        process = subprocess.Popen(
            final_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            cwd=cwd
        )
        # Log output line by line
        if process.stdout:
            for line in iter(process.stdout.readline, ""):
                logger.info(f"COLMAP: {line.strip()}")
        process.wait()
        if process.returncode != 0:
            logger.error(f"Command failed with exit code {process.returncode}: {' '.join(final_command)}")
            raise subprocess.CalledProcessError(process.returncode, final_command)
        logger.info(f"Command finished successfully: {' '.join(final_command)}")
    except FileNotFoundError:
        # Specifically check if it was xvfb-run or colmap that wasn't found
        cmd_not_found = final_command[0]
        logger.error(f"Error: '{cmd_not_found}' command not found. Is it installed and in your PATH?")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise

def run_colmap_pipeline(image_dir, output_dir):
    """Executes the full COLMAP reconstruction pipeline."""
    logger.info("Starting COLMAP pipeline...")
    logger.info(f"Input Image Directory: {image_dir}")
    logger.info(f"Output Directory: {output_dir}")

    # --- Set Environment for Headless Qt (Robustness) ---
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    logger.info("Set QT_QPA_PLATFORM=offscreen for headless execution.")

    # --- Check for Xvfb and Decide on GPU Usage ---
    use_gpu = False
    if shutil.which("xvfb-run"):
        logger.info("Found 'xvfb-run'. Will attempt to use GPU with COLMAP via virtual framebuffer.")
        use_gpu = True
    else:
        logger.warning("'xvfb-run' not found. COLMAP will run in CPU-only mode.")
        logger.warning("Install 'xvfb' for potential GPU acceleration in headless environments.")
    
    # COLMAP expects boolean flags as strings 'true' or 'false'
    gpu_flag_str = str(use_gpu).lower()

    # --- Define Paths ---
    base_dir = os.path.abspath(output_dir)
    image_dir_abs = os.path.abspath(image_dir)
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
        return False

    # --- Step 1: Feature Extraction ---
    logger.info("Step 1: Extracting features...")
    cmd_feature = [
        "colmap", "feature_extractor",
        "--database_path", db_path,
        "--image_path", image_dir_abs,
        "--ImageReader.single_camera", "1",
        "--ImageReader.camera_model", "PINHOLE",
        "--SiftExtraction.use_gpu", gpu_flag_str # Use GPU if available
    ]
    run_command(cmd_feature, use_xvfb=use_gpu)

    # --- Step 2: Feature Matching ---
    logger.info("Step 2: Matching features...")
    cmd_match = [
        "colmap", "exhaustive_matcher",
        "--database_path", db_path,
        "--SiftMatching.use_gpu", gpu_flag_str # Use GPU if available
    ]
    run_command(cmd_match, use_xvfb=use_gpu)

    # --- Step 3: Sparse Reconstruction (Mapping) ---
    logger.info("Step 3: Sparse reconstruction (mapping)...")
    cmd_map = [
        "colmap", "mapper",
        "--database_path", db_path,
        "--image_path", image_dir_abs,
        "--output_path", sparse_path,
        # Consider adding mapper options if needed, e.g., related to camera parameters
        "--Mapper.init_min_num_inliers", "50" # Lower threshold to help initialization
    ]
    run_command(cmd_map, use_xvfb=use_gpu)

    # --- Step 4: Image Undistortion ---
    logger.info("Step 4: Undistorting images...")
    sparse_model_path = os.path.join(sparse_path, "0")
    if not os.path.exists(sparse_model_path):
         alt_sparse_model_paths = [d for d in os.listdir(sparse_path) if os.path.isdir(os.path.join(sparse_path, d))]
         if not alt_sparse_model_paths:
             logger.error(f"Error: No sparse model found in {sparse_path}. Mapping might have failed.")
             raise FileNotFoundError(f"No sparse model found in {sparse_path}")
         sparse_model_path = os.path.join(sparse_path, alt_sparse_model_paths[0])
         logger.warning(f"Sparse model '0' not found, using first available: {sparse_model_path}")

    cmd_undistort = [
        "colmap", "image_undistorter",
        "--image_path", image_dir_abs,
        "--input_path", sparse_model_path,
        "--output_path", dense_path,
        "--output_type", "COLMAP",
    ]
    run_command(cmd_undistort, use_xvfb=use_gpu)

    # --- Step 5: Dense Stereo Matching ---
    logger.info("Step 5: Dense stereo matching...")
    cmd_stereo = [
        "colmap", "patch_match_stereo",
        "--workspace_path", dense_path,
        "--workspace_format", "COLMAP",
        "--PatchMatchStereo.geom_consistency", "true",
        # PatchMatchStereo might also benefit from GPU, check COLMAP docs for specific flags 
        # (e.g., --PatchMatchStereo.gpu_index can specify a GPU)
    ]
    run_command(cmd_stereo, use_xvfb=use_gpu)

    # --- Step 6: Stereo Fusion ---
    logger.info("Step 6: Fusing stereo results into 3D model...")
    cmd_fuse = [
        "colmap", "stereo_fusion",
        "--workspace_path", dense_path,
        "--workspace_format", "COLMAP",
        "--input_type", "geometric",
        "--output_path", fused_ply_path,
    ]
    run_command(cmd_fuse, use_xvfb=use_gpu)

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
        "-o",
        "--output_dir", 
        type=str, 
        default="./colmap_output",
        help="Directory to store COLMAP intermediate and final results. Defaults to './colmap_output'."
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
