import { chromium } from '../web/player/node_modules/playwright/index.mjs';
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve('runs/v1');
const source = path.join(root, process.env.CUSTOM_SOURCE || 'v1-final-guided/package');
const prefix = process.env.CUSTOM_PREFIX || 'custom';
const names = ['theme-captions', 'focused-tour', 'object-info-panel'];
const browser = await chromium.launch({ channel: 'msedge', headless: true,
  args: ['--use-gl=angle', '--use-angle=d3d11'] });
const result = { cases: {} };
try {
  for (const name of names) {
    const target = path.join(root, `${prefix}-${name}`);
    if (fs.existsSync(target)) throw new Error(`Test target already exists: ${target}`);
    fs.cpSync(source, target, { recursive: true });
    const html = path.join(target, 'index.html');
    fs.writeFileSync(html, fs.readFileSync(html, 'utf8').replace('</body>',
      `<script src="./customization/examples/${name}.js" defer></script></body>`));
    const context = await browser.newContext({ viewport: { width: 1280, height: 720 } });
    const page = await context.newPage();
    const errors = [];
    const external = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    await page.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.protocol !== 'data:' && url.origin !== 'http://127.0.0.1:8003') {
        external.push(url.href);
        await route.abort();
      } else await route.continue();
    });
    await page.goto(`http://127.0.0.1:8003/${prefix}-${name}/`);
    await page.evaluate(() => window.isaacReplay.ready);
    if (name === 'theme-captions')
      await page.getByText('Sorting cell · recorded demonstration').waitFor();
    if (name === 'focused-tour') {
      await page.waitForFunction(() => window.isaacReplay.getExperience().chapters.length === 3);
      await page.evaluate(() => window.isaacReplay.seek(21));
      if ((await page.evaluate(() => window.isaacReplay.getState())).time !== 21)
        throw new Error('Focused tour failed to seek');
    }
    if (name === 'object-info-panel') {
      await page.getByRole('button', { name: 'Inspect and focus' }).click();
      if ((await page.evaluate(() => window.isaacReplay.getState())).selectedId !==
          '/World/Products/PartA') throw new Error('Info panel failed to select');
    }
    if (errors.length || external.length) throw new Error(`${name}: browser error or external request`);
    result.cases[name] = { status: 'PASS', errors, external };
    await context.close();
  }
  result.status = 'PASS';
} catch (error) {
  result.status = 'FAIL';
  result.failure = error.message;
  throw error;
} finally {
  fs.writeFileSync(path.join(root, `${prefix}-browser.json`), JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
  await browser.close();
}
