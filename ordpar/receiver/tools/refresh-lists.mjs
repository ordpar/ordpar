// Remakes the two kept lists in ../data/ from their upstream files (site decisions 104, layers 2
// and 5). Run by hand, with the files downloaded first (no network here):
//
//   curl -o /tmp/crawlers.json https://raw.githubusercontent.com/monperrus/crawler-user-agents/master/crawler-user-agents.json
//   curl -o /tmp/asns.csv https://raw.githubusercontent.com/brianhama/bad-asn-list/master/bad-asn-list.csv
//   bun tools/refresh-lists.mjs /tmp/crawlers.json <commit> /tmp/asns.csv <commit>
//
// <commit> is the upstream commit the file came from, recorded in the kept file. Then run the
// tests (`python ordpar/tests/test_ordpar_receiver104.py`): a pattern that matches an ordinary
// browser fails them.
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const [crawlersPath, crawlersCommit, asnPath, asnCommit] = process.argv.slice(2);
if (!asnCommit) { console.error('usage: refresh-lists.mjs CRAWLERS.json COMMIT ASNS.csv COMMIT'); process.exit(2); }
const data = join(dirname(fileURLToPath(import.meta.url)), '..', 'data');

const crawlers = JSON.parse(readFileSync(crawlersPath, 'utf8'));
const patterns = crawlers.map((c) => c.pattern);
patterns.forEach((p) => new RegExp(p));            // throws on a pattern JavaScript cannot read
writeFileSync(join(data, 'crawlers.json'), JSON.stringify({
  source: 'https://github.com/monperrus/crawler-user-agents (crawler-user-agents.json)',
  commit: crawlersCommit,
  licence: 'MIT, Copyright (c) 2017 Martin Monperrus — see crawlers.LICENSE.txt',
  patterns,
}, null, 0) + '\n');

const asns = readFileSync(asnPath, 'utf8').split(/\r?\n/).slice(1)
  .map((line) => parseInt(line.split(',')[0], 10)).filter((n) => Number.isInteger(n) && n > 0);
writeFileSync(join(data, 'datacentre-asns.json'), JSON.stringify({
  source: 'https://github.com/brianhama/bad-asn-list (bad-asn-list.csv)',
  commit: asnCommit,
  licence: 'MIT, Copyright (c) 2025 Brian Hamachek — see datacentre-asns.LICENSE.txt',
  asns: [...new Set(asns)].sort((a, b) => a - b),
}, null, 0) + '\n');
console.log('crawlers: %d patterns; data-centre networks: %d ASNs', patterns.length, asns.length);
