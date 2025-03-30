# midas_depth.py
import argparse
import logging

import cv2
import numpy as np
import torch

# Configure basic logging at the module level
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s"
)
logger = logging.getLogger(__name__)


def run_depth_estimation(input_path, output_path):
    """Runs MiDaS depth estimation on an input image and saves the depth map."""
    logger.info("Loading MiDaS model...")
    # model_type = "MiDaS_small" # Smaller, faster model
    model_type = "DPT_Large"  # More accurate, larger model
    midas = torch.hub.load("intel-isl/MiDaS", model_type)

    # Check if CUDA is available and move the model to GPU if it is
    device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
    midas.to(device)
    midas.eval()
    logger.info(f"Using device: {device}")

    logger.info("Loading image transformation...")
    midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
    transform = (
        midas_transforms.dpt_transform
        if model_type == "DPT_Large"
        else midas_transforms.small_transform
    )

    logger.info(f"Reading input image: {input_path}")
    img = cv2.imread(input_path)
    if img is None:
        logger.error(f"Error: Could not read image file {input_path}")
        return

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    logger.info("Transforming image...")
    input_batch = transform(img_rgb).to(device)

    logger.info("Running inference...")
    with torch.no_grad():
        prediction = midas(input_batch)

        # Resize prediction to original image size
        prediction = torch.nn.functional.interpolate(
            prediction.unsqueeze(1),
            size=img_rgb.shape[:2],
            mode="bicubic",
            align_corners=False,
        ).squeeze()

    depth_map = prediction.cpu().numpy()

    logger.info("Normalizing and saving depth map...")
    # Normalize depth map to 0-255 and convert to uint8
    output = cv2.normalize(depth_map, None, 0, 255, cv2.NORM_MINMAX)
    output = output.astype(np.uint8)

    # Optional: Apply colormap for visualization
    # output_colored = cv2.applyColorMap(output, cv2.COLORMAP_INFERNO)

    cv2.imwrite(output_path, output)
    logger.info(f"Depth map saved to: {output_path}")


if __name__ == "__main__":
    # Logging is configured at the top level now
    # logging.basicConfig(
    #     level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    # )

    parser = argparse.ArgumentParser(
        description="Estimate depth from a single image using MiDaS."
    )
    parser.add_argument("input_image", type=str, help="Path to the input image file.")
    parser.add_argument(
        "output_depth",
        type=str,
        help="Path to save the output depth map (e.g., depth.png).",
    )
    args = parser.parse_args()

    run_depth_estimation(args.input_image, args.output_depth)
