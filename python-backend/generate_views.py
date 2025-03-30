# generate_views.py
import argparse
import logging
import os

import cv2
import numpy as np

# Configure basic logging at the module level
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s"
)
logger = logging.getLogger(__name__)


def shift_view(image_path, depth_path, output_dir, shifts):
    """Generates shifted views of an image using its depth map."""
    logger.info(f"Reading image: {image_path}")
    img = cv2.imread(image_path)
    if img is None:
        logger.error(f"Error: Could not read image file {image_path}")
        return

    logger.info(f"Reading depth map: {depth_path}")
    depth = cv2.imread(depth_path, cv2.IMREAD_GRAYSCALE)
    if depth is None:
        logger.error(f"Error: Could not read depth map file {depth_path}")
        return
    depth = depth.astype(np.float32)

    h, w = img.shape[:2]
    logger.info(f"Image dimensions: {w}x{h}")

    logger.info(f"Creating output directory: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)

    # Prepare meshgrid
    map_x_base, map_y = np.meshgrid(np.arange(w), np.arange(h))
    map_y = map_y.astype(np.float32)  # map_y remains constant
    center_x = w / 2.0
    # Calculate relative x coordinates (0 at center, +/- w/2 at edges)
    relative_x = map_x_base.astype(np.float32) - center_x

    # --- Perspective configuration ---
    # Controls how much more pixels shift towards the edges compared to the center
    # Adjust this value to control the 'convergence' effect. 0.0 = parallel shift.
    perspective_strength = 0.3
    logger.info(f"Using perspective strength: {perspective_strength}")

    logger.info(f"Generating {len(shifts)} shifted views...")
    for i, shift_amount in enumerate(shifts):
        logger.info(
            f"  Generating view {i+1}/{len(shifts)} with shift {shift_amount}..."
        )
        # Normalize depth to 0-1 range for shift calculation
        depth_normalized = depth / 255.0

        # Calculate perspective scaling: 1.0 at center, >1.0 towards edges
        # Avoid division by zero if width is very small (unlikely)
        if center_x > 0:
            perspective_scale = 1.0 + (np.abs(relative_x) / center_x) * perspective_strength
        else:
            perspective_scale = 1.0

        # Calculate final horizontal shift incorporating depth and perspective
        # Pixels further from the center (larger |relative_x|) will have their shift amplified
        map_x_shifted = map_x_base.astype(np.float32) + \
                        shift_amount * depth_normalized * perspective_scale

        # Remap the image using the shifted coordinates
        warped = cv2.remap(
            img,
            map_x_shifted,
            map_y,
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE,
        )

        # Save the warped view
        output_filename = f"view_{i:03d}_shift_{shift_amount}.png"
        output_filepath = os.path.join(output_dir, output_filename)
        cv2.imwrite(output_filepath, warped)
        logger.debug(f"    Saved view to: {output_filepath}")

    logger.info("View generation complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate synthetic views using an image and its depth map."
    )
    parser.add_argument("input_image", type=str, help="Path to the input image file.")
    parser.add_argument(
        "input_depth", type=str, help="Path to the input depth map file (grayscale)."
    )
    parser.add_argument(
        "-d",
        "--output_dir",
        type=str,
        default="./views",
        help="Directory to save the generated views. Defaults to './views'.",
    )
    parser.add_argument(
        "--shifts",
        type=int,
        nargs="+",
        default=[-60, -30, 0, 30, 60],
        help="List of horizontal shift amounts.",
    )

    args = parser.parse_args()

    shift_view(args.input_image, args.input_depth, args.output_dir, args.shifts)
