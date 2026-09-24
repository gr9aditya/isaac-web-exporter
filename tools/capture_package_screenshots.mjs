// Capture a browser package at selected recorded times using Playwright.

import { chromium } from '../web/player/node_modules/playwright/index.mjs';
import fs from 'node:fs';
import path from 'node:path';

const url = process.env.CAPTURE_URL;
const out = process.env.CAPTURE_OUT;
if (!url || !out) throw new Error('Set CAPTURE_URL and CAPTURE_OUT');
const times = (process.env.CAPTURE_TIMES || '0,35,70')
  .split(',').map(Number);
if (times.some(time => !Number.isFinite(time) || time < 0))
  throw new Error('CAPTURE_TIMES must be nonnegative seconds');
fs.mkdirSync(out, { recursive: true });

const browser = await chromium.launch({ channel: 'msedge', headless: true,
  args: ['--use-gl=angle', '--use-angle=d3d11'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on('pageerror', error => errors.push(error.message));
page.on('console', message => {
  if (message.type() === 'error') errors.push(message.text());
});
try {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.evaluate(() => window.isaacReplay.ready);
  await page.getByRole('button', { name: 'Guided demo' }).click();
  await page.evaluate(() => window.isaacReplay.setCamera({
    position: [3, 2.3, 3.8], target: [0.35, 0.3, 0],
  }));
  for (const time of times) {
    await page.evaluate(seconds => window.isaacReplay.seek(seconds), time);
    await page.waitForTimeout(200);
    const state = await page.evaluate(() => window.isaacReplay.getState());
    if (Math.abs(state.time - time) > 0.05)
      throw new Error(`Seek failed for ${time}: ${state.time}`);
    const target = path.join(out, `guided-${String(time).replace('.', '-')}.png`);
    await page.screenshot({ path: target });
    console.log(`${time} ${target}`);
  }
  if (errors.length) throw new Error(errors.join('; '));
} finally {
  await browser.close();
}
