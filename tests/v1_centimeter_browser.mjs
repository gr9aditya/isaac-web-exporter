import { chromium } from '../web/player/node_modules/playwright/index.mjs';
import fs from 'node:fs';

const browser = await chromium.launch({ channel: 'msedge', headless: true,
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage();
const result = { url: process.env.ACCEPT_URL || 'http://127.0.0.1:8003/from-isaac-centimeter/', samples: [] };
try {
  await page.goto(result.url);
  await page.waitForFunction(() => window.__checkpoint?.loaded);
  for (const seconds of [0, 1, 2]) {
    const observed = await page.evaluate(seconds => {
      window.isaacReplay.seek(seconds);
      const root = window.__checkpoint.loaded;
      root.updateMatrixWorld(true);
      const nodes = {};
      root.traverse(node => {
        const id = node.userData?.isaacObjectId;
        if (id === '/World/Cell/Shoulder' || id === '/World/Cell/Shoulder/Tool')
          nodes[id] = node.matrixWorld.toArray();
      });
      return nodes;
    }, seconds);
    const shoulder = observed['/World/Cell/Shoulder'];
    const tool = observed['/World/Cell/Shoulder/Tool'];
    if (!shoulder || !tool) throw new Error('Nested moving node missing');
    const shoulderAngle = (20 + 30 * seconds) * Math.PI / 180;
    const toolAngle = (20 + 15 * seconds) * Math.PI / 180;
    const expectedToolX = 0.5 + 0.8 * Math.cos(shoulderAngle);
    const expectedToolZ = -0.35 - 0.8 * Math.sin(shoulderAngle);
    const comparisons = {
      shoulderPosition: Math.hypot(shoulder[12] - 0.5, shoulder[13] - 0.85, shoulder[14] + 0.35),
      shoulderRotation: Math.abs(Math.atan2(-shoulder[2], shoulder[0]) - shoulderAngle),
      toolPosition: Math.hypot(tool[12] - expectedToolX, tool[13] - 0.85, tool[14] - expectedToolZ),
      toolRotation: Math.abs(Math.atan2(-tool[2], tool[0]) - toolAngle),
    };
    result.samples.push({ seconds, comparisons });
    if (comparisons.shoulderPosition > 0.001 || comparisons.toolPosition > 0.001 ||
        comparisons.shoulderRotation > Math.PI / 180 * 0.1 ||
        comparisons.toolRotation > Math.PI / 180 * 0.1)
      throw new Error(`Unit/up-axis/nested transform mismatch: ${JSON.stringify(comparisons)}`);
  }
  result.status = 'PASS';
} catch (error) {
  result.status = 'FAIL';
  result.failure = error.message;
  throw error;
} finally {
  fs.writeFileSync('runs/v1/centimeter-browser.json', JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
  await browser.close();
}
