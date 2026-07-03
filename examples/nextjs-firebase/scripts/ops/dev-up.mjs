#!/usr/bin/env node
// dev-up: garantiza UN dev server sano y devuelve su URL. Uso: node scripts/ops/dev-up.mjs
//
// Friccion que ataca (auditoria 2026-07): cada smoke test re-descubria a mano
// que el dev server ya estaba vivo en otro puerto, o quedaba un proceso
// huerfano ocupando 3000-3003 sin responder. Esto lo vuelve 1 comando:
//   1. Escanea 3000-3010 con GET /api/health (2s timeout).
//   2. Si alguno responde -> imprime DEV_URL=<url> y sale (reusar, no duplicar).
//   3. Si un puerto esta ocupado pero /api/health no responde -> mata ese PID
//      (proceso huerfano de un dev server anterior).
//   4. Si ninguno vive -> spawnea `npm run dev` detached con la memoria de CI
//      y espera readiness hasta 120s.
//
// Exit 0 con "DEV_URL=http://localhost:<port>" en stdout; exit 1 si no pudo.

import { spawn, spawnSync } from 'node:child_process';
import http from 'node:http';
import net from 'node:net';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const PORTS = Array.from({ length: 11 }, (_, i) => 3000 + i);
const READINESS_TIMEOUT_MS = 120_000;

function healthCheck(port) {
  return new Promise((resolve) => {
    const req = http.get({ host: '127.0.0.1', port, path: '/api/health', timeout: 2000 }, (res) => {
      res.resume();
      resolve(res.statusCode != null && res.statusCode < 500);
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => { req.destroy(); resolve(false); });
  });
}

function portOccupied(port) {
  return new Promise((resolve) => {
    const socket = net.connect({ host: '127.0.0.1', port, timeout: 1500 });
    socket.on('connect', () => { socket.destroy(); resolve(true); });
    socket.on('error', () => resolve(false));
    socket.on('timeout', () => { socket.destroy(); resolve(false); });
  });
}

function killPortOwner(port) {
  // netstat sin shell + filtrado en JS (nada de exec con interpolacion).
  const r = spawnSync('netstat', ['-ano', '-p', 'tcp'], { encoding: 'utf8' });
  if (r.status !== 0 || !r.stdout) return false;
  const pids = new Set();
  for (const line of r.stdout.split('\n')) {
    if (!line.includes(`:${port} `) && !line.includes(`:${port}\t`)) continue;
    const m = line.trim().match(/LISTENING\s+(\d+)\s*$/);
    if (m && m[1] !== '0') pids.add(m[1]);
  }
  for (const pid of pids) {
    console.log(`dev-up: matando proceso huerfano PID ${pid} (puerto ${port} ocupado sin /api/health)`);
    spawnSync('taskkill', ['/PID', pid, '/F'], { stdio: 'ignore' });
  }
  return pids.size > 0;
}

async function findAlive() {
  for (const port of PORTS) {
    if (await healthCheck(port)) return port;
  }
  return null;
}

async function main() {
  const alive = await findAlive();
  if (alive) {
    console.log(`dev-up: reusando server vivo\nDEV_URL=http://localhost:${alive}`);
    return 0;
  }

  // Limpiar huerfanos: puertos ocupados que no respondieron al health check.
  for (const port of [3000, 3001, 3002, 3003]) {
    if (await portOccupied(port)) killPortOwner(port);
  }

  console.log('dev-up: no hay server vivo, levantando `npm run dev`...');
  const child = spawn('npm', ['run', 'dev'], {
    cwd: ROOT,
    detached: true,
    shell: true,
    stdio: 'ignore',
    env: { ...process.env, NODE_OPTIONS: '--max-old-space-size=6144' },
  });
  child.unref();

  const start = Date.now();
  while (Date.now() - start < READINESS_TIMEOUT_MS) {
    await new Promise((r) => setTimeout(r, 3000));
    const port = await findAlive();
    if (port) {
      console.log(`dev-up: listo en ${Math.round((Date.now() - start) / 1000)}s\nDEV_URL=http://localhost:${port}`);
      return 0;
    }
  }

  console.error(`dev-up: el server no respondio /api/health en ${READINESS_TIMEOUT_MS / 1000}s. Revisar \`npm run dev\` a mano.`);
  return 1;
}

main().then((code) => process.exit(code));
