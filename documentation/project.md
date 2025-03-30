📘 Project: From AI Image to 3D Web Experience

🔹 Goal

Transform a single image (e.g., generated via Stable Diffusion) into a pseudo-3D scene that can be explored interactively in a web browser using Three.js.

⸻

🧩 Tech Stack

Stage	Tool / Library
Depth Estimation	MiDaS (PyTorch)
View Synthesis	OpenCV
3D Reconstruction	COLMAP
Mesh Conversion	MeshLab / Blender / Open3D
Web Viewer	Three.js (GLTFLoader, OrbitControls)



⸻

🔧 Implementation Plan with Code Snippets

⸻

Step 1: Depth Estimation from Image

Input: image.jpg
Output: depth.png

# midas_depth.py
import torch
import cv2
import numpy as np

def run_depth_estimation(input_path, output_path):
    model_type = "DPT_Large"
    midas = torch.hub.load("intel-isl/MiDaS", model_type)
    midas.eval()

    transform = torch.hub.load("intel-isl/MiDaS", "transforms").dpt_transform
    img = cv2.imread(input_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    input_tensor = transform(img_rgb).unsqueeze(0)

    with torch.no_grad():
        prediction = midas(input_tensor)[0]
        depth = prediction.numpy()

    # Normalize and save as grayscale
    depth_norm = cv2.normalize(depth, None, 0, 255, cv2.NORM_MINMAX)
    depth_uint8 = depth_norm.astype(np.uint8)
    cv2.imwrite(output_path, depth_uint8)

# Usage
# python midas_depth.py image.jpg depth.png



⸻

Step 2: Generate Synthetic Views Using Depth Map

Input: image.jpg, depth.png
Output: Multiple warped views in views/

# generate_views.py
import cv2
import numpy as np
import os

def shift_view(image_path, depth_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    img = cv2.imread(image_path)
    depth = cv2.imread(depth_path, cv2.IMREAD_GRAYSCALE).astype(np.float32)

    h, w = img.shape[:2]
    for i, shift in enumerate([-20, -10, 0, 10, 20]):
        map_x, map_y = np.meshgrid(np.arange(w), np.arange(h))
        map_x = map_x.astype(np.float32) + shift * (depth / 255.0)
        warped = cv2.remap(img, map_x, map_y.astype(np.float32), interpolation=cv2.INTER_LINEAR)
        cv2.imwrite(f"{output_dir}/view_{i}.png", warped)

# Usage
# python generate_views.py image.jpg depth.png views/



⸻

Step 3: Reconstruct 3D Model with COLMAP

Input: Synthetic image views
Output: fused.ply 3D model

# Terminal commands

# Set paths
IMAGE_PATH=views/
DB_PATH=colmap.db
SPARSE_PATH=sparse/
DENSE_PATH=dense/

# Step 1: Extract features
colmap feature_extractor --database_path $DB_PATH --image_path $IMAGE_PATH

# Step 2: Match features
colmap exhaustive_matcher --database_path $DB_PATH

# Step 3: Sparse reconstruction
mkdir $SPARSE_PATH
colmap mapper --database_path $DB_PATH --image_path $IMAGE_PATH --output_path $SPARSE_PATH

# Step 4: Undistort images
colmap image_undistorter --image_path $IMAGE_PATH --input_path $SPARSE_PATH/0 --output_path $DENSE_PATH

# Step 5: Dense stereo matching
colmap patch_match_stereo --workspace_path $DENSE_PATH --workspace_format COLMAP

# Step 6: Fuse stereo into 3D model
colmap stereo_fusion --workspace_path $DENSE_PATH --workspace_format COLMAP --output_path $DENSE_PATH/fused.ply



⸻

Step 4: Convert 3D Model for the Web

Use MeshLab or Blender to convert fused.ply to scene.glb or scene.gltf.

In Blender:
	•	Import .ply
	•	File → Export → .glb or .gltf

⸻

Step 5: Load and View in Three.js (Browser)

File structure:

public/
  index.html
  scene.glb
src/
  viewer.js

HTML:

<!-- index.html -->
<!DOCTYPE html>
<html>
  <head>
    <title>3D Viewer</title>
    <style> body { margin: 0; overflow: hidden; } </style>
  </head>
  <body>
    <script type="module" src="viewer.js"></script>
  </body>
</html>

Three.js Viewer:

// viewer.js
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x111111);

const camera = new THREE.PerspectiveCamera(70, window.innerWidth/window.innerHeight, 0.1, 100);
camera.position.set(0, 1, 3);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;

const light = new THREE.HemisphereLight(0xffffff, 0x444444);
scene.add(light);

const loader = new GLTFLoader();
loader.load('scene.glb', (gltf) => {
  scene.add(gltf.scene);
});

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}
animate();
