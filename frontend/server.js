const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');
const { parse } = require('url');

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

const getContentType = (ext) => ({
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.json': 'application/json',
}[ext] || 'application/octet-stream');

const proxyRequest = (req, res, targetPath) => {
  const parsedApi = new URL(apiUrl);
  const clientIp = req.headers['x-forwarded-for']?.split(',')[0]?.trim() 
    || req.socket?.remoteAddress 
    || req.connection?.remoteAddress 
    || '0.0.0.0';
  
  const options = {
    hostname: parsedApi.hostname,
    port: parsedApi.port || 80,
    path: targetPath,
    method: req.method,
    headers: { 
      ...req.headers, 
      host: parsedApi.host,
      'x-forwarded-for': clientIp,
      'x-real-ip': clientIp,
    },
  };

  const proxyReq = http.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(res);
  });

  proxyReq.on('error', (err) => {
    console.error('Proxy error:', err.message);
    res.writeHead(502);
    res.end('Bad Gateway');
  });

  req.pipe(proxyReq);
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
  const parsedUrl = parse(req.url, true);
  const { pathname } = parsedUrl;

  if (pathname.startsWith('/api/')) {
    return proxyRequest(req, res, req.url);
  }

  if (pathname === '/health' || pathname === '/metrics') {
    return proxyRequest(req, res, pathname);
  }

  if (pathname.startsWith('/uiview/')) {
    const targetPath = pathname.replace('/uiview', '');
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

  if (pathname.startsWith('/_next/static/')) {
    const relativePath = pathname.replace('/_next/static/', '');
    const filePath = path.join(__dirname, '.next', 'static', relativePath);
    
    if (fs.existsSync(filePath)) {
      const ext = path.extname(filePath);
      res.setHeader('Content-Type', getContentType(ext));
      res.setHeader('Cache-Control', 'public, max-age=31536000, immutable');
      fs.createReadStream(filePath).pipe(res);
      return;
    }
  }

  if (pathname.startsWith('/') && !pathname.startsWith('/_next') && !pathname.startsWith('/api')) {
    const publicPath = path.join(__dirname, 'public', pathname);
    if (fs.existsSync(publicPath) && fs.statSync(publicPath).isFile()) {
      const ext = path.extname(publicPath);
      res.setHeader('Content-Type', getContentType(ext));
      res.setHeader('Cache-Control', 'public, max-age=86400');
      fs.createReadStream(publicPath).pipe(res);
      return;
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
