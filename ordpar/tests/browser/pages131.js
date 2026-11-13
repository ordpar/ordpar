// Site-review decisions 131 (2026-10-25/26): the About page's new parts and the "Coming to Ordpar"
// page, as the browser gets them (the check the deploy runs on the live site after a push).
//
// `/about/#contact` opened: the section "Contact" there (`h2#contact`), scrolled to (its top within
// the window's first third, or the page scrolled to its end with it in view), its `mailto:` link; the deck's paragraph under "Thanks" with its two
// AnkiWeb links and the deck's name in italics; the link to `/coming/` at the end of "How far it has
// come". `/coming/` opened: its status, title, heading, the six items with their "Waiting for:"
// lines, no `noindex`, its canonical; and no footer link to either new part on either page.
//
// args: {}   Result: { base, about: {...}, coming: {...} }
import { open, base, run, done, sleep } from './cdp.js';

run(async () => {
  const p = await open({ w: 1280, h: 800 });
  await p.goto(base + '/about/#contact', 600);
  await sleep(300);
  const about = await p.eval(`(() => {
    const h = document.getElementById('contact'), r = h ? h.getBoundingClientRect() : null;
    const mail = h && h.nextElementSibling ? h.nextElementSibling.querySelector('a[href^="mailto:"]') : null;
    const paras = [...document.querySelectorAll('.ordpar-about p')];
    const deck = paras.find(x => x.textContent.startsWith("The same list, blended with how often"));
    const far = document.getElementById('how-far-it-has-come');
    const farP = far ? far.nextElementSibling : null;
    const coming = farP ? farP.querySelector('a[href="https://ordpar.no/coming/"]') : null;
    const foot = document.querySelector('footer') ? document.querySelector('footer').innerHTML : '';
    return { contact: h ? h.textContent : null, last: h ? !h.nextElementSibling.nextElementSibling : null,
      top: r ? r.top : null, vh: innerHeight, y: scrollY,
      ymax: document.documentElement.scrollHeight - innerHeight,
      mail: mail ? { href: mail.getAttribute('href'), text: mail.textContent } : null,
      contactText: h && h.nextElementSibling ? h.nextElementSibling.textContent : null,
      deck: deck ? deck.textContent : null, deckEm: deck && deck.querySelector('em') ? deck.querySelector('em').textContent : null,
      deckLinks: deck ? [...deck.querySelectorAll('a')].map(a => [a.textContent, a.getAttribute('href')]) : [],
      coming: coming ? coming.textContent : null, farEnds: farP ? farP.textContent.slice(-60) : null,
      footContact: foot.includes('#contact'), footComing: foot.includes('/coming/') }; })()`);
  const st = await p.eval(`fetch('/coming/').then(r => r.status)`);
  await p.goto(base + '/coming/', 400);
  const coming = await p.eval(`(() => {
    // the list of what is coming: the first list; "Built" (decisions 148) is its own list after #built
    const first = document.querySelector('.ordpar-about > ul');   // not the tabs' list (site decisions 176)
    const items = first ? [...first.querySelectorAll('li')] : [];
    const builtHead = document.getElementById('built');
    const builtList = builtHead ? builtHead.nextElementSibling && builtHead.nextElementSibling.nextElementSibling : null;
    const built = builtList && builtList.tagName === 'UL'
      ? [...builtList.querySelectorAll('li > strong')].map(s => s.textContent) : [];
    const foot = document.querySelector('footer') ? document.querySelector('footer').innerHTML : '';
    const canon = document.querySelector('link[rel=canonical]');
    return { title: document.title, h1: (document.querySelector('.ordpar-about h1') || {}).textContent || null,
      intro: (document.querySelector('.ordpar-about > p') || {}).textContent || null,   // after the tabs (176)
      items: items.map(li => ({ name: (li.querySelector('strong') || {}).textContent || null,
        waiting: ([...li.querySelectorAll('em')].map(e => e.textContent).find(t => /^Waiting for/.test(t)) || null), text: li.textContent })),
      noindex: !!document.querySelector('meta[name=robots][content*=noindex]'),
      canonical: canon ? canon.getAttribute('href') : null,
      built: built, footComing: foot.includes('/coming/') }; })()`);
  coming.status = st;
  await done({ base, about, coming });
});
