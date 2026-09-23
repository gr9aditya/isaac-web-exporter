import { chromium } from '../third_party/usd-webview-eval/node_modules/playwright/index.mjs';
import fs from 'node:fs';

const browser = await chromium.launch({channel:'msedge', headless:true, args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page = await browser.newPage({viewport:{width:1280,height:800}});
const origin = 'http://127.0.0.1:4192';
const errors = [];
const external = [];
page.on('pageerror',e=>errors.push(e.message));
page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
await page.route('**/*', async route => {
  const url = new URL(route.request().url());
  if (url.protocol !== 'data:' && url.origin !== origin) {
    external.push(url.href);
    await route.abort();
  } else await route.continue();
});
const started=Date.now();
await page.goto(`${origin}/?automationManifest=/probe-manifest.json`,{waitUntil:'domcontentloaded'});
await page.waitForFunction(()=>window.__USD_WEBVIEW_AUTOMATION__?.getState().state==='ready',{timeout:90000});
const readyMs=Date.now()-started;
const states=[];
for(const code of [0,30,60]) {
  await page.evaluate(code=>window.__USD_WEBVIEW_AUTOMATION__.setTime(code),code);
  const state=await page.evaluate(()=>({status:window.__USD_WEBVIEW_AUTOMATION__.getState(),time:document.querySelector('#playbarTime')?.textContent,viewportText:document.querySelector('.viewport')?.textContent?.slice(0,150)}));
  const png=`runs/usdz-view-${code}.png`;
  await page.locator('.viewport').screenshot({path:png});
  states.push({code,state,png,bytes:fs.statSync(png).size});
}
const result={readyMs,states,errors,external};
fs.writeFileSync('runs/usdz-webview-browser.json',JSON.stringify(result,null,2));
console.log(JSON.stringify(result,null,2));
await browser.close();
if(errors.length||external.length)process.exitCode=1;
