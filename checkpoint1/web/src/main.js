import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import './style.css';

const canvas = document.getElementById('canvas');
const status = document.getElementById('status');
const time = document.getElementById('time');
const start = document.getElementById('start');
const pause = document.getElementById('pause');
const restart = document.getElementById('restart');

const scene = new THREE.Scene();
scene.background = new THREE.Color('#182333');
const camera = new THREE.PerspectiveCamera(50, 1, 0.01, 1000);
// The converter maps Isaac's Z-up stage into glTF's Y-up scene.
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
canvas.appendChild(renderer.domElement);
const orbit = new OrbitControls(camera, renderer.domElement);
orbit.enableDamping = true;
scene.add(new THREE.HemisphereLight(0xffffff, 0x8899bb, 2.5));
const sun = new THREE.DirectionalLight(0xffffff, 2.5);
sun.position.set(3, 5, 7);
scene.add(sun);

let mixer;
let clip;
let playing = false;
let loaded;
const clock = new THREE.Clock();

function frameObject(object, preset) {
  object.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(object);
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3()).length();
  if (preset?.position && preset?.target) {
    orbit.target.fromArray(preset.target);
    camera.position.fromArray(preset.position);
    camera.near = 0.01;
    camera.far = Math.max(size * 100, 100);
    camera.updateProjectionMatrix();
    orbit.update();
    return;
  }
  orbit.target.copy(center);
  camera.position.copy(center).add(new THREE.Vector3(size, size * 0.75, size));
  camera.near = Math.max(size / 1000, 0.001);
  camera.far = Math.max(size * 100, 100);
  camera.updateProjectionMatrix();
  orbit.update();
}

function resize() {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  renderer.setSize(width, height);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(canvas);

start.addEventListener('click', () => {
  if (!mixer) return;
  if (mixer.time >= clip.duration) mixer.setTime(0);
  playing = true;
});
pause.addEventListener('click', () => { playing = false; });
restart.addEventListener('click', () => {
  if (!mixer) return;
  mixer.setTime(0);
  playing = true;
});

const manifestPromise = fetch(`${import.meta.env.BASE_URL}manifest.json`)
  .then(response => response.ok ? response.json() : {})
  .catch(() => ({}));

new GLTFLoader().load(`${import.meta.env.BASE_URL}scene.glb`, async gltf => {
  loaded = gltf.scene;
  scene.add(loaded);
  frameObject(loaded, (await manifestPromise).camera);
  if (!gltf.animations.length) {
    status.textContent = 'Scene loaded; no animation found';
    window.__checkpoint = { loaded, clips: 0, camera, orbit };
    return;
  }
  clip = gltf.animations[0];
  mixer = new THREE.AnimationMixer(loaded);
  const action = mixer.clipAction(clip);
  action.play();
  action.setLoop(THREE.LoopOnce);
  action.clampWhenFinished = true;
  mixer.setTime(0);
  status.textContent = `${gltf.animations.length} clip(s), ${clip.duration.toFixed(2)} s`;
  start.disabled = pause.disabled = restart.disabled = false;
  window.__checkpoint = { loaded, clips: gltf.animations.length, clip, mixer, camera, orbit };
}, undefined, error => {
  status.textContent = `Load failed: ${error.message || error}`;
  console.error(error);
});

function render() {
  requestAnimationFrame(render);
  const delta = clock.getDelta();
  if (mixer && playing) {
    mixer.update(delta);
    if (mixer.time >= clip.duration) playing = false;
  }
  time.textContent = `${mixer?.time.toFixed(2) || '0.00'} s`;
  orbit.update();
  renderer.render(scene, camera);
}
render();
