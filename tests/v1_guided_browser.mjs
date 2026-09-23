import { chromium } from '../web/player/node_modules/playwright/index.mjs';
import fs from 'node:fs';
import crypto from 'node:crypto';

const url = process.env.ACCEPT_URL || 'http://127.0.0.1:8003/from-isaac-guided/';
const origin = new URL(url).origin;
const browser = await chromium.launch({ channel: process.env.ACCEPT_CHANNEL || 'msedge', headless: true,
  args: ['--use-gl=angle', '--use-angle=d3d11'] });
const context = await browser.newContext({ viewport: { width: 1280, height: 720 },
  deviceScaleFactor: 1, acceptDownloads: true });
const page = await context.newPage();
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

const result = { url, browser: browser.version(), checks: {}, errors, external };
const output = process.env.ACCEPT_OUTPUT || 'runs/v1/guided-browser';
const packagePath = new URL(url).pathname.replace(/^\//, '').replace(/\/$/, '');
const localGlb = `runs/v1/${packagePath}/scene.glb`;
const glbHash = () => crypto.createHash('sha256').update(fs.readFileSync(localGlb)).digest('hex');
try {
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.waitForFunction(() => window.isaacReplay?.getState().duration === 30);
  result.checks.chapters = await page.locator('.chapter-row').count();
  if (result.checks.chapters < 3) throw new Error('Demo lacks three chapters');
  await page.getByRole('button', { name: 'Guided demo', exact: true }).click();
  result.checks.initialTitle = await page.locator('#tour-title').textContent();
  if (!result.checks.initialTitle || await page.locator('#tour-banner').isHidden())
    throw new Error('Guided mode did not show first chapter');
  await page.evaluate(() => window.isaacReplay.seek(15));
  result.checks.middle = {
    title: await page.locator('#tour-title').textContent(),
    selected: await page.evaluate(() => window.isaacReplay.getState().selectedId),
    label: await page.locator('#anchor-label').textContent(),
  };
  if (!result.checks.middle.title || !result.checks.middle.selected)
    throw new Error('Middle chapter did not select a moving object');
  await page.screenshot({ path: `${output}-15.png` });
  await page.getByRole('button', { name: 'Explore', exact: true }).click();
  if (!(await page.locator('#tour-banner').isHidden())) throw new Error('Explore did not hide tour');
  await page.getByRole('button', { name: 'Guided demo', exact: true }).click();
  if (await page.locator('#tour-banner').isHidden()) throw new Error('Guided resume failed');
  const originalHash = glbHash();
  await page.locator('#tour-editor').evaluate(element => { element.open = true; });
  await page.locator('#chapter-time').fill('12.25');
  await page.locator('#chapter-title-input').fill('Extra review');
  await page.locator('#chapter-caption-input').fill('A saved presentation edit.');
  await page.getByRole('button', { name: 'Add chapter' }).click();
  result.checks.editedChapters = await page.locator('.chapter-row').count();
  if (result.checks.editedChapters !== result.checks.chapters + 1)
    throw new Error('Chapter editor failed');
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForFunction(() => window.isaacReplay?.getState().duration === 30);
  result.checks.reloadedChapters = await page.locator('.chapter-row').count();
  if (result.checks.reloadedChapters !== result.checks.editedChapters)
    throw new Error('Saved chapter did not reload');
  result.checks.originalHash = originalHash;
  await page.locator('#tour-editor').evaluate(element => { element.open = true; });
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download JSON' }).click();
  const download = await downloadPromise;
  result.checks.downloadedName = download.suggestedFilename();
  result.checks.downloadedChapters = JSON.parse(fs.readFileSync(await download.path(), 'utf8')).chapters.length;
  if (result.checks.downloadedName !== 'experience.json' ||
      result.checks.downloadedChapters !== result.checks.editedChapters)
    throw new Error('Downloaded presentation JSON is wrong');
  const imported = JSON.stringify({ schemaVersion: 'v1.0', chapters: [] });
  await page.locator('#import-tour').setInputFiles({ name: 'experience.json', mimeType: 'application/json', buffer: Buffer.from(imported) });
  result.checks.importedChapters = await page.locator('.chapter-row').count();
  if (result.checks.importedChapters !== 0) throw new Error('Tour import failed');
  result.checks.glbHashAfter = glbHash();
  if (result.checks.glbHashAfter !== originalHash)
    throw new Error('Presentation edit changed the recorded GLB');
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
