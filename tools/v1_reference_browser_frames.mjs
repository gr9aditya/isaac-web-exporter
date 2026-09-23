import { chromium } from '../web/player/node_modules/playwright/index.mjs';
import fs from 'node:fs';
import path from 'node:path';

const url = process.env.E06_URL || 'http://127.0.0.1:8003/v1-release-guided/package/';
const times = (process.env.E06_TIMES || '0,15,29.9').split(',').map(Number);
const output = process.env.E06_OUTPUT || 'runs/v1/reference-browser';
fs.mkdirSync(output, { recursive: true });
const browser = await chromium.launch({ channel: 'msedge', headless: true,
  args: ['--use-gl=angle', '--use-angle=d3d11'] });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 },
  deviceScaleFactor: 1 });
const errors = [];
const external = [];
page.on('pageerror', error => errors.push(error.message));
await page.route('**/*', async route => {
  const requested = new URL(route.request().url());
  if (requested.origin !== new URL(url).origin && requested.protocol !== 'data:') {
    external.push(requested.href);
    await route.abort();
  } else await route.continue();
});
const result = { url, times, frames: [], errors, external };
try {
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => window.isaacReplay.ready);
  await page.addStyleTag({ content: `
    .masthead,.timeline,.inspector,.view-actions,#tour-banner,#anchor-label {display:none!important}
    .workspace,.viewport,#canvas {width:100%!important;height:100%!important}
  ` });
  await page.waitForFunction(() => {
    const canvas = document.querySelector('#canvas canvas');
    return canvas?.width === 1280 && canvas?.height === 720;
  });
  for (const seconds of times) {
    const state = await page.evaluate(time => {
      window.isaacReplay.pause();
      window.isaacReplay.seek(time);
      window.isaacReplay.setCamera({ position: [7, 6, 9], target: [0, 0.6, 0.5] });
      return { ...window.isaacReplay.getState(),
        camera: window.__checkpoint.camera.position.toArray(),
        target: window.__checkpoint.orbit.target.toArray(),
        aspect: window.__checkpoint.camera.aspect,
        fov: window.__checkpoint.camera.fov };
    }, seconds);
    await page.waitForTimeout(120);
    const image = path.join(output, `browser-${seconds}.png`);
    await page.locator('#canvas canvas').screenshot({ path: image });
    result.frames.push({ seconds, image, state });
  }
  if (errors.length || external.length) throw new Error('Browser errors or external requests');
  result.status = 'PASS';
} catch (error) {
  result.status = 'FAIL';
  result.failure = error.message;
  throw error;
} finally {
  fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
  await browser.close();
}
