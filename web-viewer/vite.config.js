import { defineConfig } from 'vite';

export default defineConfig({
  base: '/3d-viewer/', // Replace <your-repo-name> with your actual GitHub repository name
  server: {
    port: 3000, // Specify the port for the dev server
    host: '0.0.0.0' // Optional: Makes the server accessible on your network
  }
}); 
