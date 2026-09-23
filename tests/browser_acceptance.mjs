import { chromium } from '../checkpoint1/web/node_modules/playwright/index.mjs';
import fs from 'node:fs';

const url = process.env.ACCEPT_URL;
const objectName = process.env.ACCEPT_OBJECT;
const channel = process.env.ACCEPT_CHANNEL || 'msedge';
const output = process.env.ACCEPT_OUTPUT;
if (!url || !objectName || !output) throw new Error('Set ACCEPT_URL, ACCEPT_OBJECT and ACCEPT_OUTPUT');
const origin = new URL(url).origin;
const browser = await chromium.launch({channel,headless:true,
  args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page = await browser.newPage({viewport:{width:1280,height:800}});
const errors=[];
const external=[];
page.on('pageerror',e=>errors.push(e.message));
page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
await page.route('**/*',async route=>{
  const requestUrl=new URL(route.request().url());
  if(requestUrl.protocol!=='data:' && requestUrl.origin!==origin){
    external.push(requestUrl.href);
    await route.abort();
  } else await route.continue();
});
const start=Date.now();
try {
  await page.goto(url,{waitUntil:'networkidle'});
  await page.waitForFunction(()=>window.__checkpoint?.clips>0,{timeout:60000});
  const loadMs=Date.now()-start;
  const sample=async time=>page.evaluate(({time,objectName})=>{
    const {mixer,loaded}=window.__checkpoint;
    mixer.setTime(time);
    const node=loaded.getObjectByName(objectName);
    return {time:mixer.time,local:node?.position.toArray(),
      world:node?.getWorldPosition(node.position.clone()).toArray()};
  },{time,objectName});
  const duration=await page.evaluate(()=>window.__checkpoint.clip.duration);
  const first=await sample(0);
  const middle=await sample(duration/2);
  const last=await sample(duration);
  await sample(0);
  await page.screenshot({path:`${output}-initial.png`});
  await page.getByRole('button',{name:'Start',exact:true}).click();
  await page.waitForTimeout(650);
  await page.getByRole('button',{name:'Pause'}).click();
  const paused=await page.evaluate(()=>window.__checkpoint.mixer.time);
  await page.waitForTimeout(250);
  const pausedAgain=await page.evaluate(()=>window.__checkpoint.mixer.time);
  await page.evaluate(()=>document.getElementById('restart').addEventListener('click',()=>{
    window.__restartAtClick=window.__checkpoint.mixer.time;
  },{once:true}));
  await page.getByRole('button',{name:'Restart'}).click();
  const restarted=await page.evaluate(()=>window.__restartAtClick);
  const cameraBefore=await page.evaluate(()=>window.__checkpoint.camera.position.toArray());
  const canvas=page.locator('#canvas canvas');
  const bounds=await canvas.boundingBox();
  await page.mouse.move(bounds.x+bounds.width/2,bounds.y+bounds.height/2);
  await page.mouse.down();
  await page.mouse.move(bounds.x+bounds.width/2+100,bounds.y+bounds.height/2+40,{steps:10});
  await page.mouse.up();
  await page.waitForTimeout(100);
  const cameraAfter=await page.evaluate(()=>window.__checkpoint.camera.position.toArray());
  const targetBeforePan=await page.evaluate(()=>window.__checkpoint.orbit.target.toArray());
  await page.mouse.move(bounds.x+bounds.width/2,bounds.y+bounds.height/2);
  await page.mouse.down({button:'right'});
  await page.mouse.move(bounds.x+bounds.width/2+60,bounds.y+bounds.height/2+30,{steps:8});
  await page.mouse.up({button:'right'});
  await page.waitForTimeout(100);
  const targetAfterPan=await page.evaluate(()=>window.__checkpoint.orbit.target.toArray());
  const cameraBeforeZoom=await page.evaluate(()=>window.__checkpoint.camera.position.toArray());
  await page.mouse.wheel(0,-450);
  await page.waitForTimeout(150);
  const cameraAfterZoom=await page.evaluate(()=>window.__checkpoint.camera.position.toArray());
  const metrics=await page.evaluate(()=>({
    renderer:(()=>{const gl=document.querySelector('canvas').getContext('webgl2');const ext=gl?.getExtension('WEBGL_debug_renderer_info');return ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):'unreported'})(),
    heapBytes:performance.memory?.usedJSHeapSize??null,
    resources:performance.getEntriesByType('resource').map(item=>({name:item.name,bytes:item.transferSize,duration:item.duration})),
  }));
  await page.screenshot({path:`${output}-proof.png`});
  const result={channel,url,loadMs,duration,first,middle,last,paused,pausedAgain,restarted,
    cameraBefore,cameraAfter,targetBeforePan,targetAfterPan,cameraBeforeZoom,cameraAfterZoom,
    metrics,external,errors};
  fs.writeFileSync(`${output}.json`,JSON.stringify(result,null,2));
  console.log(JSON.stringify({channel,loadMs,duration,first,middle,last,paused,pausedAgain,restarted,
    renderer:metrics.renderer,external,errors},null,2));
  if(!first.local||!middle.local||!last.local)throw new Error(`${objectName} absent`);
  if(JSON.stringify(first.local)===JSON.stringify(last.local))throw new Error(`${objectName} did not move`);
  if(paused<0.2||Math.abs(pausedAgain-paused)>0.05||restarted>0.2)throw new Error('Playback controls failed');
  if(JSON.stringify(cameraBefore)===JSON.stringify(cameraAfter))throw new Error('Camera orbit failed');
  if(JSON.stringify(targetBeforePan)===JSON.stringify(targetAfterPan))throw new Error('Camera pan failed');
  if(JSON.stringify(cameraBeforeZoom)===JSON.stringify(cameraAfterZoom))throw new Error('Camera zoom failed');
  if(external.length||errors.length)throw new Error('External request or page error');
} finally { await browser.close(); }
