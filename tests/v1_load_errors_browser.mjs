import { chromium } from '../web/player/node_modules/playwright/index.mjs';
import fs from 'node:fs';

const url = process.env.ACCEPT_URL || 'http://127.0.0.1:8003/player-download-probe/';
const browser = await chromium.launch({ channel: 'msedge', headless: true,
  args: ['--use-gl=angle', '--use-angle=d3d11'] });
const result = {};
try {
  const page = await browser.newPage();
  await page.route('**/scene.glb', async route => {
    await new Promise(resolve => setTimeout(resolve, 700));
    await route.continue();
  });
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  result.loading = await page.locator('#status').innerText();
  await page.evaluate(() => window.isaacReplay.ready);
  result.ready = await page.locator('#status').innerText();
  if (!result.loading.includes('Loading scene') || !result.ready.includes('clip'))
    throw new Error('Loading and ready statuses are not clear');
  await page.close();
  const broken = await browser.newPage();
  await broken.route('**/scene.glb', route => route.fulfill({ status: 404,
    contentType: 'text/plain', body: 'Missing scene' }));
  await broken.goto(url);
  await broken.getByText(/Load failed:/).waitFor();
  result.missingScene = await broken.locator('#status').innerText();
  if (!result.missingScene.includes('404'))
    throw new Error('Required scene failure did not show HTTP status');
  result.status = 'PASS';
  await broken.close();
} catch (error) {
  result.status = 'FAIL'; result.failure = error.message; throw error;
} finally {
  fs.writeFileSync('runs/v1/load-errors-browser.json', JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
  await browser.close();
}
