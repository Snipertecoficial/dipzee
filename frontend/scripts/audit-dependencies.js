const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const yarnEntrypoint = process.env.npm_execpath;
if (!yarnEntrypoint) throw new Error('This audit must run through Yarn');

const result = spawnSync(
  process.execPath,
  [yarnEntrypoint, 'audit', '--json', '--groups', 'dependencies'],
  { encoding: 'utf8' },
);
const advisories = result.stdout
  .split(/\r?\n/)
  .filter(Boolean)
  .map((line) => {
    try { return JSON.parse(line); } catch { return null; }
  })
  .filter((entry) => entry?.type === 'auditAdvisory')
  .map((entry) => entry.data.advisory);

const sourceRoot = path.join(__dirname, '..', 'src');
function sourceUsesRsc(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).some((entry) => {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) return sourceUsesRsc(target);
    if (!/\.[jt]sx?$/.test(entry.name)) return false;
    return /react-server-dom|unstable_.*RSC|RSCRouter/.test(fs.readFileSync(target, 'utf8'));
  });
}

const allowed = new Set();
if (!sourceUsesRsc(sourceRoot)) {
  // GHSA-qwww-vcr4-c8h2 explicitly affects only unstable React Server
  // Components APIs. Dipzee is a static BrowserRouter SPA and ships no RSC
  // runtime. Keep this exception narrow so any other advisory still fails CI.
  allowed.add(1124282);
}

const blocking = advisories.filter(
  (advisory) => ['high', 'critical'].includes(advisory.severity) && !allowed.has(advisory.id),
);
if (blocking.length) {
  for (const advisory of blocking) {
    console.error(`${advisory.severity}: ${advisory.module_name}: ${advisory.title} (${advisory.url})`);
  }
  process.exit(1);
}
console.log(`Dependency audit passed; ${advisories.length} advisory record(s), ${advisories.filter((item) => allowed.has(item.id)).length} non-applicable RSC exception(s).`);
