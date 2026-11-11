// Prueba extremo a extremo: levanta el backend (tutor simulado) y recorre Inicio → Simulación → Resultados → SUS.
import { createRequire } from 'node:module';
import { spawn, execSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); }
catch { ({ chromium } = require(execSync('npm root -g').toString().trim() + '/playwright')); }

const PORT = process.env.E2E_PORT || '8765';
const OUT = process.env.E2E_OUT || 'e2e/screenshots';
mkdirSync(OUT, { recursive: true });
const server = spawn('python3', ['-m', 'cervix_sim'], {
  cwd: 'backend', stdio: 'inherit',
  env: { ...process.env, PORT, TUTOR_MODE: 'mock', ADMIN_TOKEN: 'e2e-token' },
});
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let failed = false;
try {
  for (let i = 0; i < 50; i++) { try { if ((await fetch(`http://127.0.0.1:${PORT}/api/health`)).ok) break; } catch { await sleep(200); } }
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 });
  const problems = [];
  page.on('console', (m) => { if (['error', 'warning'].includes(m.type()) && !/ERR_TUNNEL|ERR_NAME_NOT_RESOLVED/.test(m.text())) problems.push(m.text()); });  // (se ignoran las fuentes de Google bloqueadas en el sandbox)
  page.on('pageerror', (e) => problems.push(String(e)));
  await page.goto(`http://127.0.0.1:${PORT}/`);
  await page.getByRole('heading', { name: 'Prepara tu sesión' }).waitFor();
  await page.screenshot({ path: `${OUT}/1-inicio.png` });
  await page.fill('#nombre', 'Ana Prueba'); await page.fill('#correo', 'ana@example.com');
  await page.check('#consentimiento');
  await page.getByRole('button', { name: /Iniciar Simulación/ }).click();
  await page.getByRole('heading', { name: 'Entorno de Simulación' }).waitFor();
  await page.getByRole('button', { name: 'Pedir sugerencia al tutor' }).click();
  await page.locator('.bubble.tutor').waitFor();
  await page.getByRole('button', { name: 'Acercar' }).click();
  await page.screenshot({ path: `${OUT}/2-simulacion.png` });
  await page.selectOption('#interpretacion', { index: 1 });
  await page.getByRole('button', { name: /Registrar Decisión/ }).click();
  await page.getByRole('heading', { name: 'Dashboard de Resultados' }).waitFor();
  await page.screenshot({ path: `${OUT}/3-resultados.png`, fullPage: true });
  await page.reload(); await page.getByRole('heading', { name: 'Dashboard de Resultados' }).waitFor(); // reanuda sesión
  await page.getByRole('button', { name: /Reporte SUS/ }).click();
  for (let i = 0; i < 10; i++) await page.locator(`input[name=sus${i}][value="4"]`).check({ force: true });
  await page.screenshot({ path: `${OUT}/4-sus.png` });
  await page.getByRole('button', { name: 'Enviar cuestionario' }).click();
  await page.getByText(/Tu puntaje SUS es/).waitFor();
  await page.getByRole('button', { name: 'Cerrar' }).click();
  await page.getByRole('button', { name: /Volver al Inicio/ }).click();
  await page.getByRole('heading', { name: 'Prepara tu sesión' }).waitFor();
  await page.setViewportSize({ width: 390, height: 800 });
  await page.screenshot({ path: `${OUT}/5-movil.png` });
  if (problems.length) { console.error('Problemas de consola:', problems); failed = true; }
  await browser.close();
  console.log(failed ? 'E2E con problemas' : 'E2E OK');
} catch (e) { console.error(e); failed = true; }
finally { server.kill(); }
process.exit(failed ? 1 : 0);
