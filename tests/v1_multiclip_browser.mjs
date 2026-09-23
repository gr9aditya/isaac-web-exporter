import { chromium } from '../web/player/node_modules/playwright/index.mjs';
import fs from 'node:fs';

const browser = await chromium.launch({ channel: 'msedge', headless: true,
  args: ['--use-gl=angle', '--use-angle=d3d11'] });
const page = await browser.newPage();
const result = {};
try {
  await page.goto('http://127.0.0.1:8003/two-clips/');
  await page.evaluate(() => window.isaacReplay.ready);
  result.initial = await page.evaluate(() => window.isaacReplay.getState());
  result.prompt = await page.locator('#status').innerText();
  result.startEnabled = await page.locator('#start').isEnabled();
  if (result.initial.clipIndex !== -1 || result.startEnabled ||
      !result.prompt.includes('choose one'))
    throw new Error('Multiple clips were silently selected');
  await page.getByRole('combobox', { name: 'Clip' }).selectOption('1');
  result.chosen = await page.evaluate(() => window.isaacReplay.getState());
  if (result.chosen.clipIndex !== 1 || !(await page.locator('#start').isEnabled()))
    throw new Error('Explicit alternate clip selection failed');
  await page.evaluate(() => window.isaacReplay.seek(4.5));
  const fragment = new URL(page.url()).hash;
  if (!fragment.includes('clip=1') || !fragment.includes('t=4.500'))
    throw new Error('Selected clip/time absent from share fragment');
  await page.reload();
  await page.evaluate(() => window.isaacReplay.ready);
  result.restored = await page.evaluate(() => window.isaacReplay.getState());
  if (result.restored.clipIndex !== 1 || Math.abs(result.restored.time - 4.5) > 0.001)
    throw new Error('Selected clip/time did not survive reload');
  result.status = 'PASS';
} catch (error) {
  result.status = 'FAIL';
  result.failure = error.message;
  throw error;
} finally {
  fs.writeFileSync('runs/v1/multiclip-browser.json', JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
  await browser.close();
}
