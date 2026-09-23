import { chromium } from '../web/player/node_modules/playwright/index.mjs';
import fs from 'node:fs';

const url = process.env.ACCEPT_URL || 'http://127.0.0.1:8001/';
const output = process.env.ACCEPT_OUTPUT || 'runs/v1/player-acceptance';
const origin = new URL(url).origin;
const browser = await chromium.launch({ channel: process.env.ACCEPT_CHANNEL || 'msedge', headless: true,
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
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

const near = (actual, expected, tolerance = 0.01) => Math.abs(actual - expected) <= tolerance;
const state = () => page.evaluate(() => window.isaacReplay.getState());
const result = { url, checks: {}, errors, external };
try {
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.waitForFunction(() => window.isaacReplay.getState().duration > 0, { timeout: 30000 });
  result.checks.initial = await state();
  if (result.checks.initial.playing || !near(result.checks.initial.time, 0))
    throw new Error('Initial state is not paused at zero');

  await page.getByRole('slider', { name: 'Timeline seek' }).fill('2.5');
  result.checks.seek = await state();
  if (!near(result.checks.seek.time, 2.5) || result.checks.seek.playing)
    throw new Error('Paused seek failed');

  await page.getByRole('button', { name: 'Frame ▶' }).click();
  result.checks.stepForward = await state();
  if (!(result.checks.stepForward.time > 2.5 && result.checks.stepForward.time < 2.55))
    throw new Error('Forward frame step failed');
  await page.getByRole('button', { name: '◀ Frame' }).click();
  result.checks.stepBack = await state();
  if (!near(result.checks.stepBack.time, 2.5)) throw new Error('Back frame step failed');

  await page.getByRole('combobox', { name: 'Speed' }).selectOption('2');
  await page.getByRole('button', { name: 'Start', exact: true }).click();
  await page.waitForTimeout(300);
  await page.getByRole('button', { name: 'Pause' }).click();
  result.checks.fastPlayback = await state();
  if (!result.checks.fastPlayback.time || result.checks.fastPlayback.playing ||
      result.checks.fastPlayback.time < 2.85)
    throw new Error('2x playback/pause failed');

  await page.getByRole('option', { name: 'FallingBox', exact: true }).click();
  result.checks.selected = await state();
  if (result.checks.selected.selectedId !== '/World/FallingBox')
    throw new Error('Catalog selection failed');
  await page.getByRole('button', { name: 'Isolate' }).click();
  if (!(await page.getByRole('button', { name: 'Show all' }).isVisible()))
    throw new Error('Isolate toggle failed');
  await page.getByRole('button', { name: 'Show all' }).click();
  await page.getByRole('button', { name: 'Focus' }).click();
  await page.getByRole('button', { name: 'Reset view' }).click();

  await page.getByRole('button', { name: 'Restart' }).click();
  await page.waitForTimeout(100);
  result.checks.restart = await state();
  if (!result.checks.restart.playing || result.checks.restart.time > 0.5)
    throw new Error('Restart failed');
  await page.getByRole('button', { name: 'Pause' }).click();
  const fragment = new URL(page.url()).hash;
  if (!fragment.includes('object=%2FWorld%2FFallingBox'))
    throw new Error('Share URL lacks selected object');
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForFunction(() => window.isaacReplay.getState().duration > 0);
  result.checks.restored = await state();
  if (result.checks.restored.selectedId !== '/World/FallingBox')
    throw new Error('Share URL did not restore selection');

  await page.screenshot({ path: `${output}.png` });
  if (errors.length || external.length) throw new Error('Browser errors or external requests');
  result.status = 'PASS';
} catch (error) {
  result.status = 'FAIL';
  result.failure = error.message;
  throw error;
} finally {
  fs.writeFileSync(`${output}.json`, JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
  await browser.close();
}
