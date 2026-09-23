export function validateExperience(data, catalog, clips) {
  if (!data || data.schemaVersion !== 'v1.0' || !Array.isArray(data.chapters))
    throw new Error('Experience needs schemaVersion v1.0 and a chapters array');
  const ids = new Set();
  const knownObjects = new Set(catalog.map(item => item.id));
  for (const chapter of data.chapters) {
    if (typeof chapter.id !== 'string' || !chapter.id || ids.has(chapter.id))
      throw new Error('Each chapter needs a unique nonempty ID');
    ids.add(chapter.id);
    const index = chapter.clipIndex ?? 0;
    if (!Number.isInteger(index) || index < 0 || index >= Math.max(1, clips.length))
      throw new Error(`Chapter ${chapter.id} has an invalid clip index`);
    const duration = clips[index]?.duration ?? 0;
    if (!Number.isFinite(chapter.startSeconds) || chapter.startSeconds < 0 ||
        chapter.startSeconds > duration)
      throw new Error(`Chapter ${chapter.id} has a time outside the clip`);
    if (typeof chapter.title !== 'string' || !chapter.title.trim() ||
        typeof chapter.caption !== 'string')
      throw new Error(`Chapter ${chapter.id} needs title and caption text`);
    if (chapter.objectId && !knownObjects.has(chapter.objectId))
      throw new Error(`Chapter ${chapter.id} refers to unknown object ${chapter.objectId}`);
    if (chapter.camera) {
      for (const key of ['position', 'target']) {
        const values = chapter.camera[key];
        if (!Array.isArray(values) || values.length !== 3 ||
            values.some(value => !Number.isFinite(value)))
          throw new Error(`Chapter ${chapter.id} has invalid camera ${key}`);
      }
      if (chapter.transitionSeconds !== undefined &&
          (!Number.isFinite(chapter.transitionSeconds) || chapter.transitionSeconds < 0 ||
           chapter.transitionSeconds > 10))
        throw new Error(`Chapter ${chapter.id} has invalid camera transition`);
    }
  }
  return data;
}

export function activeChapter(chapters, clipIndex, time) {
  let selected = null;
  for (const chapter of chapters) {
    if ((chapter.clipIndex ?? 0) !== clipIndex || chapter.startSeconds > time) continue;
    if (!selected || chapter.startSeconds >= selected.startSeconds) selected = chapter;
  }
  return selected;
}
