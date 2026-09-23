window.addEventListener('load', async () => {
  await window.isaacReplay.ready;
  const id = '/World/Products/PartA';
  const panel = document.createElement('section');
  panel.setAttribute('aria-label', 'Custom object information');
  panel.style.cssText = 'position:absolute;right:1rem;bottom:1rem;background:#101923eb;padding:.7rem;border-radius:.3rem;max-width:14rem';
  const heading = document.createElement('strong');
  heading.textContent = 'Part A';
  const description = document.createElement('p');
  description.textContent = 'A recorded product moving from conveyor to output bin.';
  const button = document.createElement('button');
  button.textContent = 'Inspect and focus';
  button.addEventListener('click', () => {
    window.isaacReplay.selectObject(id);
    window.isaacReplay.focusObject(id);
  });
  panel.append(heading, description, button);
  document.querySelector('.viewport').append(panel);
});
