import cv2
import numpy as np
import json
import argparse
import logging
import os

# Configure basic logging at the module level
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s"
)
logger = logging.getLogger(__name__)

def generate_displaced_mesh(image_path, depth_path, output_json_path, grid_density=100, depth_scale=0.1):
    """
    Generates mesh data (vertices, UVs, faces) from an image and its depth map.
    The mesh is a grid displaced along the Z-axis based on the depth map.
    """
    logger.info(f"Loading image from: {image_path}")
    img = cv2.imread(image_path)
    logger.info(f"Loading depth map from: {depth_path}")
    depth_map = cv2.imread(depth_path, cv2.IMREAD_GRAYSCALE)

    if img is None:
        logger.error(f"Error loading image: {image_path}")
        return
    if depth_map is None:
        logger.error(f"Error loading depth map: {depth_path}")
        return

    h, w = img.shape[:2]
    logger.info(f"Image dimensions: {w}x{h}")
    # Ensure depth map has the same dimensions as the image, resize if necessary
    if depth_map.shape[0] != h or depth_map.shape[1] != w:
        logger.warning(f"Depth map dimensions ({depth_map.shape[1]}x{depth_map.shape[0]}) differ from image dimensions ({w}x{h}). Resizing depth map.")
        depth_map = cv2.resize(depth_map, (w, h), interpolation=cv2.INTER_LINEAR)

    # Normalize depth map (0.0 = far, 1.0 = near - adjust if MiDaS output is inverse)
    # Assuming MiDaS output is higher value = closer, so normalize 0-1
    # Check for max depth value to avoid division by zero if depth map is all black
    max_depth = np.max(depth_map)
    if max_depth == 0:
        logger.warning("Depth map is all black (max value is 0). Mesh will be flat.")
        depth_normalized = np.zeros_like(depth_map, dtype=np.float32)
    else:
        depth_normalized = depth_map.astype(np.float32) / max_depth
    # If MiDaS outputs inverse depth (lower value = closer), use:
    # depth_normalized = 1.0 - (depth_map.astype(np.float32) / 255.0)

    logger.info(f"Creating grid with density: {grid_density}x{grid_density}")
    # Create a grid (normalized coordinates -1 to +1)
    # Adjust aspect ratio for the grid points
    aspect_ratio = w / h
    x = np.linspace(-aspect_ratio, aspect_ratio, grid_density)
    y = np.linspace(-1, 1, grid_density)
    xv, yv = np.meshgrid(x, y) # xv, yv are grid coordinates in world space

    # Sample depth map at grid points
    # Map grid coords (-aspect_ratio to +aspect_ratio, -1 to 1) to image coords (0 to w-1, 0 to h-1)
    img_x_coords = ((xv / aspect_ratio + 1) / 2 * w).astype(int)
    img_y_coords = ((-yv + 1) / 2 * h).astype(int) # Flip Y-axis

    # Clamp coordinates to be within image bounds
    img_x_coords = np.clip(img_x_coords, 0, w - 1)
    img_y_coords = np.clip(img_y_coords, 0, h - 1)

    # Sample depth at the calculated image coordinates
    sampled_depth = depth_normalized[img_y_coords, img_x_coords]

    # Displace Z based on depth (adjust scale)
    # Center the displacement around z=0
    logger.info(f"Applying depth displacement with scale: {depth_scale}")
    zv = (sampled_depth - 0.5) * depth_scale

    # Flatten vertices (X, Y, Z)
    # Use the original grid coordinates (xv, yv) for X and Y
    vertices = np.stack([xv.flatten(), yv.flatten(), zv.flatten()], axis=-1).tolist()

    # Create UV coordinates (0 to 1)
    # Map grid coords to UV coords (0 to 1)
    u_coords = (xv / aspect_ratio + 1) / 2
    v_coords = (-yv + 1) / 2 # Flip Y-axis for UVs as well
    uvs = np.stack([u_coords.flatten(), v_coords.flatten()], axis=-1).tolist()

    # Define faces (triangles for the grid)
    faces = []
    grid_h, grid_w = xv.shape
    for i in range(grid_h - 1):
        for j in range(grid_w - 1):
            # Vertex indices in the flattened list
            v0 = i * grid_w + j         # Top-left
            v1 = i * grid_w + (j + 1)     # Top-right
            v2 = (i + 1) * grid_w + j     # Bottom-left
            v3 = (i + 1) * grid_w + (j + 1) # Bottom-right
            # Triangle 1: v0, v1, v2 (Top-left, Top-right, Bottom-left)
            faces.append([v0, v1, v2])
            # Triangle 2: v1, v3, v2 (Top-right, Bottom-right, Bottom-left)
            faces.append([v1, v3, v2])

    mesh_data = {
        "vertices": vertices,
        "uvs": uvs,
        "faces": faces
    }

    logger.info(f"Writing mesh data to: {output_json_path}")
    try:
        with open(output_json_path, 'w') as f:
            json.dump(mesh_data, f, indent=4) # Use indent for readability
        logger.info(f"Successfully generated mesh data at: {output_json_path}")
    except IOError as e:
        logger.error(f"Error writing JSON file: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate 3D mesh data from an image and its depth map.")
    parser.add_argument("image_path", help="Path to the input image file.")
    parser.add_argument("depth_path", help="Path to the input depth map file (grayscale image).")
    parser.add_argument("-o", "--output", dest="output_json_path", default=None, help="Path to save the output mesh data (JSON file). Defaults to <image_path_base>_mesh.json")
    parser.add_argument("-d", "--density", type=int, default=150, help="Grid density (number of vertices along each dimension). Default: 150")
    parser.add_argument("-s", "--scale", type=float, default=0.1, help="Depth scale factor for Z displacement. Default: 0.1")

    args = parser.parse_args()

    # Determine the output path if not provided
    output_path = args.output_json_path
    if output_path is None:
        base_name = os.path.splitext(args.image_path)[0]
        output_path = f"{base_name}_mesh.json"
        logger.info(f"Output path not specified, defaulting to: {output_path}")

    generate_displaced_mesh(args.image_path, args.depth_path, output_path, args.density, args.scale) 
