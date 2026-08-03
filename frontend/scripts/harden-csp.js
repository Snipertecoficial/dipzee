const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const indexPath = path.join(__dirname, '..', 'build', 'index.html');
let html = fs.readFileSync(indexPath, 'utf8');
const hashes = [];
const inlineScript = /<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi;
for (const match of html.matchAll(inlineScript)) {
  if (match[1]) {
    const digest = crypto.createHash('sha256').update(match[1], 'utf8').digest('base64');
    hashes.push(`'sha256-${digest}'`);
  }
}

let connectOrigin = "'self'";
const backendUrl = process.env.REACT_APP_BACKEND_URL;
if (backendUrl) {
  try {
    const origin = new URL(backendUrl).origin;
    if (origin !== 'null') connectOrigin += ` ${origin}`;
  } catch {
    throw new Error('REACT_APP_BACKEND_URL must be an absolute URL');
  }
}

const policy = [
  "default-src 'self'",
  `script-src 'self' ${hashes.join(' ')}`.trim(),
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src 'self' data: https://fonts.gstatic.com",
  "img-src 'self' data: blob: https:",
  `connect-src ${connectOrigin}`,
  "worker-src 'self' blob:",
  "child-src 'self' blob:",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join('; ') + ';';

html = html.replace(
  /(<meta\s+id="csp-policy"\s+http-equiv="Content-Security-Policy"\s+content=")[^"]*("\s*\/?>)/i,
  `$1${policy}$2`,
);
fs.writeFileSync(indexPath, html, 'utf8');
