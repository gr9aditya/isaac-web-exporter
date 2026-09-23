import { chromium } from '../web/player/node_modules/playwright/index.mjs';
import fs from 'node:fs';

const url = process.env.ACCEPT_URL || 'http://127.0.0.1:8003/from-panel-package/';
const browser = await chromium.launch({ channel: process.env.ACCEPT_CHANNEL || 'msedge', headless: true,
  args: ['--use-gl=angle', '--use-angle=d3d11'] });
const results = [];
for (const width of [480, 1280]) {
  const page = await browser.newPage({ viewport: { width, height: 800 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.waitForFunction(() => window.isaacReplay?.getState().duration > 0);
  const boxes = await page.evaluate(() => {
    const rect = id => {
      const { x, y, width, height } = document.querySelector(id).getBoundingClientRect();
      return { x, y, width, height };
    };
    const canvas = document.querySelector('#canvas canvas');
    const gl = canvas.getContext('webgl2');
    return { canvas: rect('#canvas'), timeline: rect('.timeline'), start: rect('#start'),
      renderer: gl.getExtension('WEBGL_debug_renderer_info')
        ? gl.getParameter(gl.getExtension('WEBGL_debug_renderer_info').UNMASKED_RENDERER_WEBGL)
        : 'unreported' };
  });
  await page.locator('body').click({ position: { x: width / 2, y: 15 } });
  await page.keyboard.press('Space');
  await page.waitForTimeout(100);
  const playing = await page.evaluate(() => window.isaacReplay.getState().playing);
  await page.keyboard.press('Space');
  if (!playing || boxes.canvas.width < 200 || boxes.canvas.height < 200 ||
      boxes.start.y + boxes.start.height > 800 || errors.length)
    throw new Error(`Unusable ${width}px layout: ${JSON.stringify({boxes, playing, errors})}`);
  await page.screenshot({ path: `runs/v1/responsive-${width}.png` });
  results.push({ width, boxes, playing, errors, status: 'PASS' });
  await page.close();
}
fs.writeFileSync('runs/v1/responsive-browser.json', JSON.stringify(results, null, 2));
console.log(JSON.stringify(results));
await browser.close();
