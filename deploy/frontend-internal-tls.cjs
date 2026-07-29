const fs = require('node:fs');
const http = require('node:http');
const https = require('node:https');

const originalRequest = http.request.bind(http);
const internalApiHost = new URL(
  process.env.NEXT_PUBLIC_API_URL || 'https://blacklist-app:2542',
).hostname;
const internalCa = fs.readFileSync(
  process.env.INTERNAL_CA_CERT || '/run/blacklist/ca.crt',
);

http.request = function request(options, callback) {
  if (options && typeof options === 'object' && options.hostname === internalApiHost) {
    return https.request(
      {
        ...options,
        ca: internalCa,
        rejectUnauthorized: true,
      },
      callback,
    );
  }

  return originalRequest(options, callback);
};
