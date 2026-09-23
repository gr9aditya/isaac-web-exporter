import { chromium } from 'playwright';
import fs from 'node:fs';

const browser = await chromium.launch({
  channel: 'msedge',
  headless: true,
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
});
const objectName = process.env.CHECKPOINT_OBJECT || 'FallingBox';
const resultDir = process.env.CHECKPOINT_RESULT_DIR || '..';
const extraObjectNames = (process.env.CHECKPOINT_EXTRA_OBJECTS || '').split(',').filter(Boolean);
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
const errors = [];
const externalRequests = [];
await page.route('**/*', async route => {
  const url = new URL(route.request().url());
  if (url.protocol !== 'data:' && url.origin !== new URL(process.env.CHECKPOINT_URL || 'http://127.0.0.1:4173/').origin) {
    externalRequests.push(url.href);
    await route.abort();
  } else {
    await route.continue();
  }
});
page.on('pageerror', error => errors.push(error.message));
page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });

try {
  await page.goto(process.env.CHECKPOINT_URL || 'http://127.0.0.1:4173/', { waitUntil: 'networkidle' });
  await page.waitForFunction(() => window.__checkpoint?.clips > 0, { timeout: 20000 });
  const initial = await page.evaluate(({ objectName, extraObjectNames }) => ({
    clips: window.__checkpoint.clips,
    duration: window.__checkpoint.clip.duration,
    object: window.__checkpoint.loaded.getObjectByName(objectName)?.position.toArray(),
    extras: Object.fromEntries(extraObjectNames.map(name => {
      const node = window.__checkpoint.loaded.getObjectByName(name);
      return [name, node ? { position: node.position.toArray(), quaternion: node.quaternion.toArray() } : null];
    })),
    camera: window.__checkpoint.camera.position.toArray(),
    renderer: (() => {
      const gl = document.querySelector('canvas').getContext('webgl2');
      const extension = gl?.getExtension('WEBGL_debug_renderer_info');
      return extension ? gl.getParameter(extension.UNMASKED_RENDERER_WEBGL) : 'unreported';
    })(),
  }), { objectName, extraObjectNames });
  await page.screenshot({ path: `${resultDir}/browser-initial.png` });
  await page.getByRole('button', { name: 'Start', exact: true }).click();
  await page.waitForTimeout(650);
  await page.getByRole('button', { name: 'Pause' }).click();
  const paused = await page.evaluate(({ objectName, extraObjectNames }) => ({
    time: window.__checkpoint.mixer.time,
    object: window.__checkpoint.loaded.getObjectByName(objectName)?.position.toArray(),
    extras: Object.fromEntries(extraObjectNames.map(name => {
      const node = window.__checkpoint.loaded.getObjectByName(name);
      return [name, node ? { position: node.position.toArray(), quaternion: node.quaternion.toArray() } : null];
    })),
  }), { objectName, extraObjectNames });
  await page.screenshot({ path: `${resultDir}/browser-paused.png` });
  await page.waitForTimeout(300);
  const pausedAgain = await page.evaluate(() => window.__checkpoint.mixer.time);
  await page.getByRole('button', { name: 'Restart' }).click();
  const restarted = await page.evaluate(() => window.__checkpoint.mixer.time);
  const element = page.locator('#canvas canvas');
  const bounds = await element.boundingBox();
  await page.mouse.move(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2);
  await page.mouse.down();
  await page.mouse.move(bounds.x + bounds.width / 2 + 100, bounds.y + bounds.height / 2 + 40, { steps: 10 });
  await page.mouse.up();
  await page.waitForTimeout(100);
  const cameraAfterDrag = await page.evaluate(() => window.__checkpoint.camera.position.toArray());
  await page.screenshot({ path: `${resultDir}/browser-proof.png` });
  const result = { initial, paused, pausedAgain, restarted, cameraAfterDrag, externalRequests, errors };
  fs.writeFileSync(`${resultDir}/browser-proof.json`, JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result, null, 2));
  if (initial.clips < 1 || initial.duration < 0.5) throw new Error('Animation missing or too short');
  if (initial.camera.some(value => !Number.isFinite(value) || Math.abs(value) > 1e6)) throw new Error('Camera framing is invalid');
  if (!initial.object || !paused.object || JSON.stringify(initial.object) === JSON.stringify(paused.object)) throw new Error(`${objectName} did not move`);
  for (const name of extraObjectNames) {
    if (!initial.extras[name] || !paused.extras[name] || JSON.stringify(initial.extras[name]) === JSON.stringify(paused.extras[name])) throw new Error(`${name} did not move`);
  }
  if (paused.time < 0.2 || Math.abs(pausedAgain - paused.time) > 0.05) throw new Error('Playback or Pause failed');
  if (restarted >= Math.min(0.5, paused.time * 0.75)) throw new Error('Restart failed');
  if (JSON.stringify(initial.camera) === JSON.stringify(cameraAfterDrag)) throw new Error('Camera navigation failed');
  if (errors.length) throw new Error('Browser errors: ' + errors.join('; '));
  if (externalRequests.length) throw new Error('External requests: ' + externalRequests.join('; '));
} finally {
  await browser.close();
}
