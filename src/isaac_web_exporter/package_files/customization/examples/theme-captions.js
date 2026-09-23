window.addEventListener('load', async () => {
  await window.isaacReplay.ready;
  const style = document.createElement('style');
  style.textContent = ':root{--accent:#f8c653}button:focus-visible{outline-color:var(--accent)!important}.masthead{border-bottom-color:var(--accent)!important}';
  document.head.append(style);
  const caption = document.createElement('p');
  caption.textContent = 'Sorting cell · recorded demonstration';
  caption.style.cssText = 'position:absolute;right:1rem;top:1rem;background:#182333dd;padding:.5rem;border-radius:.3rem;pointer-events:none';
  document.querySelector('.viewport').append(caption);
});
