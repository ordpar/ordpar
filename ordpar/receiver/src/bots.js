// Two of the six layers against bots (site decisions 104), both decided here on the Worker, with
// no third party asked:
//   (2) the browser name (User-Agent) against a kept copy of a public crawler list —
//       monperrus/crawler-user-agents, MIT (data/crawlers.json, data/crawlers.LICENSE.txt);
//   (5) the network (request.cf.asn, given to Workers on every plan) against a kept list of
//       hosting and data-centre networks — brianhama/bad-asn-list, MIT
//       (data/datacentre-asns.json, data/datacentre-asns.LICENSE.txt).
// The address is never looked at here. `tools/refresh-lists.mjs` remakes both files.
import crawlers from '../data/crawlers.json';
import networks from '../data/datacentre-asns.json';

// one expression, compiled once per isolate; case-sensitive, as the list's patterns are written
const CRAWLER = new RegExp(crawlers.patterns.join('|'));
const ASNS = new Set(networks.asns);

/** A browser name that is a crawler's — or none at all (every browser sends one). */
export function isCrawler(ua) {
  return typeof ua !== 'string' || !ua || CRAWLER.test(ua);
}

/** A network on the data-centre list (`asn` a number; anything else is not on it). */
export function isDataCentre(asn) {
  return ASNS.has(Number(asn));
}

export const LISTS = {
  crawlers: { source: crawlers.source, commit: crawlers.commit, count: crawlers.patterns.length },
  networks: { source: networks.source, commit: networks.commit, count: networks.asns.length },
};
