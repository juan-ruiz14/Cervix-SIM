// Copia las piezas de three.js que usa el visor 3D a frontend/vendor/three (sin paso de compilación).
// Uso (desde frontend/):  npm install three@0.160.0 --no-save && node tools/instalar_three.mjs
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');
const pkg = join(root, 'node_modules', 'three');
const out = join(root, 'vendor', 'three');
if (!existsSync(pkg)) {
  console.error('No encuentro node_modules/three. Ejecuta primero: npm install three@0.160.0 --no-save');
  process.exit(1);
}
mkdirSync(out, { recursive: true });

// [origen dentro de three, destino en vendor/three, reescribir imports]
const files = [
  ['build/three.module.js', 'three.module.js', false],
  ['examples/jsm/loaders/GLTFLoader.js', 'GLTFLoader.js', true],
  ['examples/jsm/utils/BufferGeometryUtils.js', 'BufferGeometryUtils.js', true],
  ['examples/jsm/controls/OrbitControls.js', 'OrbitControls.js', true],
  ['examples/jsm/libs/meshopt_decoder.module.js', 'meshopt_decoder.module.js', false],
];
for (const [src, dst, rewrite] of files) {
  const from = join(pkg, src);
  if (!existsSync(from)) { console.error(`Falta ${src} en la versión instalada de three.`); process.exit(1); }
  if (!rewrite) { copyFileSync(from, join(out, dst)); continue; }
  const text = readFileSync(from, 'utf8')
    .replace(/from\s+['"]three['"]/g, "from './three.module.js'")
    .replace(/from\s+['"]\.\.\/utils\/BufferGeometryUtils\.js['"]/g, "from './BufferGeometryUtils.js'");
  writeFileSync(join(out, dst), text);
}
console.log('three.js instalado en frontend/vendor/three:', files.map((f) => f[1]).join(', '));
