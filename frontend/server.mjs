import { createReadStream, existsSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';
import { createServer } from 'node:http';

const port = Number(process.env.PORT || 5173);
const host = '0.0.0.0';
const distDir = join(process.cwd(), 'dist');

const contentTypes = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon'
};

function send(res, statusCode, body, contentType = 'text/plain; charset=utf-8') {
  res.writeHead(statusCode, {
    'content-type': contentType,
    'cache-control': 'no-store'
  });
  res.end(body);
}

function serveStatic(req, res) {
  const url = new URL(req.url || '/', `http://${req.headers.host || 'localhost'}`);
  if (url.pathname === '/health') {
    send(res, 200, 'ok');
    return;
  }
  if (url.pathname === '/env.js') {
    const backendUrl = JSON.stringify(process.env.VITE_BACKEND_URL || '');
    send(res, 200, `window.__MARL_TRAFFICOPT_CONFIG__ = { BACKEND_URL: ${backendUrl} };\n`, 'text/javascript; charset=utf-8');
    return;
  }

  const requestedPath = url.pathname === '/' ? '/index.html' : decodeURIComponent(url.pathname);
  const normalizedPath = normalize(requestedPath).replace(/^(\.\.[/\\])+/, '');
  const filePath = join(distDir, normalizedPath);
  const fallbackPath = join(distDir, 'index.html');
  const targetPath = existsSync(filePath) ? filePath : fallbackPath;
  const extension = extname(targetPath);

  res.writeHead(200, {
    'content-type': contentTypes[extension] || 'application/octet-stream',
    'cache-control': targetPath.endsWith('index.html') ? 'no-store' : 'public, max-age=31536000, immutable'
  });
  createReadStream(targetPath).pipe(res);
}

createServer(serveStatic).listen(port, host, () => {
  console.log(`MARL TrafficOpt frontend listening on ${host}:${port}`);
});
