import { chromium } from '../web/player/node_modules/playwright/index.mjs';
import fs from 'node:fs';

const url = process.env.FACTORY_URL || 'http://127.0.0.1:8003/factory-model-full/package/';
const out = process.env.FACTORY_CHECK_OUT || 'runs/v1/factory-model-full';
const browser = await chromium.launch({ channel: 'msedge', headless: true,
  args: ['--use-gl=angle', `--use-angle=${process.env.FACTORY_ANGLE || 'd3d11'}`,
    '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
const external = [];
page.on('pageerror', error => errors.push(error.message));
page.on('console', message => {
  if (message.type() === 'error') errors.push(message.text());
});
await page.route('**/*', async route => {
  const requested = new URL(route.request().url());
  if (requested.protocol !== 'data:' && requested.origin !== new URL(url).origin) {
    external.push(requested.href);
    await route.abort();
  } else await route.continue();
});
const result = { url, errors, external, checks: {} };
try {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.evaluate(() => window.isaacReplay.ready);
  const snapshot = async time => page.evaluate(seconds => {
    window.isaacReplay.seek(seconds);
    const root = window.__checkpoint.loaded;
    root.updateMatrixWorld(true);
    const position = name => {
      const node = root.getObjectByName(name);
      if (!node) throw new Error(`Missing ${name}`);
      const p = node.getWorldPosition(node.position.clone());
      return p.toArray();
    };
    return { state: window.isaacReplay.getState(),
      hand: position('panda_hand'),
      first: position('Item000'), last: position('Item010') };
  }, time);
  result.checks.start = await snapshot(0);
  result.checks.middle = await snapshot(35);
  result.checks.end = await snapshot(70);
  result.checks.chapters = (await page.evaluate(() => window.isaacReplay.getExperience())).chapters.length;
  if (result.checks.start.state.duration < 72 || result.checks.chapters !== 12)
    throw new Error('Expected 11-item animation and 12 guided chapters');
  if (JSON.stringify(result.checks.start.hand) === JSON.stringify(result.checks.middle.hand))
    throw new Error('Robot hand did not move');
  if (JSON.stringify(result.checks.start.last) === JSON.stringify(result.checks.end.last))
    throw new Error('Last item did not move');
  if (Math.abs(result.checks.start.hand[0] - 0.389) > 0.02 ||
      Math.abs(result.checks.start.first[0] - 15) > 0.02 ||
      Math.abs(result.checks.end.last[0] - 0.5) > 0.05)
    throw new Error('Factory recording has an incorrect world-unit scale');
  await page.getByRole('button', { name: 'Guided demo' }).click();
  result.checks.guidedTitle = await page.locator('#tour-title').innerText();
  await page.getByRole('button', { name: 'Start', exact: true }).click();
  await page.waitForTimeout(350);
  await page.getByRole('button', { name: 'Pause' }).click();
  result.checks.paused = await page.evaluate(() => window.isaacReplay.getState());
  if (result.checks.paused.playing) throw new Error('Pause did not stop playback');
  await page.getByRole('button', { name: 'Restart' }).click();
  result.checks.restarted = await page.evaluate(() => window.isaacReplay.getState());
  if (result.checks.restarted.time > 0.5) throw new Error('Restart did not reset playback');
  await page.getByRole('button', { name: 'Pause' }).click();
  await page.evaluate(() => window.isaacReplay.seek(35));
  const cameraBefore = await page.evaluate(() => window.__checkpoint.camera.position.toArray());
  const canvas = page.locator('canvas').first();
  const bounds = await canvas.boundingBox();
  await page.mouse.move(bounds.x + bounds.width * 0.5, bounds.y + bounds.height * 0.5);
  await page.mouse.down();
  await page.mouse.move(bounds.x + bounds.width * 0.62, bounds.y + bounds.height * 0.55,
    { steps: 8 });
  await page.mouse.up();
  result.checks.cameraBefore = cameraBefore;
  result.checks.cameraAfter = await page.evaluate(() => window.__checkpoint.camera.position.toArray());
  if (JSON.stringify(result.checks.cameraBefore) === JSON.stringify(result.checks.cameraAfter))
    throw new Error('Drag did not navigate camera');
  await page.getByRole('button', { name: 'Reset view' }).click();
  await page.getByRole('button', { name: 'Clear', exact: true }).click();
  await page.evaluate(() => window.isaacReplay.setCamera({
    position: [4, 3, 5], target: [0, 0.5, 0],
  }));
  await page.screenshot({ path: `${out}/preview.png`, fullPage: true });
  if (errors.length || external.length) throw new Error('Browser errors or external requests');
  result.status = 'PASS';
} catch (error) {
  result.status = 'FAIL';
  result.failure = error.message;
  throw error;
} finally {
  fs.writeFileSync(`${out}/browser-check.json`, JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
  await browser.close();
}
