import { chromium } from '../web/player/node_modules/playwright/index.mjs';
const browser = await chromium.launch({ channel: 'msedge', headless: true });
const context = await browser.newContext({ acceptDownloads: true });
const page = await context.newPage();
page.on('console', message => console.log('CONSOLE', message.type(), message.text()));
page.on('pageerror', error => console.log('ERROR', error.message));
page.on('download', download => console.log('DOWNLOAD', download.suggestedFilename()));
await page.route('**/*', async route => {
  const url = new URL(route.request().url());
  if (url.protocol !== 'data:' && url.origin !== 'http://127.0.0.1:8003') {
    console.log('ABORT', url.href); await route.abort();
  } else await route.continue();
});
await page.goto('http://127.0.0.1:8003/player-download-probe/');
await page.evaluate(() => window.isaacReplay.ready);
await page.locator('#tour-editor').evaluate(element => element.open = true);
console.log('BEFORE', await page.locator('#download-tour').evaluate(e => ({ outer:e.outerHTML, visible:getComputedStyle(e).visibility })));
await page.locator('#download-tour').click();
await page.waitForTimeout(1500);
console.log('AFTER', await page.evaluate(() => ({ links:[...document.querySelectorAll('a')].map(a=>a.href), status:document.querySelector('#status').textContent })));
await browser.close();
