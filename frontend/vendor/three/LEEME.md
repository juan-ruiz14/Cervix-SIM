# three.js (visor 3D)

Esta carpeta se llena con el script de instalación (no se descarga nada en tiempo de ejecución):

    cd frontend
    npm install three@0.160.0 --no-save
    node tools/instalar_three.mjs

Quedan aquí: `three.module.js`, `GLTFLoader.js`, `OrbitControls.js`, `BufferGeometryUtils.js` y
`meshopt_decoder.module.js` (necesario para el modelo CS-001, que usa compresión Meshopt).
Estos archivos sí se suben a GitHub (la app los sirve desde el mismo origen).
