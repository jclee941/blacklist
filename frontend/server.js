const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');
const {
  createProxyHeaders,
  isProxyBodyTooLarge,
  parseNextUrl,
  resolveProxyTarget,
  resolveStaticTarget,
  setSecurityHeaders,
} = require('./server-routing');

// SSL Configuration with fallback paths
const SSL_PATHS = [
  // Environment variables (highest priority)
  { key: process.env.SSL_KEY_PATH, cert: process.env.SSL_CERT_PATH },
  // Standard container paths
  { key: '/app/ssl/server.key', cert: '/app/ssl/server.crt' },
  { key: '/app/ssl/privkey.pem', cert: '/app/ssl/fullchain.pem' },
  { key: '/app/ssl/tls.key', cert: '/app/ssl/tls.crt' },
  // Let's Encrypt style
  { key: '/etc/letsencrypt/live/default/privkey.pem', cert: '/etc/letsencrypt/live/default/fullchain.pem' },
];

const findSSLCerts = () => {
  for (const { key, cert } of SSL_PATHS) {
    if (key && cert && fs.existsSync(key) && fs.existsSync(cert)) {
      return { key, cert };
    }
  }
  return null;
};

const sslPaths = findSSLCerts();
const useHTTPS = sslPaths !== null;
const defaultPort = useHTTPS ? 443 : 3000;
const port = parseInt(process.env.PORT, 10) || defaultPort;
const hostname = process.env.HOSTNAME || '0.0.0.0';
const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:2542';
const maxProxyBodyBytes = Number.parseInt(process.env.MAX_REQUEST_BODY_BYTES || '1048576', 10);
if (!Number.isSafeInteger(maxProxyBodyBytes) || maxProxyBodyBytes <= 0) {
  throw new Error('MAX_REQUEST_BODY_BYTES must be a positive integer');
}

const NextServer = require('next/dist/server/next-server').default;
const nextConfig = require('./.next/required-server-files.json');

process.env.__NEXT_PRIVATE_STANDALONE_CONFIG = JSON.stringify(nextConfig.config);

const nextServer = new NextServer({
  dir: __dirname,
  dev: false,
  hostname,
  port,
  conf: {
    ...nextConfig.config,
    distDir: '.next',
  },
  customServer: true,
  minimalMode: false,
});

const handler = nextServer.getRequestHandler();

const getContentType = (extension) =>
  ({
    '.css': 'text/css',
    '.ico': 'image/x-icon',
    '.js': 'application/javascript',
    '.json': 'application/json',
    '.jpg': 'image/jpeg',
    '.png': 'image/png',
    '.svg': 'image/svg+xml',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
  })[extension] || 'application/octet-stream';

const proxyRequest = (req, res, targetPath) => {
  const parsedApi = new URL(apiUrl);
  const clientIp = req.socket?.remoteAddress
    || req.connection?.remoteAddress 
    || '0.0.0.0';
  
  if (isProxyBodyTooLarge(req.headers, maxProxyBodyBytes)) {
    req.resume();
    res.writeHead(413, { 'content-type': 'application/json', connection: 'close' });
    res.end(JSON.stringify({ success: false, error: { code: 'REQUEST_TOO_LARGE' } }));
    return;
  }

  const options = {
    hostname: parsedApi.hostname,
    port: parsedApi.port || 80,
    path: targetPath,
    method: req.method,
    headers: createProxyHeaders(
      req.headers,
      clientIp,
      parsedApi.host,
      req.socket?.encrypted === true ? 'https' : 'http'
    ),
  };

  let bodyBytes = 0;
  let bodyRejected = false;

  const proxyReq = http.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(res);
  });

  proxyReq.on('error', (err) => {
    if (bodyRejected) {
      return;
    }
    console.error('Proxy error:', err.message);
    if (res.headersSent) {
      res.destroy();
    } else {
      res.writeHead(502);
      res.end('Bad Gateway');
    }
  });

  req.on('data', (chunk) => {
    if (bodyRejected) {
      return;
    }
    bodyBytes += chunk.length;
    if (bodyBytes > maxProxyBodyBytes) {
      bodyRejected = true;
      proxyReq.destroy();
      res.writeHead(413, { 'content-type': 'application/json', connection: 'close' });
      res.end(JSON.stringify({ success: false, error: { code: 'REQUEST_TOO_LARGE' } }));
      return;
    }
    if (!proxyReq.write(chunk)) {
      req.pause();
      proxyReq.once('drain', () => req.resume());
    }
  });
  req.on('end', () => {
    if (!bodyRejected) {
      proxyReq.end();
    }
  });
  req.on('error', (error) => proxyReq.destroy(error));
};

// Load redirects from Next.js routes manifest
const loadRedirects = () => {
  try {
    const manifest = JSON.parse(
      fs.readFileSync(path.join(__dirname, '.next', 'routes-manifest.json'), 'utf8')
    );
    return (manifest.redirects || [])
      .filter((r) => !r.internal)
      .map((r) => ({
        regex: new RegExp(r.regex),
        destination: r.destination,
        statusCode: r.statusCode || 307,
      }));
  } catch {
    return [];
  }
};

const redirects = loadRedirects();

const requestHandler = async (req, res) => {
  const parsedUrl = parseNextUrl(req.url);
  if (parsedUrl === null) {
    res.statusCode = 400;
    res.end('Bad Request');
    return;
  }
  const { pathname } = parsedUrl;
  setSecurityHeaders(res);

  const targetPath = resolveProxyTarget(req.url);
  if (targetPath !== null) {
    return proxyRequest(req, res, targetPath);
  }

  // Handle redirects from next.config.ts
  for (const redirect of redirects) {
    if (redirect.regex.test(pathname)) {
      res.writeHead(redirect.statusCode, { Location: redirect.destination });
      res.end();
      return;
    }
  }

  const staticTarget = resolveStaticTarget(__dirname, req.url);
  if (staticTarget !== null) {
    try {
      const realBase = fs.realpathSync(staticTarget.base);
      const realFile = fs.realpathSync(staticTarget.candidate);
      if (
        realFile.startsWith(`${realBase}${path.sep}`) &&
        fs.statSync(realFile).isFile()
      ) {
        res.setHeader('Content-Type', getContentType(path.extname(realFile)));
        res.setHeader('Cache-Control', staticTarget.cacheControl);
        fs.createReadStream(realFile).pipe(res);
        return;
      }
    } catch (error) {
      if (error?.code !== 'ENOENT' && error?.code !== 'ENOTDIR') {
        throw error;
      }
    }
  }

  try {
    await handler(req, res, parsedUrl);
  } catch (err) {
    console.error('Error:', err);
    res.statusCode = 500;
    res.end('Internal Server Error');
  }
};

if (useHTTPS) {
  const httpsOptions = {
    key: fs.readFileSync(sslPaths.key),
    cert: fs.readFileSync(sslPaths.cert),
  };
  https.createServer(httpsOptions, requestHandler).listen(port, hostname, () => {
    console.log(`> HTTPS server ready on https://${hostname}:${port}`);
    console.log(`> SSL: ${sslPaths.key}, ${sslPaths.cert}`);
    console.log(`> API proxy: ${apiUrl}`);
  });
} else {
  http.createServer(requestHandler).listen(port, hostname, () => {
    console.log(`> HTTP server ready on http://${hostname}:${port}`);
    console.log(`> SSL certificates not found, running in HTTP mode`);
    console.log(`> API proxy: ${apiUrl}`);
  });
}
