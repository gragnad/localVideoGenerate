import http from 'node:http';
import { createReadStream, watch } from 'node:fs';
import { mkdir, readFile, readdir, rename, rm, stat, writeFile } from 'node:fs/promises';
import { Readable } from 'node:stream';
import { extname, isAbsolute, join, normalize, relative, resolve } from 'node:path';
import { randomUUID } from 'node:crypto';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const exec = promisify(execFile);
const APP_ROOT = resolve(import.meta.dirname, '..');
const ROOT = resolve(process.env.VIDEO_ENGINE_ROOT || APP_ROOT);
const PUBLIC = join(import.meta.dirname, 'public');
const H3_ROOT = join(ROOT, 'runtime/h3');
const H3_JOBS = join(H3_ROOT, 'jobs');
const H3_CANDIDATE_SETS = join(H3_ROOT, 'candidate_sets');
const H3_CANDIDATE_REVIEW_QUEUE = join(H3_ROOT, 'candidate_review_queue');
const H3_PROJECT_TEST_SETS = join(H3_ROOT, 'project_test_sets');
const H3_TEST_QUEUES = join(H3_ROOT, 'test_queues');
const H3_THUMBNAIL_CACHE = join(H3_ROOT, 'thumbnail_cache');
const MODEL_REVIEW_QUEUE = join(ROOT, 'runtime/model_test_review_queue');
const ARCHIVED_JOBS = join(ROOT, 'jobs'); // read-only playback for archived benchmark history
const TMP = join(ROOT, 'runtime/ui-uploads');
const COMFY_OUTPUT = resolve(
  process.env.COMFY_OUTPUT_DIR || join(APP_ROOT, '../../ai-workspace/apps/ComfyUI/output'),
);
const HOST = process.env.VIDEO_UI_HOST || '0.0.0.0';
const PORT = Number(process.env.VIDEO_UI_PORT || 8502);
const PYTHON = process.env.VIDEO_ENGINE_PYTHON || join(APP_ROOT, '.venv/bin/python');
const BACKEND = join(APP_ROOT, 'ui_backend.py');
const ACCESS_KEY = process.env.VIDEO_UI_ACCESS_KEY || '';
const WINDOWS_RENDER_AGENT_URL = String(
  process.env.H3_RENDER_AGENT_URL
  || process.env.H3_PROMPT_REVISION_REMOTE_URL
  || '',
).trim().replace(/\/+$/, '');

await mkdir(TMP, { recursive: true });

async function readJson(path, fallback = {}) {
  try {
    return JSON.parse(await readFile(path, 'utf8'));
  } catch {
    return fallback;
  }
}

function json(res, statusCode, payload) {
  const body = Buffer.from(JSON.stringify(payload));
  res.writeHead(statusCode, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': body.length,
    'cache-control': 'no-store',
  });
  res.end(body);
}

async function bodyJson(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  return JSON.parse(Buffer.concat(chunks).toString() || '{}');
}

function formData(req) {
  return new Request(`http://local${req.url}`, {
    method: req.method,
    headers: req.headers,
    body: Readable.toWeb(req),
    duplex: 'half',
  }).formData();
}

function safeText(value) {
  return String(value || '').replace(
    /(api[_-]?key|token|password|secret)(\s*[:=]\s*)\S+/gi,
    '$1$2[REDACTED]',
  );
}

function safeId(value, label = 'ID') {
  const id = String(value || '');
  if (!id || id === '.' || id === '..' || id.includes('/') || id.includes('\\')) {
    throw new Error(`허용되지 않는 ${label}입니다.`);
  }
  return id;
}

async function python(action, payload) {
  return new Promise((resolveCall, reject) => {
    const child = execFile(
      PYTHON,
      [BACKEND, action],
      {
        env: { ...process.env, VIDEO_ENGINE_ROOT: ROOT, PYTHONPATH: ROOT },
        maxBuffer: 16 * 1024 * 1024,
      },
      (error, stdout, stderr) => {
        if (error) return reject(new Error(stderr || error.message));
        try {
          resolveCall(JSON.parse(stdout));
        } catch (parseError) {
          reject(parseError);
        }
      },
    );
    child.stdin.end(JSON.stringify(payload));
  });
}

async function saveUpload(file, folder) {
  if (!file || typeof file.arrayBuffer !== 'function') return null;
  const path = join(folder, `${randomUUID()}${extname(file.name).toLowerCase()}`);
  await writeFile(path, Buffer.from(await file.arrayBuffer()));
  return path;
}

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.mp4': 'video/mp4',
  '.webm': 'video/webm',
  '.mov': 'video/quicktime',
};

async function stream(path, req, res, { staticFile = false, cacheSeconds = null } = {}) {
  try {
    const info = await stat(path);
    const contentType = MIME_TYPES[extname(path).toLowerCase()] || 'application/octet-stream';
    const cacheControl = cacheSeconds == null
      ? (staticFile ? 'no-cache' : 'private, max-age=60')
      : `public, max-age=${cacheSeconds}`;
    const range = String(req.headers.range || '');
    if (range && /^video\//.test(contentType)) {
      const match = range.match(/^bytes=(\d*)-(\d*)$/);
      if (match) {
        const start = match[1] ? Number(match[1]) : 0;
        const end = match[2] ? Math.min(Number(match[2]), info.size - 1) : info.size - 1;
        if (start <= end && start < info.size) {
          res.writeHead(206, {
            'content-type': contentType,
            'content-length': end - start + 1,
            'content-range': `bytes ${start}-${end}/${info.size}`,
            'accept-ranges': 'bytes',
            'cache-control': cacheControl,
          });
          createReadStream(path, { start, end }).pipe(res);
          return;
        }
      }
      res.writeHead(416, { 'content-range': `bytes */${info.size}` });
      res.end();
      return;
    }
    res.writeHead(200, {
      'content-type': contentType,
      'content-length': info.size,
      'accept-ranges': /^video\//.test(contentType) ? 'bytes' : 'none',
      'cache-control': cacheControl,
    });
    createReadStream(path).pipe(res);
  } catch {
    json(res, 404, { error: '파일을 찾을 수 없습니다.' });
  }
}

async function serviceReady(url) {
  try {
    return (await fetch(url, { signal: AbortSignal.timeout(1200) })).ok;
  } catch {
    return false;
  }
}

function finiteNumber(value) {
  const number = Number(String(value ?? '').trim());
  return Number.isFinite(number) ? number : null;
}

async function systemMetrics() {
  let memory = null;
  let gpu = null;
  try {
    const values = {};
    for (const line of (await readFile('/proc/meminfo', 'utf8')).split('\n')) {
      const match = line.match(/^([A-Za-z_()]+):\s+(\d+)\s+kB$/);
      if (match) values[match[1]] = Number(match[2]) * 1024;
    }
    const total = values.MemTotal || 0;
    const free = values.MemFree || 0;
    const cache = (values.Buffers || 0) + (values.Cached || 0) + (values.SReclaimable || 0);
    memory = {
      total_bytes: total,
      used_including_cache_bytes: Math.max(0, total - free),
      available_bytes: values.MemAvailable || 0,
      cache_bytes: cache,
    };
  } catch {}
  try {
    const { stdout } = await exec(
      'nvidia-smi',
      [
        '--query-gpu=name,temperature.gpu,power.draw,utilization.gpu',
        '--format=csv,noheader,nounits',
      ],
      { timeout: 2500, maxBuffer: 256 * 1024 },
    );
    const fields = String(stdout).trim().split(',').map((value) => value.trim());
    gpu = {
      name: fields[0] || 'NVIDIA GPU',
      temperature_c: finiteNumber(fields[1]),
      power_w: finiteNumber(fields[2]),
      utilization_percent: finiteNumber(fields[3]),
    };
  } catch {}
  return { sampled_at: new Date().toISOString(), memory, gpu };
}

async function windowsRenderStatus() {
  const sampledAt = new Date().toISOString();
  if (!WINDOWS_RENDER_AGENT_URL) {
    return {
      sampled_at: sampledAt,
      sleep_state: 'unconfigured',
      sleep_label: '설정 안 됨',
      gpu_power_w: null,
      reachable: false,
    };
  }
  try {
    const response = await fetch(`${WINDOWS_RENDER_AGENT_URL}/healthz`, {
      headers: { accept: 'application/json' },
      signal: AbortSignal.timeout(1800),
    });
    if (!response.ok) throw new Error(`healthz ${response.status}`);
    const health = await response.json();
    if (health?.status !== 'ok') throw new Error('invalid health response');
    const rawGpuPower = health.gpu_power_w ?? health.power_w;
    return {
      sampled_at: sampledAt,
      sleep_state: 'awake',
      sleep_label: '켜짐',
      gpu_power_w: rawGpuPower == null ? null : finiteNumber(rawGpuPower),
      reachable: true,
    };
  } catch {
    return {
      sampled_at: sampledAt,
      sleep_state: 'sleeping_or_offline',
      sleep_label: '최대 절전/오프라인',
      gpu_power_w: null,
      reachable: false,
    };
  }
}

async function resolveJobDir(jobId) {
  const id = safeId(jobId, '작업 ID');
  for (const base of [H3_JOBS, ARCHIVED_JOBS]) {
    const directory = join(base, id);
    try {
      if ((await stat(join(directory, 'request.json'))).isFile()) return directory;
    } catch {}
  }
  throw new Error(`작업을 찾을 수 없습니다: ${id}`);
}

async function resolveJobVideoPath(jobId) {
  const directory = await resolveJobDir(jobId);
  const request = await readJson(join(directory, 'request.json'), {});
  const manifest = await readJson(join(directory, 'manifest.json'), {});
  const status = await readJson(join(directory, 'status.json'), {});
  if (request.job_type === 'h3_r2v_generate' && status.status !== 'completed') {
    return null;
  }
  for (const direct of [manifest.local_video_path, manifest.review_video_local_path]) {
    if (!direct) continue;
    try {
      if ((await stat(String(direct))).isFile()) return String(direct);
    } catch {}
  }
  const outputs = [
    ...(Array.isArray(manifest.outputs) ? manifest.outputs : []),
    ...(Array.isArray(status.outputs) ? status.outputs : []),
  ];
  for (const output of outputs) {
    if (!/\.(mp4|webm|mov)$/i.test(String(output.filename || ''))) continue;
    const local = resolve(COMFY_OUTPUT, String(output.subfolder || ''), String(output.filename));
    const rel = relative(COMFY_OUTPUT, local);
    if (rel.startsWith('..') || isAbsolute(rel)) continue;
    try {
      if ((await stat(local)).isFile()) return local;
    } catch {}
  }
  return null;
}

async function serveVideoThumbnailPath(video, cacheId, req, res) {
  const id = safeId(cacheId, '썸네일 캐시 ID');
  let videoInfo;
  try {
    videoInfo = await stat(video);
    if (!videoInfo.isFile()) throw new Error('not a file');
  } catch {
    return json(res, 404, { error: '완료된 영상을 찾을 수 없습니다.' });
  }
  await mkdir(H3_THUMBNAIL_CACHE, { recursive: true });
  const thumbnail = join(H3_THUMBNAIL_CACHE, `${id}.jpg`);
  let fresh = false;
  try {
    const thumbInfo = await stat(thumbnail);
    fresh = thumbInfo.size > 0 && thumbInfo.mtimeMs >= videoInfo.mtimeMs;
  } catch {}
  if (!fresh) {
    const temporary = `${thumbnail}.${randomUUID()}.tmp.jpg`;
    try {
      await exec(
        'ffmpeg',
        [
          '-hide_banner', '-loglevel', 'error', '-y', '-ss', '0.1', '-i', video,
          '-frames:v', '1', '-vf', 'scale=960:-2:force_original_aspect_ratio=decrease',
          '-q:v', '3', temporary,
        ],
        { timeout: 30000, maxBuffer: 2 * 1024 * 1024 },
      );
      const generated = await stat(temporary);
      if (!generated.isFile() || generated.size <= 0) {
        throw new Error('빈 썸네일이 생성되었습니다.');
      }
      await rename(temporary, thumbnail);
    } catch {
      return json(res, 500, { error: '영상 썸네일을 생성하지 못했습니다.' });
    } finally {
      await rm(temporary, { force: true }).catch(() => {});
    }
  }
  return stream(thumbnail, req, res, { cacheSeconds: 3600 });
}

async function serveVideoThumbnail(jobId, req, res) {
  let video;
  try {
    video = await resolveJobVideoPath(jobId);
  } catch {
    return json(res, 404, { error: '완료된 영상을 찾을 수 없습니다.' });
  }
  if (!video) return json(res, 404, { error: '완료된 영상을 찾을 수 없습니다.' });
  return serveVideoThumbnailPath(video, safeId(jobId, '작업 ID'), req, res);
}

async function serveH3VideoThumbnail(jobId, req, res) {
  const id = safeId(jobId, 'H3 작업 ID');
  const status = await readJson(join(H3_JOBS, id, 'status.json'), {});
  if (status.status !== 'completed') {
    return json(res, 404, { error: '완료된 H3 영상을 찾을 수 없습니다.' });
  }
  let video;
  try {
    video = await resolveJobVideoPath(id);
  } catch {
    return json(res, 404, { error: '완료된 H3 영상을 찾을 수 없습니다.' });
  }
  if (!video) return json(res, 404, { error: '완료된 H3 영상을 찾을 수 없습니다.' });
  return serveVideoThumbnailPath(video, id, req, res);
}

const eventClients = new Set();
const watchConfigs = [
  { kind: 'h3_job', root: H3_JOBS, file: 'status.json' },
  { kind: 'h3_candidate_set', root: H3_CANDIDATE_SETS, file: 'candidate_set.json' },
  { kind: 'h3_candidate_review', root: H3_CANDIDATE_REVIEW_QUEUE, file: 'status.json' },
  { kind: 'h3_project_test_set', root: H3_PROJECT_TEST_SETS, file: 'project_test_set.json' },
  { kind: 'h3_test_queue', root: H3_TEST_QUEUES, file: 'queue.json' },
  { kind: 'model_review_queue', root: MODEL_REVIEW_QUEUE, file: 'status.json' },
];

function publishStateEvent(payload) {
  const message = `event: state_changed\ndata: ${JSON.stringify({
    ...payload,
    at: new Date().toISOString(),
  })}\n\n`;
  for (const client of [...eventClients]) {
    try {
      client.write(message);
    } catch {
      eventClients.delete(client);
    }
  }
}

for (const config of watchConfigs) {
  await mkdir(config.root, { recursive: true });
  try {
    const watcher = watch(config.root, { recursive: true }, (_event, filename) => {
      if (!filename || String(filename).endsWith(config.file)) {
        publishStateEvent({ resource: config.kind, change: 'state' });
      }
    });
    watcher.on('error', () => {});
    watcher.unref();
  } catch {}
}
const keepalive = setInterval(() => {
  for (const client of [...eventClients]) {
    try {
      client.write(': keepalive\n\n');
    } catch {
      eventClients.delete(client);
    }
  }
}, 25000);
keepalive.unref();

function requestKey(req) {
  const raw = String(req.headers['x-access-key'] || '');
  const encoded = String(req.headers['x-access-key-b64'] || '');
  try {
    if (encoded) return Buffer.from(encoded, 'base64').toString('utf8');
  } catch {}
  const cookies = String(req.headers.cookie || '');
  const cookie = (cookies.match(/(?:^|;\s*)h3_session=([^;]+)/) || [])[1];
  return raw || decodeURIComponent(cookie || '');
}

async function route(req, res) {
  const url = new URL(req.url, 'http://local');
  const key = requestKey(req);
  if (ACCESS_KEY && url.pathname.startsWith('/api/') && key !== ACCESS_KEY) {
    return json(res, 401, { error: '접근 키가 필요합니다.' });
  }
  if (ACCESS_KEY && key === ACCESS_KEY) {
    res.setHeader(
      'set-cookie',
      `h3_session=${encodeURIComponent(ACCESS_KEY)}; Path=/; HttpOnly; SameSite=Strict`,
    );
  }

  if (req.method === 'GET' && url.pathname === '/api/events') {
    res.writeHead(200, {
      'content-type': 'text/event-stream; charset=utf-8',
      'cache-control': 'no-cache, no-transform',
      connection: 'keep-alive',
      'x-accel-buffering': 'no',
    });
    res.write('retry: 2000\nevent: ready\ndata: {}\n\n');
    eventClients.add(res);
    req.on('close', () => eventClients.delete(res));
    return;
  }
  if (req.method === 'GET' && url.pathname === '/api/status') {
    return json(res, 200, {
      ui: true,
      h3_worker: await readJson(join(H3_ROOT, 'worker_status.json'), {}),
      windows_candidate_worker: await readJson(
        join(H3_ROOT, 'windows_candidate_worker_status.json'),
        {},
      ),
      review_worker: await readJson(join(ROOT, 'runtime/model_test_review_worker_status.json'), {}),
      comfyui: await serviceReady(`${process.env.COMFY_URL || 'http://127.0.0.1:8188'}/system_stats`),
      vllm: await serviceReady(`${process.env.VLLM_URL || 'http://127.0.0.1:8091'}/v1/models`),
    });
  }
  if (req.method === 'GET' && url.pathname === '/api/system-metrics') {
    return json(res, 200, await systemMetrics());
  }
  if (req.method === 'GET' && url.pathname === '/api/windows-render-status') {
    return json(res, 200, await windowsRenderStatus());
  }

  if (req.method === 'GET' && url.pathname === '/api/h3/config') {
    return json(res, 200, await python('h3_config', {}));
  }
  if (req.method === 'GET' && url.pathname === '/api/h3/state') {
    return json(res, 200, await python('h3_state', {}));
  }
  if (req.method === 'GET' && url.pathname === '/api/h3/projects') {
    return json(res, 200, await python('h3_projects', {}));
  }
  const h3Project = url.pathname.match(/^\/api\/h3\/projects\/([^/]+)$/);
  if (req.method === 'DELETE' && h3Project) {
    return json(res, 200, await python('delete_h3_project', {
      project_id: decodeURIComponent(h3Project[1]),
      ...(await bodyJson(req)),
    }));
  }
  const projectClips = url.pathname.match(/^\/api\/h3\/projects\/([^/]+)\/clips$/);
  if (req.method === 'GET' && projectClips) {
    return json(res, 200, await python('h3_project_clips', {
      project_id: decodeURIComponent(projectClips[1]),
    }));
  }
  const projectClip = url.pathname.match(/^\/api\/h3\/projects\/([^/]+)\/clips\/([^/]+)$/);
  if (req.method === 'GET' && projectClip) {
    return json(res, 200, await python('h3_project_clip', {
      project_id: decodeURIComponent(projectClip[1]),
      clip_id: decodeURIComponent(projectClip[2]),
    }));
  }
  const projectPicture = url.pathname.match(
    /^\/api\/h3\/projects\/([^/]+)\/clips\/([^/]+)\/pictures\/(\d+)$/,
  );
  if (req.method === 'GET' && projectPicture) {
    try {
      const output = await python('h3_project_picture', {
        project_id: decodeURIComponent(projectPicture[1]),
        clip_id: decodeURIComponent(projectPicture[2]),
        picture_index: Number(projectPicture[3]),
      });
      return stream(output.path, req, res, { cacheSeconds: 3600 });
    } catch (error) {
      return json(res, 404, { error: error.message });
    }
  }
  if (req.method === 'POST' && url.pathname === '/api/h3/project-test-sets') {
    return json(res, 201, await python('create_h3_project_test_set', await bodyJson(req)));
  }
  const projectTestSet = url.pathname.match(
    /^\/api\/h3\/project-test-sets\/([^/]+)$/,
  );
  if (req.method === 'DELETE' && projectTestSet) {
    return json(res, 200, await python('delete_h3_project_test_set', {
      project_test_set_id: decodeURIComponent(projectTestSet[1]),
      ...(await bodyJson(req)),
    }));
  }
  const projectTestQueue = url.pathname.match(
    /^\/api\/h3\/project-test-sets\/([^/]+)\/queue$/,
  );
  if (req.method === 'POST' && projectTestQueue) {
    return json(res, 200, await python('queue_h3_project_test_set', {
      project_test_set_id: decodeURIComponent(projectTestQueue[1]),
      ...(await bodyJson(req)),
    }));
  }
  if (req.method === 'POST' && url.pathname === '/api/h3/scenes/candidate-sets') {
    return json(res, 201, await python('queue_h3_scene_candidates', await bodyJson(req)));
  }
  const groupStop = url.pathname.match(/^\/api\/h3\/queue-groups\/([^/]+)\/force-stop$/);
  if (req.method === 'POST' && groupStop) {
    return json(res, 200, await python('force_stop_h3_group', {
      group_id: decodeURIComponent(groupStop[1]),
      ...(await bodyJson(req)),
    }));
  }
  if (req.method === 'POST' && url.pathname === '/api/h3/candidate-sets') {
    const form = await formData(req);
    const data = JSON.parse(String(form.get('data') || '{}'));
    const folder = join(TMP, randomUUID());
    await mkdir(folder, { recursive: true });
    try {
      for (let index = 0; index < (data.references || []).length; index += 1) {
        if (data.references[index].project_id) continue;
        const file = form.get(`reference_${index}`);
        if (!file || typeof file.arrayBuffer !== 'function') {
          throw new Error(`Picture ${index + 1} 파일이 필요합니다.`);
        }
        data.references[index].upload_path = await saveUpload(file, folder);
        data.references[index].original_name = file.name || `picture_${index + 1}.png`;
      }
      return json(res, 201, await python('create_h3_candidate_set', data));
    } finally {
      await rm(folder, { recursive: true, force: true });
    }
  }
  if (req.method === 'PUT' && url.pathname === '/api/h3/candidate-ai-review') {
    return json(res, 200, await python(
      'set_h3_candidate_ai_review',
      await bodyJson(req),
    ));
  }
  const candidateSet = url.pathname.match(
    /^\/api\/h3\/candidate-sets\/([^/]+)$/,
  );
  if (req.method === 'DELETE' && candidateSet) {
    return json(res, 200, await python('delete_h3_candidate_set', {
      candidate_set_id: decodeURIComponent(candidateSet[1]),
      ...(await bodyJson(req)),
    }));
  }
  const candidateRequeue = url.pathname.match(
    /^\/api\/h3\/candidate-sets\/([^/]+)\/requeue$/,
  );
  if (req.method === 'POST' && candidateRequeue) {
    return json(res, 201, await python('requeue_h3_candidate_set', {
      candidate_set_id: decodeURIComponent(candidateRequeue[1]),
    }));
  }
  const candidateRevision = url.pathname.match(
    /^\/api\/h3\/candidate-sets\/([^/]+)\/(?:revision-requests|revisions)$/,
  );
  if (req.method === 'POST' && candidateRevision) {
    return json(res, 201, await python('save_h3_prompt_revision_request', {
      candidate_set_id: decodeURIComponent(candidateRevision[1]),
      ...(await bodyJson(req)),
    }));
  }
  const promptRevisionApply = url.pathname.match(
    /^\/api\/h3\/prompt-revision-requests\/([^/]+)\/apply$/,
  );
  if (req.method === 'POST' && promptRevisionApply) {
    return json(res, 201, await python('apply_h3_prompt_revision', {
      prompt_revision_request_id: decodeURIComponent(promptRevisionApply[1]),
      ...(await bodyJson(req)),
    }));
  }
  const candidateRestore = url.pathname.match(
    /^\/api\/h3\/candidate-sets\/([^/]+)\/restore$/,
  );
  if (req.method === 'POST' && candidateRestore) {
    return json(res, 201, await python('restore_h3_candidate_version', {
      candidate_set_id: decodeURIComponent(candidateRestore[1]),
    }));
  }
  const candidateSelect = url.pathname.match(
    /^\/api\/h3\/candidate-sets\/([^/]+)\/select$/,
  );
  if (req.method === 'POST' && candidateSelect) {
    return json(res, 200, await python('select_h3_candidate', {
      candidate_set_id: decodeURIComponent(candidateSelect[1]),
      ...(await bodyJson(req)),
    }));
  }
  const candidateResolutionRerender = url.pathname.match(
    /^\/api\/h3\/candidate-sets\/([^/]+)\/resolution-rerenders$/,
  );
  if (req.method === 'POST' && candidateResolutionRerender) {
    return json(res, 201, await python('create_h3_resolution_rerender', {
      candidate_set_id: decodeURIComponent(candidateResolutionRerender[1]),
      ...(await bodyJson(req)),
    }));
  }
  const candidateVideoUpscale = url.pathname.match(
    /^\/api\/h3\/candidate-sets\/([^/]+)\/video-upscales$/,
  );
  if (req.method === 'POST' && candidateVideoUpscale) {
    return json(res, 201, await python('create_h3_video_upscale', {
      candidate_set_id: decodeURIComponent(candidateVideoUpscale[1]),
      ...(await bodyJson(req)),
    }));
  }
  const candidateJobSelection = url.pathname.match(
    /^\/api\/h3\/candidate-sets\/([^/]+)\/selection\/([^/]+)$/,
  );
  if (req.method === 'DELETE' && candidateJobSelection) {
    return json(res, 200, await python('clear_h3_candidate_selection', {
      candidate_set_id: decodeURIComponent(candidateJobSelection[1]),
      job_id: decodeURIComponent(candidateJobSelection[2]),
    }));
  }
  const candidateSelection = url.pathname.match(
    /^\/api\/h3\/candidate-sets\/([^/]+)\/selection$/,
  );
  if (req.method === 'DELETE' && candidateSelection) {
    return json(res, 200, await python('clear_h3_candidate_selection', {
      candidate_set_id: decodeURIComponent(candidateSelection[1]),
    }));
  }
  const h3VideoThumbnail = url.pathname.match(
    /^\/api\/h3\/jobs\/([^/]+)\/video-thumbnail$/,
  );
  if (req.method === 'GET' && h3VideoThumbnail) {
    return serveH3VideoThumbnail(decodeURIComponent(h3VideoThumbnail[1]), req, res);
  }
  const h3Video = url.pathname.match(/^\/api\/h3\/jobs\/([^/]+)\/video$/);
  if (req.method === 'GET' && h3Video) {
    try {
      const output = await python('h3_video', { job_id: decodeURIComponent(h3Video[1]) });
      return stream(output.path, req, res);
    } catch (error) {
      return json(res, 404, { error: error.message });
    }
  }

  if (req.method === 'GET' && url.pathname === '/api/model-tests') {
    return json(res, 200, await python('model_test_dashboard', {}));
  }
  if (req.method === 'POST' && url.pathname === '/api/model-tests/models') {
    return json(res, 201, await python('register_test_model', await bodyJson(req)));
  }
  if (req.method === 'POST' && url.pathname === '/api/model-tests/workflows') {
    return json(res, 201, await python('register_test_workflow', await bodyJson(req)));
  }
  const workflowInspect = url.pathname.match(
    /^\/api\/model-tests\/workflows\/([^/]+)\/inspect$/,
  );
  if (req.method === 'GET' && workflowInspect) {
    return json(res, 200, await python('inspect_test_workflow', {
      workflow_profile_id: decodeURIComponent(workflowInspect[1]),
    }));
  }
  if (req.method === 'POST' && url.pathname === '/api/model-tests/adapters') {
    return json(res, 201, await python('register_test_adapter', await bodyJson(req)));
  }
  const caseAssets = url.pathname.match(/^\/api\/model-tests\/cases\/([^/]+)\/assets$/);
  if (caseAssets && req.method === 'POST') {
    const form = await formData(req);
    const folder = join(TMP, randomUUID());
    await mkdir(folder, { recursive: true });
    try {
      const file = form.get('file');
      return json(res, 201, await python('save_model_test_asset', {
        case_version_id: decodeURIComponent(caseAssets[1]),
        role: String(form.get('role') || ''),
        upload_path: await saveUpload(file, folder),
        original_name: file?.name || 'reference.png',
      }));
    } finally {
      await rm(folder, { recursive: true, force: true });
    }
  }
  if (caseAssets && req.method === 'DELETE') {
    return json(res, 200, await python('unlink_model_test_asset', {
      case_version_id: decodeURIComponent(caseAssets[1]),
      ...(await bodyJson(req)),
    }));
  }
  const sharedAsset = url.pathname.match(
    /^\/api\/model-tests\/r2v\/shared-assets\/([^/]+)$/,
  );
  if (sharedAsset && req.method === 'POST') {
    const form = await formData(req);
    const folder = join(TMP, randomUUID());
    await mkdir(folder, { recursive: true });
    try {
      const file = form.get('file');
      return json(res, 201, await python('save_r2v_shared_asset', {
        shared_asset_key: decodeURIComponent(sharedAsset[1]),
        upload_path: await saveUpload(file, folder),
        original_name: file?.name || 'reference.png',
      }));
    } finally {
      await rm(folder, { recursive: true, force: true });
    }
  }
  if (sharedAsset && req.method === 'DELETE') {
    return json(res, 200, await python('unlink_r2v_shared_asset', {
      shared_asset_key: decodeURIComponent(sharedAsset[1]),
    }));
  }
  const assetFile = url.pathname.match(/^\/api\/model-tests\/assets\/([^/]+)\/file$/);
  if (req.method === 'GET' && assetFile) {
    try {
      const output = await python('model_test_asset_file', {
        asset_id: decodeURIComponent(assetFile[1]),
      });
      return stream(output.path, req, res, { cacheSeconds: 86400 });
    } catch (error) {
      return json(res, 404, { error: error.message });
    }
  }
  if (req.method === 'POST' && url.pathname === '/api/model-tests/sessions') {
    return json(res, 201, await python('create_model_test_session', await bodyJson(req)));
  }
  const session = url.pathname.match(/^\/api\/model-tests\/sessions\/([^/]+)$/);
  if (req.method === 'DELETE' && session) {
    return json(res, 200, await python('delete_model_test_session', {
      session_id: decodeURIComponent(session[1]),
    }));
  }
  const preflight = url.pathname.match(
    /^\/api\/model-tests\/sessions\/([^/]+)\/preflight$/,
  );
  if (req.method === 'POST' && preflight) {
    return json(res, 200, await python('preflight_model_test_session', {
      session_id: decodeURIComponent(preflight[1]),
    }));
  }
  const sessionQueue = url.pathname.match(/^\/api\/model-tests\/sessions\/([^/]+)\/queue$/);
  if (req.method === 'POST' && sessionQueue) {
    return json(res, 201, await python('queue_model_test_session', {
      session_id: decodeURIComponent(sessionQueue[1]),
    }));
  }
  const aiReview = url.pathname.match(
    /^\/api\/model-tests\/sessions\/([^/]+)\/ai-review$/,
  );
  if (req.method === 'POST' && aiReview) {
    return json(res, 201, await python('queue_model_test_ai_review', {
      session_id: decodeURIComponent(aiReview[1]),
    }));
  }
  if (req.method === 'DELETE' && aiReview) {
    return json(res, 200, await python('cancel_model_test_ai_review', {
      session_id: decodeURIComponent(aiReview[1]),
    }));
  }
  const sessionResults = url.pathname.match(
    /^\/api\/model-tests\/sessions\/([^/]+)\/results$/,
  );
  if (req.method === 'GET' && sessionResults) {
    return json(res, 200, await python('model_test_session_results', {
      session_id: decodeURIComponent(sessionResults[1]),
    }));
  }
  const runReview = url.pathname.match(/^\/api\/model-tests\/runs\/([^/]+)\/review$/);
  if (runReview && req.method === 'GET') {
    return json(res, 200, await python('model_test_run_review', {
      run_id: decodeURIComponent(runReview[1]),
    }));
  }
  if (runReview && req.method === 'PUT') {
    return json(res, 200, await python('model_test_run_review', {
      run_id: decodeURIComponent(runReview[1]),
      review: await bodyJson(req),
    }));
  }
  if (req.method === 'GET' && url.pathname === '/api/model-tests/comparison') {
    return json(res, 200, await python('model_test_comparison', {}));
  }
  if (req.method === 'GET' && url.pathname === '/api/model-tests/analysis') {
    return json(res, 200, await python('model_test_analysis', {
      model_id: String(url.searchParams.get('model_id') || ''),
      workflow_profile_id: String(url.searchParams.get('workflow_profile_id') || ''),
    }));
  }
  if (req.method === 'POST' && url.pathname === '/api/model-tests/policies') {
    return json(res, 201, await python('save_model_test_policy', await bodyJson(req)));
  }
  const policy = url.pathname.match(/^\/api\/model-tests\/policies\/([^/]+)$/);
  if (req.method === 'PATCH' && policy) {
    return json(res, 200, await python('set_model_test_policy_active', {
      policy_id: decodeURIComponent(policy[1]),
      ...(await bodyJson(req)),
    }));
  }
  const followup = url.pathname.match(
    /^\/api\/model-tests\/sessions\/([^/]+)\/followup$/,
  );
  if (req.method === 'POST' && followup) {
    return json(res, 201, await python('create_model_test_followup', {
      source_session_id: decodeURIComponent(followup[1]),
      ...(await bodyJson(req)),
    }));
  }
  if (req.method === 'GET' && url.pathname === '/api/model-tests/export') {
    const output = await python('export_model_tests', {
      format: String(url.searchParams.get('format') || 'json'),
    });
    res.setHeader('content-disposition', `attachment; filename="${output.filename}"`);
    return stream(output.path, req, res, { cacheSeconds: 0 });
  }

  const jobVideo = url.pathname.match(/^\/api\/jobs\/([^/]+)\/video$/);
  if (req.method === 'GET' && jobVideo) {
    try {
      const video = await resolveJobVideoPath(decodeURIComponent(jobVideo[1]));
      if (!video) return json(res, 404, { error: '영상 출력이 없습니다.' });
      return stream(video, req, res);
    } catch (error) {
      return json(res, 404, { error: error.message });
    }
  }
  const videoThumbnail = url.pathname.match(
    /^\/api\/jobs\/([^/]+)\/(?:video-thumbnail|thumbnail)$/,
  );
  if (req.method === 'GET' && videoThumbnail) {
    return serveVideoThumbnail(decodeURIComponent(videoThumbnail[1]), req, res);
  }

  if (req.method === 'GET') {
    const rel = url.pathname === '/' ? 'index.html' : url.pathname.slice(1);
    const path = normalize(join(PUBLIC, rel));
    if (!path.startsWith(PUBLIC)) return json(res, 403, { error: 'forbidden' });
    return stream(path, req, res, { staticFile: true });
  }
  return json(res, 404, { error: 'not found' });
}

const server = http.createServer((req, res) => {
  route(req, res).catch((error) => {
    console.error(`[request_error] ${req.method} ${req.url}: ${safeText(error.stack || error.message)}`);
    if (!res.headersSent) json(res, 500, { error: safeText(error.message || error) });
    else res.destroy();
  });
});
server.on('clientError', (error, socket) => {
  console.error(`[client_error] ${safeText(error.message)}`);
  if (socket.writable) socket.end('HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n');
});
server.listen(PORT, HOST, () => {
  console.log(`H3 video UI http://${HOST}:${PORT}`);
});
