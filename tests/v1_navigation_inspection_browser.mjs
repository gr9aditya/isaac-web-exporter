import { chromium } from '../web/player/node_modules/playwright/index.mjs';
import fs from 'node:fs';

const browser = await chromium.launch({ channel: 'msedge', headless: true,
  args: ['--use-gl=angle', '--use-angle=d3d11'] });
const result = {};
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await page.goto(process.env.GUIDED_URL || 'http://127.0.0.1:8003/v1-final-guided/package/');
  await page.evaluate(() => window.isaacReplay.ready);
  await page.getByRole('button', { name: 'Info' }).click();
  result.compatibilityVisible = await page.locator('#compatibility').isVisible();
  if (!result.compatibilityVisible || !(await page.locator('#compatibility').innerText()).includes('success'))
    throw new Error('Compatibility information was not readable');
  const camera = () => page.evaluate(() => ({
    position: window.__checkpoint.camera.position.toArray(),
    target: window.__checkpoint.orbit.target.toArray(),
  }));
  result.overview = await camera();
  await page.getByRole('combobox', { name: 'Camera bookmark' }).selectOption('1');
  result.inspectionView = await camera();
  if (JSON.stringify(result.overview) === JSON.stringify(result.inspectionView))
    throw new Error('Camera bookmark did not change view');
  await page.locator('#object-search').fill('PartA');
  result.filtered = await page.locator('.object-row').allTextContents();
  if (result.filtered.length !== 1 || result.filtered[0] !== 'PartA')
    throw new Error('Object search did not narrow catalog');
  await page.locator('.object-row').click();
  if ((await page.evaluate(() => window.isaacReplay.getState())).selectedId !== '/World/Products/PartA')
    throw new Error('Object catalog click selected wrong object');
  await page.getByRole('button', { name: 'Focus' }).click();
  result.focusView = await camera();
  if (JSON.stringify(result.focusView.target) === JSON.stringify(result.inspectionView.target))
    throw new Error('Focus did not move camera target');
  await page.getByRole('button', { name: 'Isolate' }).click();
  const isolated = await page.evaluate(() => {
    let visible = 0; window.__checkpoint.loaded.traverse(node => { if (node.isMesh && node.visible) visible++; });
    return visible;
  });
  await page.getByRole('button', { name: 'Show all' }).click();
  const all = await page.evaluate(() => {
    let visible = 0; window.__checkpoint.loaded.traverse(node => { if (node.isMesh && node.visible) visible++; });
    return visible;
  });
  result.visibility = { isolated, all };
  if (!(isolated > 0 && isolated < all)) throw new Error('Isolate/show-all did not change visibility');
  await page.getByRole('button', { name: 'Clear' }).click();
  if ((await page.evaluate(() => window.isaacReplay.getState())).selectedId)
    throw new Error('Clear selection failed');
  await page.close();

  const clickPage = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await clickPage.goto(process.env.BOX_URL || 'http://127.0.0.1:8003/v1-final-box/package/');
  await clickPage.evaluate(() => window.isaacReplay.ready);
  const point = await clickPage.evaluate(() => {
    const root = window.__checkpoint.loaded;
    let box;
    root.traverse(node => { if (node.userData?.isaacObjectId === '/World/FallingBox') box = node; });
    root.updateMatrixWorld(true);
    const world = box.getWorldPosition(box.position.clone());
    const screen = world.project(window.__checkpoint.camera);
    const rect = document.querySelector('#canvas canvas').getBoundingClientRect();
    return { x: rect.left + (screen.x + 1) * rect.width / 2,
      y: rect.top + (1 - screen.y) * rect.height / 2 };
  });
  await clickPage.mouse.click(point.x, point.y);
  result.canvasSelected = (await clickPage.evaluate(() => window.isaacReplay.getState())).selectedId;
  if (result.canvasSelected !== '/World/FallingBox')
    throw new Error(`Canvas click selected ${result.canvasSelected}`);
  result.status = 'PASS';
  await clickPage.close();
} catch (error) {
  result.status = 'FAIL'; result.failure = error.message; throw error;
} finally {
  fs.writeFileSync('runs/v1/navigation-inspection-browser.json', JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
  await browser.close();
}
