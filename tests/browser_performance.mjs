import { chromium } from '../checkpoint1/web/node_modules/playwright/index.mjs';
import fs from 'node:fs';

const url=process.env.PERF_URL;
const output=process.env.PERF_OUTPUT;
if(!url||!output)throw new Error('Set PERF_URL and PERF_OUTPUT');
const browser=await chromium.launch({channel:'msedge',headless:true,
  args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:1280,height:800}});
const started=Date.now();
await page.goto(url,{waitUntil:'networkidle'});
await page.waitForFunction(()=>window.__checkpoint?.clips>0);
const loadMs=Date.now()-started;
await page.getByRole('button',{name:'Start',exact:true}).click();
const frame=await page.evaluate(()=>new Promise(resolve=>{
  const stamps=[];
  const begin=performance.now();
  function tick(now){
    stamps.push(now);
    if(now-begin<1500)requestAnimationFrame(tick);
    else {
      const deltas=stamps.slice(1).map((t,i)=>t-stamps[i]).sort((a,b)=>a-b);
      resolve({frames:stamps.length,elapsedMs:now-begin,
        observedFps:(stamps.length-1)/((now-stamps[0])/1000),
        medianFrameMs:deltas[Math.floor(deltas.length/2)],
        p95FrameMs:deltas[Math.floor(deltas.length*0.95)],
        heapBytes:performance.memory?.usedJSHeapSize??null});
    }
  }
  requestAnimationFrame(tick);
}));
const result={url,loadMs,...frame};
fs.writeFileSync(output,JSON.stringify(result,null,2));
console.log(JSON.stringify(result,null,2));
await browser.close();
