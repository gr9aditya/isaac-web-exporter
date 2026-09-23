import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { activeChapter, validateExperience } from './experience.js';
import './style.css';

const $ = id => document.getElementById(id);
const ui = Object.fromEntries([
  'canvas', 'status', 'time', 'start', 'pause', 'restart', 'step-back',
  'step-forward', 'speed', 'loop', 'clip-select', 'seek', 'reset-view',
  'camera-bookmark', 'object-search', 'object-list', 'object-count',
  'focus-object', 'isolate-object', 'clear-selection', 'selection-detail',
  'compatibility', 'info-toggle', 'mode-toggle', 'tour-banner', 'tour-title',
  'tour-caption', 'anchor-label', 'chapter-list', 'chapter-time',
  'chapter-title-input', 'chapter-caption-input', 'chapter-object',
  'chapter-label', 'chapter-use-camera', 'chapter-transition', 'add-chapter', 'download-tour',
  'import-tour', 'tour-error',
].map(id => [id, $(id)]));

const scene = new THREE.Scene();
scene.background = new THREE.Color('#182333');
const camera = new THREE.PerspectiveCamera(50, 1, 0.01, 1000);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
ui.canvas.appendChild(renderer.domElement);
const orbit = new OrbitControls(camera, renderer.domElement);
orbit.enableDamping = true;
scene.add(new THREE.HemisphereLight(0xffffff, 0x8899bb, 2.5));
const sun = new THREE.DirectionalLight(0xffffff, 2.5);
sun.position.set(3, 5, 7);
scene.add(sun);

let resolveReady;
let rejectReady;
const ready = new Promise((resolve, reject) => {
  resolveReady = resolve;
  rejectReady = reject;
});
const state = {
  loaded: null, clips: [], clip: null, clipIndex: -1, mixer: null,
  playing: false, playhead: 0, speed: 1, loop: false, sampleTimes: [],
  catalog: [], selected: null, selectionHelpers: [], isolated: false,
  savedVisibility: new Map(), initialCamera: null, bookmarks: [],
  manifest: {}, compatibility: {},
  experience: { schemaVersion: 'v1.0', chapters: [] },
  guided: false, activeChapterId: null,
  cameraTransition: null,
};
const clock = new THREE.Clock();
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();

function asset(name) {
  if (typeof name !== 'string' || !name || name.startsWith('/') ||
      name.includes('\\') || name.split('/').includes('..') ||
      /^[a-z][a-z0-9+.-]*:/i.test(name))
    throw new Error(`Unsafe package resource: ${name}`);
  return `${import.meta.env.BASE_URL}${name}`;
}
async function json(name, fallback) {
  const response = await fetch(asset(name));
  if (!response.ok) {
    if (fallback !== undefined) return fallback;
    throw new Error(`${name}: HTTP ${response.status}`);
  }
  return response.json();
}

function resize() {
  const width = Math.max(1, ui.canvas.clientWidth);
  const height = Math.max(1, ui.canvas.clientHeight);
  renderer.setSize(width, height);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(ui.canvas);

function frameObject(object, preset) {
  object.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(object);
  const center = box.getCenter(new THREE.Vector3());
  const size = Math.max(box.getSize(new THREE.Vector3()).length(), 1);
  if (preset?.position && preset?.target) {
    orbit.target.fromArray(preset.target);
    camera.position.fromArray(preset.position);
  } else {
    orbit.target.copy(center);
    camera.position.copy(center).add(new THREE.Vector3(size, size * 0.75, size));
  }
  camera.near = Math.max(size / 1000, 0.001);
  camera.far = Math.max(size * 100, 100);
  camera.updateProjectionMatrix();
  orbit.update();
}

function transitionCamera(view, seconds = 0) {
  if (!seconds) {
    state.cameraTransition = null;
    frameObject(state.loaded, view);
    return;
  }
  state.cameraTransition = {
    fromPosition: camera.position.clone(), fromTarget: orbit.target.clone(),
    toPosition: new THREE.Vector3().fromArray(view.position),
    toTarget: new THREE.Vector3().fromArray(view.target),
    started: performance.now(), durationMs: seconds * 1000,
  };
}

function focusNodes(nodes) {
  if (!nodes.length) return;
  state.loaded.updateMatrixWorld(true);
  const box = new THREE.Box3();
  for (const node of nodes) box.union(new THREE.Box3().setFromObject(node));
  if (box.isEmpty()) return;
  const target = box.getCenter(new THREE.Vector3());
  const radius = Math.max(box.getSize(new THREE.Vector3()).length(), 0.5);
  const offset = camera.position.clone().sub(orbit.target).normalize().multiplyScalar(radius * 1.7);
  orbit.target.copy(target);
  camera.position.copy(target).add(offset);
  orbit.update();
}

function resolveNodes(entry) {
  const tagged = [];
  state.loaded.traverse(node => {
    if (node.userData?.isaacObjectId === entry.id) tagged.push(node);
  });
  if (tagged.length) return tagged;
  const names = entry.nodes || (entry.node ? [entry.node] : []);
  const nodes = [];
  for (const name of names) {
    state.loaded.traverse(node => { if (node.name === name) nodes.push(node); });
  }
  return [...new Set(nodes)];
}

function updateFragment() {
  const fragment = new URLSearchParams();
  if (state.clipIndex >= 0) fragment.set('clip', String(state.clipIndex));
  if (state.clip) fragment.set('t', state.playhead.toFixed(3));
  if (state.selected) fragment.set('object', state.selected.id);
  history.replaceState(null, '', `${location.pathname}${location.search}#${fragment}`);
}

function clearHighlights() {
  for (const helper of state.selectionHelpers) {
    scene.remove(helper);
    helper.geometry.dispose();
    helper.material.dispose();
  }
  state.selectionHelpers = [];
}

function restoreVisibility() {
  for (const [mesh, visible] of state.savedVisibility) mesh.visible = visible;
  state.savedVisibility.clear();
  state.isolated = false;
  ui['isolate-object'].textContent = 'Isolate';
}

function renderCatalog() {
  const query = ui['object-search'].value.trim().toLowerCase();
  ui['object-list'].replaceChildren();
  const visible = state.catalog.filter(item => `${item.name} ${item.id}`.toLowerCase().includes(query));
  for (const item of visible) {
    const row = document.createElement('button');
    row.type = 'button';
    row.className = 'object-row';
    row.setAttribute('role', 'option');
    row.setAttribute('aria-selected', String(state.selected?.id === item.id));
    row.textContent = item.name;
    row.title = item.id;
    row.addEventListener('click', () => selectObject(item.id));
    ui['object-list'].appendChild(row);
  }
  ui['object-count'].textContent = `${visible.length} / ${state.catalog.length}`;
}

function selectObject(id) {
  const item = id ? state.catalog.find(entry => entry.id === id) : null;
  if (id && !item) throw new Error(`Unknown object: ${id}`);
  restoreVisibility();
  clearHighlights();
  state.selected = item;
  if (item) {
    for (const node of resolveNodes(item)) {
      const helper = new THREE.BoxHelper(node, 0x75caff);
      scene.add(helper);
      state.selectionHelpers.push(helper);
    }
  }
  const enabled = Boolean(item);
  for (const key of ['focus-object', 'isolate-object', 'clear-selection']) ui[key].disabled = !enabled;
  ui['selection-detail'].textContent = item ? `${item.name}\n${item.id}` : 'Select an object to inspect it.';
  renderCatalog();
  updateFragment();
}

function experienceStorageKey() {
  return `isaac-replay-experience:${state.manifest.assetSha256 || location.pathname}`;
}

function saveExperience(data) {
  validateExperience(data, state.catalog, state.clips);
  data.chapters.sort((a, b) => a.startSeconds - b.startSeconds);
  state.experience = data;
  localStorage.setItem(experienceStorageKey(), JSON.stringify(data));
  ui['tour-error'].textContent = '';
  renderChapterList();
  applyChapter(true);
}

function renderChapterList() {
  ui['chapter-list'].replaceChildren();
  const chapters = state.experience.chapters;
  for (const chapter of chapters) {
    const row = document.createElement('div');
    row.className = 'chapter-row';
    const jump = document.createElement('button');
    jump.type = 'button';
    jump.textContent = `${chapter.startSeconds.toFixed(1)}s · ${chapter.title}`;
    jump.addEventListener('click', () => {
      if (state.clips.length) selectClip(chapter.clipIndex ?? 0);
      setTime(chapter.startSeconds);
      state.guided = true;
      ui['mode-toggle'].textContent = 'Explore';
      applyChapter(true);
    });
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.textContent = '×';
    remove.setAttribute('aria-label', `Remove ${chapter.title}`);
    remove.addEventListener('click', () => saveExperience({ ...state.experience,
      chapters: chapters.filter(item => item.id !== chapter.id) }));
    row.append(jump, remove);
    ui['chapter-list'].appendChild(row);
  }
  ui['mode-toggle'].disabled = chapters.length === 0;
  if (!chapters.length) {
    state.guided = false;
    ui['mode-toggle'].textContent = 'Guided demo';
    ui['tour-banner'].hidden = true;
    ui['anchor-label'].hidden = true;
  }
}

function applyChapter(force = false) {
  if (!state.guided) {
    ui['tour-banner'].hidden = true;
    ui['anchor-label'].hidden = true;
    state.activeChapterId = null;
    return;
  }
  const chapter = activeChapter(state.experience.chapters, state.clipIndex, state.playhead);
  if (!chapter) {
    ui['tour-banner'].hidden = true;
    ui['anchor-label'].hidden = true;
    state.activeChapterId = null;
    return;
  }
  ui['tour-banner'].hidden = false;
  ui['tour-title'].textContent = chapter.title;
  ui['tour-caption'].textContent = chapter.caption;
  ui['anchor-label'].textContent = chapter.label || chapter.title;
  if (force || state.activeChapterId !== chapter.id) {
    state.activeChapterId = chapter.id;
    if (chapter.objectId) selectObject(chapter.objectId);
    if (chapter.camera) transitionCamera(chapter.camera, chapter.transitionSeconds || 0);
  }
}

function updateAnchorLabel() {
  const chapter = activeChapter(state.experience.chapters, state.clipIndex, state.playhead);
  if (!state.guided || !chapter?.objectId || !state.loaded) {
    ui['anchor-label'].hidden = true;
    return;
  }
  const object = state.catalog.find(entry => entry.id === chapter.objectId);
  const nodes = object ? resolveNodes(object) : [];
  if (!nodes.length) { ui['anchor-label'].hidden = true; return; }
  state.loaded.updateMatrixWorld(true);
  const box = new THREE.Box3();
  nodes.forEach(node => box.union(new THREE.Box3().setFromObject(node)));
  if (box.isEmpty()) { ui['anchor-label'].hidden = true; return; }
  const point = box.getCenter(new THREE.Vector3()).project(camera);
  ui['anchor-label'].hidden = point.z < -1 || point.z > 1 ||
    Math.abs(point.x) > 1 || Math.abs(point.y) > 1;
  if (!ui['anchor-label'].hidden) {
    ui['anchor-label'].style.left = `${(point.x + 1) * ui.canvas.clientWidth / 2}px`;
    ui['anchor-label'].style.top = `${(1 - point.y) * ui.canvas.clientHeight / 2}px`;
  }
}

function isolateSelection() {
  if (!state.selected) return;
  if (state.isolated) { restoreVisibility(); return; }
  const roots = resolveNodes(state.selected);
  state.loaded.traverse(node => {
    if (!node.isMesh) return;
    state.savedVisibility.set(node, node.visible);
    const inside = roots.some(root => root === node || root.getObjectById(node.id));
    node.visible = node.visible && inside;
  });
  state.isolated = true;
  ui['isolate-object'].textContent = 'Show all';
}

function setTime(seconds) {
  if (!state.clip) return;
  const value = Number(seconds);
  if (!Number.isFinite(value)) throw new Error('Playback time must be finite');
  state.playhead = THREE.MathUtils.clamp(value, 0, state.clip.duration);
  state.mixer.setTime(state.playhead);
  refreshTime();
  applyChapter();
  updateFragment();
}

function refreshTime() {
  ui.time.textContent = `${state.playhead.toFixed(2)} / ${(state.clip?.duration || 0).toFixed(2)} s`;
  ui.seek.value = String(state.playhead);
}

function selectClip(index) {
  const clip = state.clips[index];
  if (!clip) throw new Error(`Unknown clip: ${index}`);
  state.playing = false;
  state.clipIndex = index;
  state.clip = clip;
  state.mixer?.stopAllAction();
  state.mixer = new THREE.AnimationMixer(state.loaded);
  const action = state.mixer.clipAction(clip);
  action.play();
  action.setLoop(THREE.LoopOnce);
  action.clampWhenFinished = true;
  state.sampleTimes = (state.manifest.clipSampleTimes?.[index] || state.manifest.sampleTimes || [])
    .filter(value => Number.isFinite(value) && value >= 0 && value <= clip.duration)
    .sort((a, b) => a - b);
  if (!state.sampleTimes.length) {
    const fps = Number(state.manifest.fps) || 30;
    const count = Math.ceil(clip.duration * fps);
    state.sampleTimes = Array.from({ length: count + 1 }, (_, i) => Math.min(i / fps, clip.duration));
  }
  ui.seek.max = String(clip.duration);
  for (const key of ['start', 'pause', 'restart', 'step-back',
    'step-forward', 'seek']) ui[key].disabled = false;
  setTime(0);
  ui.status.textContent = `${state.clips.length} clip(s), ${clip.duration.toFixed(2)} s`;
  ui['clip-select'].value = String(index);
  updateCheckpoint();
}

function step(direction) {
  if (!state.clip) return;
  state.playing = false;
  const epsilon = 0.0001;
  const ordered = direction > 0 ? state.sampleTimes : [...state.sampleTimes].reverse();
  const next = ordered.find(t => direction > 0 ? t > state.playhead + epsilon : t < state.playhead - epsilon);
  setTime(next ?? (direction > 0 ? state.clip.duration : 0));
}

function start() {
  if (!state.clip) return;
  if (state.playhead >= state.clip.duration) setTime(0);
  state.playing = true;
}

function updateCheckpoint() {
  // Retained for the v0 browser regression harness. Applications use isaacReplay.
  window.__checkpoint = {
    loaded: state.loaded, clips: state.clips.length, clip: state.clip,
    mixer: state.mixer, camera, orbit,
  };
}

ui.start.addEventListener('click', start);
ui.pause.addEventListener('click', () => { state.playing = false; updateFragment(); });
ui.restart.addEventListener('click', () => { setTime(0); state.playing = Boolean(state.clip); });
ui['step-back'].addEventListener('click', () => step(-1));
ui['step-forward'].addEventListener('click', () => step(1));
ui.seek.addEventListener('input', () => setTime(ui.seek.value));
ui.speed.addEventListener('change', () => { state.speed = Number(ui.speed.value); });
ui.loop.addEventListener('change', () => { state.loop = ui.loop.checked; });
ui['clip-select'].addEventListener('change', () => {
  if (ui['clip-select'].value !== '') selectClip(Number(ui['clip-select'].value));
});
ui['reset-view'].addEventListener('click', () => {
  if (state.initialCamera) frameObject(state.loaded, state.initialCamera);
});
ui['camera-bookmark'].addEventListener('change', () => {
  const view = state.bookmarks[Number(ui['camera-bookmark'].value)];
  if (view) frameObject(state.loaded, view);
});
ui['object-search'].addEventListener('input', renderCatalog);
ui['focus-object'].addEventListener('click', () => focusNodes(resolveNodes(state.selected)));
ui['isolate-object'].addEventListener('click', isolateSelection);
ui['clear-selection'].addEventListener('click', () => selectObject(null));
ui['info-toggle'].addEventListener('click', () => { ui.compatibility.hidden = !ui.compatibility.hidden; });
ui['mode-toggle'].addEventListener('click', () => {
  state.guided = !state.guided;
  if (!state.guided) state.cameraTransition = null;
  ui['mode-toggle'].textContent = state.guided ? 'Explore' : 'Guided demo';
  applyChapter(true);
});
ui['add-chapter'].addEventListener('click', () => {
  try {
    const chapter = {
      id: crypto.randomUUID(),
      startSeconds: Number(ui['chapter-time'].value),
      title: ui['chapter-title-input'].value.trim(),
      caption: ui['chapter-caption-input'].value.trim(),
      clipIndex: Math.max(0, state.clipIndex),
    };
    if (ui['chapter-object'].value) chapter.objectId = ui['chapter-object'].value;
    if (ui['chapter-label'].value.trim()) chapter.label = ui['chapter-label'].value.trim();
    if (ui['chapter-use-camera'].checked) {
      chapter.camera = {
        position: camera.position.toArray(), target: orbit.target.toArray(),
      };
      chapter.transitionSeconds = Number(ui['chapter-transition'].value);
    }
    saveExperience({ ...state.experience, chapters: [...state.experience.chapters, chapter] });
  } catch (error) { ui['tour-error'].textContent = error.message; }
});
ui['download-tour'].addEventListener('click', () => {
  const data = new Blob([JSON.stringify(state.experience, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(data);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'experience.json';
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
ui['import-tour'].addEventListener('change', async () => {
  try {
    const file = ui['import-tour'].files?.[0];
    if (file) saveExperience(JSON.parse(await file.text()));
  } catch (error) { ui['tour-error'].textContent = error.message; }
  ui['import-tour'].value = '';
});

renderer.domElement.addEventListener('click', event => {
  if (!state.loaded) return;
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.set(((event.clientX - rect.left) / rect.width) * 2 - 1,
    -((event.clientY - rect.top) / rect.height) * 2 + 1);
  raycaster.setFromCamera(pointer, camera);
  const hit = raycaster.intersectObject(state.loaded, true)[0];
  if (!hit) return;
  const item = state.catalog.find(entry => resolveNodes(entry).some(root =>
    root === hit.object || root.getObjectById(hit.object.id)));
  if (item) selectObject(item.id);
});

document.addEventListener('keydown', event => {
  if (['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
  if (event.code === 'Space') {
    event.preventDefault();
    if (state.playing) state.playing = false;
    else start();
  } else if (event.code === 'ArrowRight') { event.preventDefault(); step(1); }
  else if (event.code === 'ArrowLeft') { event.preventDefault(); step(-1); }
});

window.isaacReplay = Object.freeze({
  ready,
  play: start,
  pause: () => { state.playing = false; },
  seek: setTime,
  selectObject,
  focusObject: id => {
    const item = state.catalog.find(entry => entry.id === id);
    if (!item) throw new Error(`Unknown object: ${id}`);
    focusNodes(resolveNodes(item));
  },
  setCamera: view => {
    if (!Array.isArray(view?.position) || !Array.isArray(view?.target))
      throw new Error('Camera needs position and target arrays');
    frameObject(state.loaded, view);
  },
  setExperience: saveExperience,
  getExperience: () => structuredClone(state.experience),
  getMetrics: () => ({
    drawCalls: renderer.info.render.calls,
    triangles: renderer.info.render.triangles,
    geometries: renderer.info.memory.geometries,
    textures: renderer.info.memory.textures,
  }),
  getState: () => ({
    clipIndex: state.clipIndex, time: state.playhead,
    duration: state.clip?.duration || 0, playing: state.playing,
    selectedId: state.selected?.id || null,
  }),
});

async function load() {
  try {
    const initialFragment = new URLSearchParams(location.hash.slice(1));
    const [manifest, catalog, compatibility] = await Promise.all([
      json('manifest.json'), json('scene-map.json', { objects: [] }),
      json('compatibility-report.json', {}),
    ]);
    if (!['alpha-0.1', 'v1.0'].includes(manifest.schemaVersion))
      throw new Error(`Unsupported manifest schema: ${manifest.schemaVersion}`);
    if (manifest.schemaVersion === 'v1.0' && catalog.schemaVersion !== 'v1.0')
      throw new Error(`Scene catalog schema differs from manifest`);
    state.manifest = manifest;
    state.compatibility = compatibility;
    ui.compatibility.textContent = JSON.stringify({
      status: compatibility.status || 'unknown', warnings: compatibility.warnings || [],
    }, null, 2);
    if (manifest.schemaVersion === 'v1.0' && !manifest.asset)
      throw new Error('Manifest is missing its scene asset');
    const gltf = await new GLTFLoader().loadAsync(asset(manifest.asset || 'scene.glb'), event => {
      ui.status.textContent = event.total
        ? `Loading scene ${Math.round(100 * event.loaded / event.total)}%`
        : `Loading scene · ${Math.round(event.loaded / 1024)} KB`;
    });
    state.loaded = gltf.scene;
    state.clips = gltf.animations;
    scene.add(state.loaded);
    frameObject(state.loaded, manifest.camera);
    state.initialCamera = {
      position: camera.position.toArray(), target: orbit.target.toArray(),
    };
    state.bookmarks = [state.initialCamera, ...(manifest.cameraBookmarks || [])];
    state.bookmarks.forEach((view, index) => {
      const option = document.createElement('option');
      option.value = String(index);
      option.textContent = view.name || (index ? `View ${index}` : 'Overview');
      ui['camera-bookmark'].appendChild(option);
    });
    ui['camera-bookmark'].disabled = false;
    ui['reset-view'].disabled = false;
    state.catalog = (catalog.objects || []).map(entry => ({
      id: entry.id, name: entry.displayName || entry.name || entry.node || entry.id,
      nodes: entry.nodes || (entry.node ? [entry.node] : []),
    })).filter(entry => entry.id && resolveNodes(entry).length);
    if (!state.catalog.length) {
      state.loaded.traverse(node => {
        if (node.isMesh && node.name)
          state.catalog.push({ id: node.uuid, name: node.name, nodes: [node.name] });
      });
    }
    renderCatalog();
    state.catalog.forEach(item => {
      const option = document.createElement('option');
      option.value = item.id;
      option.textContent = `${item.name} · ${item.id}`;
      ui['chapter-object'].appendChild(option);
    });
    if (state.clips.length) {
      state.clips.forEach((clip, index) => {
        const option = document.createElement('option');
        option.value = String(index);
        option.textContent = clip.name || `Clip ${index + 1}`;
        ui['clip-select'].appendChild(option);
      });
      for (const key of ['start', 'pause', 'restart', 'step-back', 'step-forward',
        'speed', 'loop', 'clip-select', 'seek']) ui[key].disabled = false;
      if (state.clips.length === 1) selectClip(0);
      else {
        const choose = document.createElement('option');
        choose.value = '';
        choose.textContent = 'Choose a clip';
        ui['clip-select'].prepend(choose);
        ui['clip-select'].value = '';
        for (const key of ['start', 'pause', 'restart', 'step-back',
          'step-forward', 'seek']) ui[key].disabled = true;
        ui.status.textContent = `${state.clips.length} clips · choose one to play`;
      }
      ui['clip-select'].disabled = state.clips.length < 2;
    } else {
      ui.status.textContent = 'Static scene ready';
      updateCheckpoint();
    }
    if (manifest.experience) {
      const packaged = await json(manifest.experience);
      const locallyEdited = localStorage.getItem(experienceStorageKey());
      try {
        state.experience = validateExperience(
          locallyEdited ? JSON.parse(locallyEdited) : packaged,
          state.catalog, state.clips);
      } catch (error) {
        state.experience = validateExperience(packaged, state.catalog, state.clips);
        ui['tour-error'].textContent = `Saved edit ignored: ${error.message}`;
      }
    }
    renderChapterList();
    const requestedClip = Number(initialFragment.get('clip'));
    if (initialFragment.has('clip')) {
      if (Number.isInteger(requestedClip) && state.clips[requestedClip]) selectClip(requestedClip);
      else ui.status.textContent = 'Share link references an invalid clip';
    }
    const requestedTime = Number(initialFragment.get('t'));
    if (state.clip && initialFragment.has('t')) {
      if (Number.isFinite(requestedTime) && requestedTime >= 0 &&
          requestedTime <= state.clip.duration) setTime(requestedTime);
      else ui.status.textContent = 'Share link references an invalid time';
    }
    const requestedId = initialFragment.get('object');
    if (requestedId) {
      if (state.catalog.some(entry => entry.id === requestedId)) selectObject(requestedId);
      else ui.status.textContent = 'Share link references an unknown object';
    }
    resolveReady(window.isaacReplay.getState());
  } catch (error) {
    ui.status.textContent = `Load failed: ${error.message || error}`;
    console.error(error);
    rejectReady(error);
  }
}

function render() {
  requestAnimationFrame(render);
  const delta = clock.getDelta();
  if (state.clip && state.playing) {
    let next = state.playhead + delta * state.speed;
    if (next >= state.clip.duration) {
      if (state.loop) next %= state.clip.duration;
      else { next = state.clip.duration; state.playing = false; updateFragment(); }
    }
    state.playhead = next;
    state.mixer.setTime(next);
    refreshTime();
    applyChapter();
  }
  for (const helper of state.selectionHelpers) helper.update();
  if (state.cameraTransition) {
    const transition = state.cameraTransition;
    const fraction = Math.min(1, (performance.now() - transition.started) / transition.durationMs);
    const eased = fraction * fraction * (3 - 2 * fraction);
    camera.position.copy(transition.fromPosition).lerp(transition.toPosition, eased);
    orbit.target.copy(transition.fromTarget).lerp(transition.toTarget, eased);
    if (fraction >= 1) state.cameraTransition = null;
  }
  orbit.update();
  updateAnchorLabel();
  renderer.render(scene, camera);
}
render();
load();
