import { chromium } from '../web/player/node_modules/playwright/index.mjs';
import fs from 'node:fs';

const base = process.env.ACCEPT_BASE || 'http://127.0.0.1:8003/';
const browser = await chromium.launch({ channel: process.env.ACCEPT_CHANNEL || 'msedge', headless: true,
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const result = { base, cases: {} };

async function openCase(name, path) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = [];
  const external = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  const origin = new URL(base).origin;
  await page.route('**/*', async route => {
    const requested = new URL(route.request().url());
    if (requested.protocol !== 'data:' && requested.origin !== origin) {
      external.push(requested.href);
      await route.abort();
    } else await route.continue();
  });
  await page.goto(new URL(path, base).href, { waitUntil: 'networkidle' });
  await page.waitForFunction(() => Boolean(window.__checkpoint?.loaded));
  result.cases[name] = { errors, external };
  return page;
}

try {
  const staticPage = await openCase('static', process.env.STATIC_PACKAGE || 'from-isaac-static/');
  const staticCase = result.cases.static;
  staticCase.state = await staticPage.evaluate(() => window.isaacReplay.getState());
  staticCase.status = await staticPage.locator('#status').innerText();
  staticCase.objects = await staticPage.getByRole('option').allTextContents();
  staticCase.startDisabled = await staticPage.locator('#start').isEnabled() === false;
  if (staticCase.state.duration !== 0 || !staticCase.status.includes('Static scene') ||
      !staticCase.startDisabled || !staticCase.objects.includes('Part') ||
      staticCase.errors.length || staticCase.external.length)
    throw new Error(`Static browser package failed: ${JSON.stringify(staticCase)}`);
  await staticPage.screenshot({ path: 'runs/v1/static-browser.png' });
  await staticPage.close();

  const twinPage = await openCase('twins', process.env.TWIN_PACKAGE || 'from-isaac-twins/');
  const twins = result.cases.twins;
  twins.options = await twinPage.getByRole('option', { name: 'Arm', exact: true }).count();
  if (twins.options !== 2) throw new Error(`Expected two Arm options, got ${twins.options}`);
  twins.ids = [];
  for (let index = 0; index < 2; index++) {
    await twinPage.getByRole('option', { name: 'Arm', exact: true }).nth(index).click();
    twins.ids.push((await twinPage.evaluate(() => window.isaacReplay.getState())).selectedId);
  }
  twins.tagged = await twinPage.evaluate(() => {
    const result = [];
    window.__checkpoint.loaded.traverse(node => {
      if (node.userData.isaacObjectId?.endsWith('/Arm'))
        result.push({ name: node.name, id: node.userData.isaacObjectId });
    });
    return result;
  });
  if (new Set(twins.ids).size !== 2 ||
      new Set(twins.tagged.map(item => item.id)).size !== 2 ||
      !twins.ids.includes('/World/Left/Arm') || !twins.ids.includes('/World/Right/Arm') ||
      twins.errors.length || twins.external.length)
    throw new Error(`Twin identity failed: ${JSON.stringify(twins)}`);
  await twinPage.screenshot({ path: 'runs/v1/twins-browser.png' });
  await twinPage.close();
  result.status = 'PASS';
} catch (error) {
  result.status = 'FAIL';
  result.failure = error.message;
  throw error;
} finally {
  fs.writeFileSync('runs/v1/modes-identity-browser.json', JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
  await browser.close();
}
