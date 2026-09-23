import { chromium } from '../web/player/node_modules/playwright/index.mjs';
import fs from 'node:fs';

const url = process.env.PERF_URL || 'http://127.0.0.1:8002/';
const output = process.env.PERF_OUTPUT || 'runs/v1/perf.json';
const channel = process.env.PERF_CHANNEL || 'msedge';
const rendererChoice = process.env.PERF_RENDERER || 'd3d11';
const seconds = Number(process.env.PERF_SECONDS || 5);
if (!Number.isFinite(seconds) || seconds < 1) throw new Error('Invalid PERF_SECONDS');
const browser = await chromium.launch({ channel, headless: true,
  args: rendererChoice === 'swiftshader'
    ? ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader']
    : ['--use-gl=angle', '--use-angle=d3d11'] });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
const started = Date.now();
try {
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.waitForFunction(() => Boolean(window.__checkpoint?.loaded));
  const loadMs = Date.now() - started;
  if (await page.locator('#start').isEnabled()) {
    if (process.env.PERF_LOOP === '1') await page.locator('#loop').check();
    await page.getByRole('button', { name: 'Start', exact: true }).click();
  }
  const measurement = await page.evaluate(ms => new Promise(resolve => {
    const gl = document.querySelector('#canvas canvas').getContext('webgl2');
    const extension = gl?.getExtension('WEBGL_debug_renderer_info');
    const renderer = extension ? gl.getParameter(extension.UNMASKED_RENDERER_WEBGL) : 'unreported';
    const stamps = [];
    const startedAt = performance.now();
    function tick(now) {
      stamps.push(now);
      if (now - startedAt < ms) requestAnimationFrame(tick);
      else {
        const intervals = stamps.slice(1).map((t, i) => t - stamps[i]).sort((a, b) => a - b);
        const choose = q => intervals[Math.min(intervals.length - 1, Math.floor(q * intervals.length))];
        resolve({ renderer, frames: stamps.length, elapsedMs: now - startedAt,
          fps: (stamps.length - 1) / ((now - stamps[0]) / 1000),
          medianFrameMs: choose(0.5), p95FrameMs: choose(0.95),
          heapBytes: performance.memory?.usedJSHeapSize ?? null });
      }
    }
    requestAnimationFrame(tick);
  }), seconds * 1000);
  const result = { url, channel, rendererChoice, browserVersion: browser.version(),
    viewport: '1280x720', deviceScaleFactor: 1, loadMs,
    sceneMetrics: await page.evaluate(() => window.isaacReplay.getMetrics()),
    ...measurement };
  fs.writeFileSync(output, JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
} finally {
  await browser.close();
}
