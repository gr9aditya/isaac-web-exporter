import fs from 'node:fs';

const file = process.argv[2];
const data = fs.readFileSync(file);
if (data.toString('ascii', 0, 4) !== 'glTF') throw new Error('Not a GLB');
const length = data.readUInt32LE(12);
const type = data.toString('ascii', 16, 20);
if (type !== 'JSON') throw new Error('GLB JSON chunk missing');
const gltf = JSON.parse(data.toString('utf8', 20, 20 + length));
const result = {
  meshes: gltf.meshes?.length || 0,
  nodes: gltf.nodes?.map(n => n.name || 'unnamed') || [],
  materials: gltf.materials?.length || 0,
  animations: gltf.animations?.map(a => ({
    name: a.name,
    channels: a.channels?.map(c => ({ node: gltf.nodes[c.target.node]?.name, path: c.target.path })),
  })) || [],
  cameras: gltf.cameras?.length || 0,
};
console.log(JSON.stringify(result, null, 2));
if (result.meshes < 2) throw new Error('Expected both floor and falling box meshes');
if (!result.animations.length || !result.animations.some(a => a.channels?.some(c => c.path === 'translation'))) {
  throw new Error('GLB has no animated translation');
}
