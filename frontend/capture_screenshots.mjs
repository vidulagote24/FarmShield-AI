/**
 * FarmShield AI - Static Server & Headless Screenshot Capturer
 * Uses pure Node http server to serve frontend/dist and Chrome headless to capture screens.
 */

import http from 'http';
import fs from 'fs';
import path from 'path';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const distDir = path.join(__dirname, 'dist');
const screenshotsDir = path.join(__dirname, 'screenshots');

if (!fs.existsSync(screenshotsDir)) {
  fs.mkdirSync(screenshotsDir, { recursive: true });
}

const MIME_TYPES = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
};

// Create lightweight static file server
const server = http.createServer((req, res) => {
  const urlPath = req.url.split('?')[0];
  let filePath = path.join(distDir, urlPath === '/' ? 'index.html' : urlPath);

  if (!fs.existsSync(filePath)) {
    filePath = path.join(distDir, 'index.html'); // SPA fallback
  }

  const ext = path.extname(filePath);
  const contentType = MIME_TYPES[ext] || 'application/octet-stream';

  fs.readFile(filePath, (err, content) => {
    if (err) {
      res.writeHead(500);
      res.end('Error loading ' + filePath);
    } else {
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content, 'utf-8');
    }
  });
});

const PORT = 8765;
const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const desktopShot = path.join(screenshotsDir, 'recommendation_details_desktop.png');
const mobileShot = path.join(screenshotsDir, 'recommendation_details_mobile.png');

function runCommand(cmd, args) {
  return new Promise((resolve, reject) => {
    const p = spawn(cmd, args, { stdio: 'inherit' });
    p.on('close', (code) => {
      if (code === 0) resolve();
      else reject(new Error(`Process exited with code ${code}`));
    });
    p.on('error', reject);
  });
}

server.listen(PORT, '127.0.0.1', async () => {
  console.log(`Server listening on http://127.0.0.1:${PORT}`);
  try {
    const targetUrl = `http://127.0.0.1:${PORT}/?tab=recommendation_details&rec=rec-c-03`;
    const insightsUrl = `http://127.0.0.1:${PORT}/?tab=insights`;

    console.log('Capturing Desktop Screenshot (1280x840)...');
    await runCommand(chromePath, [
      '--headless=new',
      '--disable-gpu',
      '--no-sandbox',
      '--window-size=1280,840',
      `--screenshot=${desktopShot}`,
      targetUrl,
    ]);
    console.log(`✓ Desktop screenshot saved: ${desktopShot}`);

    console.log('Capturing Mobile Screenshot (390x844)...');
    await runCommand(chromePath, [
      '--headless=new',
      '--disable-gpu',
      '--no-sandbox',
      '--window-size=390,844',
      `--screenshot=${mobileShot}`,
      targetUrl,
    ]);
    console.log(`✓ Mobile screenshot saved: ${mobileShot}`);

    const insightsDesktop = path.join(screenshotsDir, 'farm_insights_desktop.png');
    const insightsMobile = path.join(screenshotsDir, 'farm_insights_mobile.png');

    console.log('Capturing Farm Insights Desktop Screenshot (1280x960)...');
    await runCommand(chromePath, [
      '--headless=new',
      '--disable-gpu',
      '--no-sandbox',
      '--window-size=1280,960',
      `--screenshot=${insightsDesktop}`,
      insightsUrl,
    ]);
    console.log(`✓ Farm Insights Desktop saved: ${insightsDesktop}`);

    console.log('Capturing Farm Insights Mobile Screenshot (390x844)...');
    await runCommand(chromePath, [
      '--headless=new',
      '--disable-gpu',
      '--no-sandbox',
      '--window-size=390,844',
      `--screenshot=${insightsMobile}`,
      insightsUrl,
    ]);
    console.log(`✓ Farm Insights Mobile saved: ${insightsMobile}`);
  } catch (err) {
    console.error('Capture error:', err);
  } finally {
    console.log('Closing server...');
    server.close();
    process.exit(0);
  }
});
