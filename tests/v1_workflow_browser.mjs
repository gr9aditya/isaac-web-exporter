import { chromium } from '../web/player/node_modules/playwright/index.mjs';
import fs from 'node:fs';

const url = process.env.ACCEPT_URL || 'http://127.0.0.1:8003/from-isaac-sort/';
const origin = new URL(url).origin;
const browser = await chromium.launch({ channel: process.env.ACCEPT_CHANNEL || 'msedge', headless: true,
  args: ['--use-gl=angle', '--use-angle=d3d11'] });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
const errors = [];
const external = [];
page.on('pageerror', error => errors.push(error.message));
page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
await page.route('**/*', async route => {
  const requested = new URL(route.request().url());
  if (requested.protocol !== 'data:' && requested.origin !== origin) {
    external.push(requested.href);
    await route.abort();
  } else await route.continue();
});

const output = process.env.ACCEPT_OUTPUT || 'runs/v1/sort-workflow-browser';
const result = { url, errors, external };
try {
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.waitForFunction(() => window.isaacReplay?.getState().duration === 30);
  result.objects = await page.locator('.object-row').allTextContents();
  result.samples = await page.evaluate(() => {
    const find = id => {
      let found;
      window.__checkpoint.loaded.traverse(node => {
        if (node.userData.isaacObjectId === id) found = node;
      });
      if (!found) throw new Error(`Missing node ${id}`);
      return found;
    };
    const parts = [
      '/World/Products/PartA', '/World/Products/PartB',
      '/World/Sorter/Shoulder', '/World/Sorter/Shoulder/Elbow',
      '/World/Sorter/Shoulder/Elbow/Wrist',
    ].map(find);
    const samples = [];
    const times = [
      ...Array.from({ length: 21 }, (_, index) => index * 1.5),
      ...Array.from({ length: 10 }, (_, index) => 1 + 3 * index + 1 / 60),
    ].sort((a, b) => a - b);
    for (const time of times) {
      window.isaacReplay.seek(time);
      window.__checkpoint.loaded.updateMatrixWorld(true);
      samples.push({ time, nodes: parts.map(node => ({
        id: node.userData.isaacObjectId,
        worldPosition: node.getWorldPosition(node.position.clone()).toArray(),
        worldQuaternion: node.getWorldQuaternion(node.quaternion.clone()).toArray(),
        worldScale: node.getWorldScale(node.scale.clone()).toArray(),
        localQuaternion: node.quaternion.toArray(),
      })) });
    }
    return samples;
  });
  for (const time of [0, 15, 30]) {
    await page.evaluate(t => window.isaacReplay.seek(t), time);
    await page.screenshot({ path: `${output}-${time}.png` });
  }
  await page.getByRole('button', { name: 'Start', exact: true }).click();
  await page.waitForTimeout(200);
  result.restartFromEnd = await page.evaluate(() => window.isaacReplay.getState());
  if (!result.restartFromEnd.playing || result.restartFromEnd.time > 0.5)
    throw new Error('Start from end failed');
  if (errors.length || external.length) throw new Error('External request or browser error');
  result.status = 'PASS';
} catch (error) {
  result.status = 'FAIL';
  result.failure = error.message;
  throw error;
} finally {
  fs.writeFileSync(`${output}.json`, JSON.stringify(result, null, 2));
  console.log(JSON.stringify({ status: result.status, objects: result.objects?.length,
    samples: result.samples?.length, restartFromEnd: result.restartFromEnd,
    errors, external, failure: result.failure }));
  await browser.close();
}
