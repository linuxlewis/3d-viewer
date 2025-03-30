import * as THREE from 'three';

let camera, scene, renderer;
let mesh;
const mouse = new THREE.Vector2();
const target = new THREE.Vector2();
const windowHalf = new THREE.Vector2(window.innerWidth / 2, window.innerHeight / 2);
const loadingIndicator = document.getElementById('loading-indicator'); // Get loading indicator element

// Function to get URL parameters
function getUrlParams() {
    const params = {};
    const queryString = window.location.search.substring(1);
    const regex = /([^&=]+)=([^&]*)/g;
    let m;
    while (m = regex.exec(queryString)) {
        params[decodeURIComponent(m[1])] = decodeURIComponent(m[2]);
    }
    return params;
}

// Get the asset name from URL
const urlParams = getUrlParams();
const assetName = urlParams['name'] || 'image'; // Default to 'image' if no name is provided

// Construct asset paths
// Adjust this logic if your naming convention is different
const imagePath = `public/${assetName}.jpg`;
const meshDataPath = `public/${assetName}_mesh.json`;

// Start the application after init completes
(async () => {
  try {
    await init(); // Wait for async setup to complete
    if (loadingIndicator) loadingIndicator.style.display = 'none'; // Hide indicator on success
    animate();    // Start the animation loop *after* init is done
  } catch (error) {
    console.error("Failed to initialize viewer:", error);
    if (loadingIndicator) {
        loadingIndicator.textContent = `Error loading ${assetName}. See console for details.`; // Update on error
        loadingIndicator.style.color = 'red';
    }
    // Optionally, display an error message to the user on the page here
  }
})();

async function init() {
    console.log(`init started for asset: ${assetName}`);
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x111111);

    camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.z = 2; // Adjust camera distance as needed
    console.log("Camera created at:", camera.position);

    try {
      // Load mesh data
      console.log(`Loading mesh data from ${meshDataPath}...`);
      const meshDataResponse = await fetch(meshDataPath); // Use dynamic path
      if (!meshDataResponse.ok) {
        throw new Error(`HTTP error loading mesh data! status: ${meshDataResponse.status}`);
      }
      const meshData = await meshDataResponse.json();
      console.log("Mesh data loaded:", meshData);

      // Create geometry
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.Float32BufferAttribute(meshData.vertices.flat(), 3));
      geometry.setAttribute('uv', new THREE.Float32BufferAttribute(meshData.uvs.flat(), 2));
      geometry.setIndex(meshData.faces.flat());
      geometry.computeVertexNormals(); // Optional, for lighting
      console.log("Geometry created");

      // Load texture
      console.log(`Loading texture from ${imagePath}...`);
      const textureLoader = new THREE.TextureLoader();
      const texture = await textureLoader.loadAsync(imagePath); // Use dynamic path
      texture.colorSpace = THREE.SRGBColorSpace; // Important for correct colors
      texture.flipY = false; // Keep flipY setting if needed
      console.log("Texture loaded:", texture);

      // Create material
      const material = new THREE.MeshBasicMaterial({ map: texture }); // Use MeshStandardMaterial for lighting
      console.log("Material created");

      // Create mesh
      mesh = new THREE.Mesh(geometry, material);
      console.log("Mesh created:", mesh);
      scene.add(mesh);
      console.log("Mesh added to scene at position:", mesh.position);

      // Renderer
      renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setSize(window.innerWidth, window.innerHeight);
      document.body.appendChild(renderer.domElement);
      console.log("Renderer created and appended");

      // Event listeners
      document.addEventListener('mousemove', onMouseMove);
      window.addEventListener('resize', onWindowResize);
      console.log("Event listeners added");
      console.log(`init finished successfully for ${assetName}`);

    } catch (error) {
        console.error(`Error during asset loading or mesh creation for ${assetName}:`, error);
        throw error; // Re-throw the error to be caught by the outer try-catch
    }
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

    // Ensure renderer is available before calling render
    if (renderer && scene && camera) {
      renderer.render(scene, camera);
    } else {
      // console.warn("Renderer, scene, or camera not ready for rendering yet.");
    }
}
