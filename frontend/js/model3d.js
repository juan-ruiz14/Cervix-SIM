// Visor 3D: carga un .glb (GLTFLoader + Meshopt + texturas WebP) y permite girar y hacer zoom.
// three.js se sirve desde vendor/three (ver vendor/three/LEEME.md). Se importa de forma dinámica
// para que el resto de la aplicación funcione aunque esa carpeta aún no esté instalada.
let libs = null;

async function loadLibs() {
  if (!libs) {
    const [THREE, { GLTFLoader }, { OrbitControls }, { MeshoptDecoder }] = await Promise.all([
      import('../vendor/three/three.module.js'),
      import('../vendor/three/GLTFLoader.js'),
      import('../vendor/three/OrbitControls.js'),
      import('../vendor/three/meshopt_decoder.module.js'),
    ]);
    libs = { THREE, GLTFLoader, OrbitControls, MeshoptDecoder };
  }
  return libs;
}

/**
 * Monta el visor dentro de `container`.
 * @returns {Promise<{zoom(f:number):void, reset():void, dispose():void}>}
 */
export async function createViewer(container, url, { onProgress } = {}) {
  const { THREE, GLTFLoader, OrbitControls, MeshoptDecoder } = await loadLibs();
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.domElement.className = 'viewer-canvas';
  renderer.domElement.setAttribute('aria-label', 'Modelo 3D del caso. Arrastra para girar, usa la rueda para acercar.');
  container.prepend(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(40, 1, 0.05, 100);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x445066, 1.5));
  const key = new THREE.DirectionalLight(0xffffff, 2.2);
  key.position.set(2, 3, 4);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xbcd0ff, 0.9);
  fill.position.set(-3, -1, -2);
  scene.add(fill);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.minDistance = 1.2;
  controls.maxDistance = 8;
  controls.rotateSpeed = 0.8;

  const HOME = new THREE.Vector3(0, 0.4, 4);
  const resetView = () => { camera.position.copy(HOME); controls.target.set(0, 0, 0); controls.update(); };
  resetView();

  const resize = () => {
    const w = container.clientWidth || 1, h = container.clientHeight || 1;
    renderer.setSize(w, h, false);
    renderer.domElement.style.width = '100%';
    renderer.domElement.style.height = '100%';
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };
  const ro = new ResizeObserver(resize);
  ro.observe(container);
  resize();

  let raf = 0, alive = true;
  const tick = () => {
    if (!alive) return;
    raf = requestAnimationFrame(tick);
    controls.update();
    renderer.render(scene, camera);
  };
  tick();

  const loader = new GLTFLoader();
  loader.setMeshoptDecoder(MeshoptDecoder);
  const gltf = await new Promise((resolve, reject) => {
    loader.load(url, resolve, (e) => { if (onProgress && e.lengthComputable) onProgress(e.loaded / e.total); }, reject);
  });
  if (!alive) return { zoom() {}, reset() {}, dispose() {} };
  const model = gltf.scene;
  // Centrar y escalar para que el modelo ocupe ~2 unidades, sin importar las unidades de origen.
  const box = new THREE.Box3().setFromObject(model);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const k = 2 / (Math.max(size.x, size.y, size.z) || 1);
  model.position.sub(center);
  const holder = new THREE.Group();
  holder.scale.setScalar(k);
  holder.add(model);
  scene.add(holder);

  return {
    zoom(factor) {
      const offset = camera.position.clone().sub(controls.target).multiplyScalar(factor);
      const len = Math.min(controls.maxDistance, Math.max(controls.minDistance, offset.length()));
      camera.position.copy(controls.target).add(offset.setLength(len));
      controls.update();
    },
    distance() { return camera.position.distanceTo(controls.target); },
    reset: resetView,
    dispose() {
      alive = false;
      cancelAnimationFrame(raf);
      ro.disconnect();
      controls.dispose();
      model.traverse((o) => {
        if (o.geometry) o.geometry.dispose();
        if (o.material) {
          for (const v of Object.values(o.material)) if (v && v.isTexture) v.dispose();
          o.material.dispose();
        }
      });
      renderer.dispose();
      renderer.domElement.remove();
    },
  };
}
