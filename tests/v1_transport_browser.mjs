import { chromium } from '../web/player/node_modules/playwright/index.mjs';
import fs from 'node:fs';

const url = process.env.ACCEPT_URL || 'http://127.0.0.1:8003/v1-final-box/package/';
const browser = await chromium.launch({ channel: 'msedge', headless: true,
  args: ['--use-gl=angle', '--use-angle=d3d11'] });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
const errors = [], external = [];
page.on('pageerror', error => errors.push(error.message));
page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
await page.route('**/*', async route => {
  const requested = new URL(route.request().url());
  if (requested.protocol !== 'data:' && requested.origin !== new URL(url).origin) {
    external.push(requested.href); await route.abort();
  } else await route.continue();
});
const result = { url, checks: {}, errors, external };
const state = () => page.evaluate(() => window.isaacReplay.getState());
try {
  await page.goto(url);
  await page.evaluate(() => window.isaacReplay.ready);
  result.checks.initial = await state();
  if (result.checks.initial.playing || result.checks.initial.time !== 0)
    throw new Error('Initial pose must be paused at first frame');
  for (const speed of ['0.25', '0.5', '1', '2']) {
    await page.evaluate(() => window.isaacReplay.seek(1.25));
    await page.getByRole('combobox', { name: 'Speed' }).selectOption(speed);
    if (Math.abs((await state()).time - 1.25) > 0.001)
      throw new Error(`Speed ${speed} jumped the playhead`);
    await page.getByRole('button', { name: 'Start', exact: true }).click();
    await page.waitForTimeout(160);
    await page.getByRole('button', { name: 'Pause' }).click();
    const observed = (await state()).time;
    result.checks[`speed${speed}`] = observed;
    if (observed <= 1.25 || observed > 1.25 + Number(speed) * 0.5)
      throw new Error(`Playback speed ${speed} did not advance plausibly: ${observed}`);
  }
  await page.evaluate(() => window.isaacReplay.seek(0));
  await page.getByRole('button', { name: '◀ Frame' }).click();
  if ((await state()).time !== 0) throw new Error('Backward step crossed first frame');
  await page.evaluate(() => window.isaacReplay.seek(5));
  await page.getByRole('button', { name: 'Frame ▶' }).click();
  if ((await state()).time !== 5) throw new Error('Forward step crossed last frame');
  await page.getByRole('combobox', { name: 'Speed' }).selectOption('1');
  await page.evaluate(() => window.isaacReplay.seek(4.95));
  await page.getByRole('button', { name: 'Start', exact: true }).click();
  await page.waitForTimeout(200);
  result.checks.end = await state();
  if (result.checks.end.playing || result.checks.end.time !== 5)
    throw new Error('No-loop playback did not stop at last frame');
  await page.getByRole('button', { name: 'Start', exact: true }).click();
  await page.waitForTimeout(100);
  result.checks.startAfterEnd = await state();
  if (!result.checks.startAfterEnd.playing || result.checks.startAfterEnd.time >= 1)
    throw new Error('Start at end did not restart from first frame');
  await page.getByRole('button', { name: 'Pause' }).click();
  await page.locator('#loop').check();
  await page.evaluate(() => window.isaacReplay.seek(4.95));
  await page.getByRole('button', { name: 'Start', exact: true }).click();
  await page.waitForTimeout(180);
  result.checks.loop = await state();
  if (!result.checks.loop.playing || result.checks.loop.time >= 1)
    throw new Error('Loop did not wrap to first frame');
  await page.getByRole('button', { name: 'Pause' }).click();
  const cameraBefore = await page.evaluate(() => window.__checkpoint.camera.position.toArray());
  await page.locator('#canvas canvas').hover();
  await page.mouse.wheel(0, -300);
  await page.waitForTimeout(100);
  const cameraMoved = await page.evaluate(() => window.__checkpoint.camera.position.toArray());
  if (JSON.stringify(cameraBefore) === JSON.stringify(cameraMoved))
    throw new Error('Camera zoom did not move');
  await page.getByRole('button', { name: 'Restart' }).click();
  const cameraAfterRestart = await page.evaluate(() => window.__checkpoint.camera.position.toArray());
  if (cameraMoved.some((value, i) => Math.abs(value - cameraAfterRestart[i]) > 0.01))
    throw new Error('Restart unexpectedly reset camera');
  await page.getByRole('button', { name: 'Reset view' }).click();
  const cameraReset = await page.evaluate(() => window.__checkpoint.camera.position.toArray());
  if (cameraReset.some((value, i) => Math.abs(value - cameraBefore[i]) > 0.01))
    throw new Error('Reset view did not restore original camera');
  await page.getByRole('button', { name: 'Pause' }).click();
  await page.goto(`${url}#clip=bogus&t=NaN&object=%2FWorld%2FAbsent`);
  await page.reload();
  await page.evaluate(() => window.isaacReplay.ready);
  result.checks.malformedLinkStatus = await page.locator('#status').innerText();
  if (!result.checks.malformedLinkStatus.includes('unknown object') ||
      (await state()).selectedId !== null)
    throw new Error('Malformed share link did not fail safely');
  if (errors.length || external.length) throw new Error('Browser error or external request');
  result.status = 'PASS';
} catch (error) {
  result.status = 'FAIL'; result.failure = error.message; throw error;
} finally {
  fs.writeFileSync('runs/v1/transport-browser.json', JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
  await browser.close();
}
