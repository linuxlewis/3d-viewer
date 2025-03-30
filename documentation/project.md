📘 Project: From AI Image to 3D Web Experience

🔹 Goal

- Transform a single image (e.g., generated via Stable Diffusion, or from user journals) into an interactive "pseudo-3D" or "2.5D" web experience, simulating parallax based on user interaction (e.g., mouse movement).

⸻

🧩 Revised Tech Stack

| Stage                    | Tool / Library             | Notes                                     |
| :----------------------- | :------------------------- | :---------------------------------------- |
| Depth Estimation         | MiDaS (PyTorch)            | Generates depth map from input image.     |
| Mesh Data Generation     | Python (NumPy, OpenCV)     | Creates a plane mesh displaced by depth.  |
| Web Viewer & Interaction | Three.js                   | Renders the mesh and handles parallax.    |

⸻

⚠️ **Pivot from COLMAP Approach**

Initial attempts used COLMAP for 3D reconstruction. However, this proved unsuitable for the target imagery (often containing people, nature scenes like beaches/water) due to fundamental limitations:

1.  **Static Scene Requirement:** COLMAP requires the scene to be identical across all views. People, water, foliage, etc., are non-static and violate this assumption.
2.  **Feature Matching Challenges:** Natural scenes and human subjects often lack the distinct, stable, and texture-rich features COLMAP needs for reliable matching between views.
3.  **Synthetic View Limitations:** While views can be generated via warping, they don't perfectly replicate the geometric consistency of real photos taken from different positions, which can hinder COLMAP's reconstruction process.

Given these challenges, the COLMAP pipeline frequently failed during the sparse reconstruction phase (mapper initialization).

The **Direct Mesh Warping** approach described below is better suited for creating the desired visual effect from single images, especially those containing non-static or less-textured elements, as it does not rely on multi-view feature matching.

⸻

🔧 **Revised Implementation Plan**

⸻

**Step 1: Depth Estimation from Image**

*   **Input:** `image.jpg`
*   **Output:** `depth.png` (Grayscale depth map)
*   **Tool:** `python-backend/midas_depth.py` (No changes needed here)

```python
# python-backend/midas_depth.py (Conceptual Usage)
# python python-backend/midas_depth.py path/to/image.jpg -o path/to/depth.png
```

⸻

**Step 2: Generate Displaced Mesh Data (Python)**

*   **Input:** `image.jpg`, `depth.png`
*   **Output:** `mesh_data.json` (or similar format containing vertex positions and UVs)
*   **Tool:** New Python script (e.g., `python-backend/generate_mesh.py`)

```python
# python-backend/generate_mesh.py (Conceptual)
import cv2
import numpy as np
import json

def generate_displaced_mesh(image_path, depth_path, output_json_path, grid_density=100, depth_scale=0.1):
    img = cv2.imread(image_path)
    depth = cv2.imread(depth_path, cv2.IMREAD_GRAYSCALE)
    if img is None or depth is None:
        print("Error loading images")
        return

    h, w = img.shape[:2]
    # Normalize depth map (0.0 = far, 1.0 = near)
    depth_normalized = depth.astype(np.float32) / 255.0

    # Create a grid (adjust density as needed)
    x = np.linspace(-w / h, w / h, grid_density) # Adjust aspect ratio
    y = np.linspace(-1, 1, grid_density)
    xv, yv = np.meshgrid(x, y)

    # Sample depth map at grid points (requires careful interpolation)
    # Simple example: use nearest neighbor - better interpolation needed for quality
    grid_h, grid_w = xv.shape
    sampled_depth = np.zeros_like(xv)
    for i in range(grid_h):
        for j in range(grid_w):
            # Map grid coords back to image coords
            img_x = int(((xv[i, j] * h / w) + 1) * w / 2) # Map back from aspect-corrected coords
            img_y = int((-yv[i, j] + 1) * h / 2)
            img_x = np.clip(img_x, 0, w - 1)
            img_y = np.clip(img_y, 0, h - 1)
            sampled_depth[i, j] = depth_normalized[img_y, img_x]

    # Displace Z based on depth (adjust scale)
    zv = (sampled_depth - 0.5) * depth_scale # Center depth around z=0

    # Flatten vertices and create UVs
    vertices = np.stack([xv.flatten(), yv.flatten(), zv.flatten()], axis=-1).tolist()
    uvs = np.stack([(xv.flatten() * h / w + 1) / 2, (-yv.flatten() + 1) / 2], axis=-1).tolist() # Map UVs correctly

    # Define faces (triangles for the grid)
    faces = []
    for i in range(grid_h - 1):
        for j in range(grid_w - 1):
            # Vertex indices
            v0 = i * grid_w + j
            v1 = i * grid_w + (j + 1)
            v2 = (i + 1) * grid_w + j
            v3 = (i + 1) * grid_w + (j + 1)
            # Triangle 1: v0, v1, v2
            faces.append([v0, v1, v2])
            # Triangle 2: v1, v3, v2
            faces.append([v1, v3, v2])

    mesh_data = {
        "vertices": vertices,
        "uvs": uvs,
        "faces": faces
    }

    with open(output_json_path, 'w') as f:
        json.dump(mesh_data, f)

# Usage
# python python-backend/generate_mesh.py image.jpg depth.png mesh_data.json
```
*Note: The mesh generation code above is conceptual and needs refinement, especially regarding depth sampling/interpolation and UV mapping.*

⸻

**Step 3: Load and View in Three.js (Browser)**

*   **Input:** `image.jpg`, `mesh_data.json` (or `depth.png` if doing client-side displacement)
*   **Output:** Interactive web view with parallax effect.
*   **Tool:** HTML + Three.js (`viewer.js`)

File structure example:

```
web-viewer/
  index.html
  viewer.js
  assets/
    image.jpg
    mesh_data.json
  node_modules/
    three/
```

HTML:

```html
<!-- index.html -->
<!DOCTYPE html>
<html>
<head>
    <title>2.5D Image Viewer</title>
    <style> body { margin: 0; overflow: hidden; } canvas { display: block; } </style>
</head>
<body>
    <script type="importmap">
        {
            "imports": {
                "three": "https://unpkg.com/three@0.160.0/build/three.module.js"
            }
        }
    </script>
    <script type="module" src="viewer.js"></script>
</body>
</html>
```

Three.js Viewer (using pre-computed mesh data):

```javascript
// viewer.js
import * as THREE from 'three';

let camera, scene, renderer;
let mesh;
const mouse = new THREE.Vector2();
const target = new THREE.Vector2();
const windowHalf = new THREE.Vector2(window.innerWidth / 2, window.innerHeight / 2);

init();
animate();

async function init() {
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x111111);

    camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.z = 2; // Adjust camera distance as needed

    // Load mesh data
    const meshDataResponse = await fetch('./assets/mesh_data.json');
    const meshData = await meshDataResponse.json();

    // Create geometry
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(meshData.vertices.flat(), 3));
    geometry.setAttribute('uv', new THREE.Float32BufferAttribute(meshData.uvs.flat(), 2));
    geometry.setIndex(meshData.faces.flat());
    geometry.computeVertexNormals(); // Optional, for lighting

    // Load texture
    const textureLoader = new THREE.TextureLoader();
    const texture = await textureLoader.loadAsync('./assets/image.jpg');
    texture.colorSpace = THREE.SRGBColorSpace; // Important for correct colors

    // Create material
    const material = new THREE.MeshBasicMaterial({ map: texture }); // Use MeshStandardMaterial for lighting

    // Create mesh
    mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    // Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    document.body.appendChild(renderer.domElement);

    // Event listeners
    document.addEventListener('mousemove', onMouseMove);
    window.addEventListener('resize', onWindowResize);
}

function onWindowResize() {
    windowHalf.set(window.innerWidth / 2, window.innerHeight / 2);
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

function onMouseMove(event) {
    // Normalize mouse coordinates (-1 to +1)
    mouse.x = (event.clientX - windowHalf.x);
    mouse.y = (event.clientY - windowHalf.y);
}

function animate() {
    requestAnimationFrame(animate);

    // Simple parallax effect: move camera slightly based on mouse
    target.x = (mouse.x * 0.001); // Adjust sensitivity
    target.y = (mouse.y * 0.001); // Adjust sensitivity

    // Smoothly interpolate camera rotation or position
    if (mesh) {
         mesh.rotation.y += (target.x - mesh.rotation.y) * 0.05;
         mesh.rotation.x += (-target.y - mesh.rotation.x) * 0.05;
         // Alternatively, move the camera position slightly
         // camera.position.x += (target.x - camera.position.x) * 0.05;
         // camera.position.y += (-target.y - camera.position.y) * 0.05;
    }

    renderer.render(scene, camera);
}

```

*Note: The viewer code provides a basic structure. Implementing robust parallax, potentially using device orientation, and optimizing mesh generation/loading would be further steps.*
