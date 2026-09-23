import { chromium } from '../web/player/node_modules/playwright/index.mjs';
import fs from 'node:fs';

const browser = await chromium.launch({ channel: 'msedge', headless: true,
  args: ['--use-gl=angle', '--use-angle=d3d11'] });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
const result = {};
try {
  await page.goto(process.env.ACCEPT_URL || 'http://127.0.0.1:8003/v1-final-guided/package/');
  await page.evaluate(() => window.isaacReplay.ready);
  await page.getByRole('button', { name: 'Guided demo' }).click();
  await page.evaluate(() => window.isaacReplay.seek(15));
  result.middle = { title: await page.locator('#tour-title').innerText(),
    label: await page.locator('#anchor-label').innerText(),
    left: await page.locator('#anchor-label').evaluate(element => element.style.left) };
  await page.evaluate(() => window.isaacReplay.seek(18));
  await page.waitForFunction(previous =>
    document.querySelector('#anchor-label').style.left !== previous,
    result.middle.left);
  result.moved = { label: await page.locator('#anchor-label').innerText(),
    left: await page.locator('#anchor-label').evaluate(element => element.style.left) };
  if (result.middle.label !== 'Inspected part' || result.middle.left === result.moved.left)
    throw new Error('Moving-object label did not follow its object');
  await page.evaluate(() => window.isaacReplay.seek(22));
  result.transfer = { title: await page.locator('#tour-title').innerText(),
    selected: await page.evaluate(() => window.isaacReplay.getState().selectedId) };
  if (result.transfer.title !== 'Transfer' || !result.transfer.selected.endsWith('/Gripper'))
    throw new Error('Seeking did not reconstruct transfer chapter');
  await page.getByRole('button', { name: 'Restart' }).click();
  result.restartTitle = await page.locator('#tour-title').innerText();
  if (result.restartTitle !== 'Parts arrive') throw new Error('Restart retained stale chapter');
  await page.getByRole('button', { name: 'Pause' }).click();
  await page.locator('#loop').check();
  await page.evaluate(() => window.isaacReplay.seek(29.95));
  await page.getByRole('button', { name: 'Start', exact: true }).click();
  await page.waitForTimeout(180);
  result.loopTitle = await page.locator('#tour-title').innerText();
  if (result.loopTitle !== 'Parts arrive') throw new Error('Loop retained stale result chapter');
  await page.getByRole('button', { name: 'Pause' }).click();
  await page.locator('#tour-editor').evaluate(element => { element.open = true; });
  await page.locator('#chapter-time').fill('5');
  await page.locator('#chapter-title-input').fill('Transition check');
  await page.locator('#chapter-caption-input').fill('Camera moves over one second.');
  await page.locator('#chapter-use-camera').check();
  await page.locator('#chapter-transition').fill('1');
  await page.getByRole('button', { name: 'Add chapter' }).click();
  result.transition = await page.evaluate(() => window.isaacReplay.getExperience()
    .chapters.find(chapter => chapter.title === 'Transition check')?.transitionSeconds);
  if (result.transition !== 1) throw new Error('Camera transition was not saved');
  await page.evaluate(() => {
    window.isaacReplay.seek(0);
    window.isaacReplay.setExperience({ schemaVersion: 'v1.0', chapters: [
      { id: 'a', startSeconds: 0, title: 'A', caption: '',
        camera: { position: [7, 6, 9], target: [0, 0, 0] } },
      { id: 'b', startSeconds: 5, title: 'B', caption: '',
        camera: { position: [2, 3, 5], target: [1, 0, 0] }, transitionSeconds: 1 },
    ] });
    window.isaacReplay.seek(5);
  });
  const cameraX = () => page.evaluate(() => window.__checkpoint.camera.position.x);
  const firstX = await cameraX();
  await page.waitForTimeout(300);
  const middleX = await cameraX();
  await page.waitForTimeout(900);
  const lastX = await cameraX();
  result.cameraTransition = { firstX, middleX, lastX };
  if (!(firstX > middleX && middleX > lastX && Math.abs(lastX - 2) < 0.02))
    throw new Error('Camera did not transition over time');
  result.status = 'PASS';
} catch (error) {
  result.status = 'FAIL'; result.failure = error.message; throw error;
} finally {
  fs.writeFileSync('runs/v1/guided-state-browser.json', JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
  await browser.close();
}
