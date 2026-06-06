'use strict';

let currentRole = null;
const blobCache = new Map();

document.addEventListener('DOMContentLoaded', () => {
  loadImages();
});

async function login(e) {
  e.preventDefault();
  const password = document.getElementById('login-password').value;
  const resp = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  });
  if (resp.ok) {
    const { role } = await resp.json();
    applyRole(role);
    document.getElementById('login-password').value = '';
    document.getElementById('login-error').textContent = '';
    loadImages();
  } else {
    const data = await resp.json().catch(() => ({}));
    document.getElementById('login-error').textContent = data.detail || 'Invalid password';
  }
}

async function logout() {
  await fetch('/auth/logout', { method: 'POST' });
  applyRole(null);
  setOnline(false);
  document.getElementById('gallery').innerHTML = '';
  document.getElementById('img-count').textContent = '';
}

function applyRole(role) {
  currentRole = role;
  const isAdmin = role === 'admin';
  const isAuthed = role !== null;

  document.getElementById('login-overlay').style.display = isAuthed ? 'none' : 'flex';
  document.getElementById('logout-btn').style.display = isAuthed ? '' : 'none';
  document.getElementById('upload-zone').style.display = isAdmin ? '' : 'none';
  document.getElementById('push-daily-btn').style.display = isAuthed ? '' : 'none';

  if (isAdmin) setupUpload();
}

async function loadImages() {
  try {
    const resp = await fetch('/api/images');
    if (resp.status === 401) {
      applyRole(null);
      return;
    }
    if (!resp.ok) throw new Error(resp.status);
    const images = await resp.json();
    setOnline(true);
    renderGallery(images);
  } catch (e) {
    setOnline(false);
    toast(`Failed to load images: ${e.message}`, 'err');
  }
}

function renderGallery(images) {
  const gallery = document.getElementById('gallery');
  document.getElementById('img-count').textContent =
    images.length === 0 ? '' : `${images.length} image${images.length === 1 ? '' : 's'}`;

  const ids = new Set(images.map(i => i.id));
  for (const [id, url] of blobCache) {
    if (!ids.has(id)) { URL.revokeObjectURL(url); blobCache.delete(id); }
  }

  gallery.innerHTML = '';

  if (images.length === 0) {
    gallery.innerHTML = '<div class="empty"><p>No images yet — upload one above.</p></div>';
    return;
  }

  const todayIdx = dailyIndex(images.length);
  const isAdmin = currentRole === 'admin';

  images.forEach((img, idx) => {
    const isToday = idx === todayIdx;
    const card = document.createElement('div');
    card.className = 'card';
    card.dataset.id = img.id;
    card.innerHTML = `
      <div class="thumb" data-lazy="${img.id}">
        ${isToday ? '<span class="badge">TODAY</span>' : ''}
        <span class="placeholder">Loading…</span>
      </div>
      <div class="card-body">
        <div class="card-name" title="${esc(img.original_name)}">${esc(img.original_name)}</div>
        <div class="card-date">${fmtDate(img.upload_date)}</div>
      </div>
      <div class="card-actions">
        <button class="btn btn-push btn-sm" onclick="pushToFrame(${img.id})">Push</button>
        ${isAdmin ? `<button class="btn btn-danger btn-sm" onclick="deleteImage(${img.id}, this)">Delete</button>` : ''}
      </div>
    `;
    gallery.appendChild(card);
  });

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const el = entry.target;
      const id = parseInt(el.dataset.lazy);
      observer.unobserve(el);
      loadThumb(id, el);
    });
  }, { rootMargin: '200px' });

  document.querySelectorAll('.thumb[data-lazy]').forEach(el => observer.observe(el));
}

async function loadThumb(id, container) {
  if (blobCache.has(id)) { showThumb(container, blobCache.get(id)); return; }
  try {
    const resp = await fetch(`/api/images/${id}`);
    if (!resp.ok) return;
    const url = URL.createObjectURL(await resp.blob());
    blobCache.set(id, url);
    showThumb(container, url);
  } catch (_) { /* leave placeholder */ }
}

function showThumb(container, url) {
  const badge = container.querySelector('.badge');
  container.innerHTML = `<img src="${url}" alt="" loading="lazy">`;
  if (badge) container.appendChild(badge);
}

async function deleteImage(id, btn) {
  if (!confirm('Delete this image?')) return;
  btn.disabled = true;
  try {
    const resp = await fetch(`/api/images/${id}`, { method: 'DELETE' });
    if (resp.status === 204) {
      if (blobCache.has(id)) { URL.revokeObjectURL(blobCache.get(id)); blobCache.delete(id); }
      toast('Image deleted', 'ok');
      await loadImages();
    } else {
      throw new Error(resp.status);
    }
  } catch (e) {
    toast(`Delete failed: ${e.message}`, 'err');
    btn.disabled = false;
  }
}

async function pushToFrame(imageId) {
  const btn = document.getElementById('push-daily-btn');
  btn.disabled = true;
  const body = imageId != null ? { image_id: imageId } : {};
  try {
    const resp = await fetch('/api/push', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (resp.ok) {
      toast(imageId ? 'Image pushed to frame' : 'Daily image pushed to frame', 'ok');
    } else {
      const data = await resp.json().catch(() => ({}));
      throw new Error(data.detail || resp.status);
    }
  } catch (e) {
    toast(`Push failed: ${e.message}`, 'err');
  } finally {
    btn.disabled = false;
  }
}

let uploadSetup = false;
function setupUpload() {
  if (uploadSetup) return;
  uploadSetup = true;

  const zone = document.getElementById('upload-zone');
  const input = document.getElementById('file-input');

  document.getElementById('browse-trigger').addEventListener('click', () => input.click());
  zone.addEventListener('click', e => { if (e.target.id !== 'browse-trigger') input.click(); });
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('over'));
  zone.addEventListener('drop', e => {
    e.preventDefault(); zone.classList.remove('over');
    uploadFiles(e.dataTransfer.files);
  });
  input.addEventListener('change', () => { uploadFiles(input.files); input.value = ''; });
}

async function uploadFiles(files) {
  const progress = document.getElementById('progress');
  const arr = Array.from(files);

  const items = arr.map(file => {
    const el = document.createElement('div');
    el.className = 'prog-item';
    el.textContent = `Uploading ${file.name}…`;
    progress.appendChild(el);
    return { file, el };
  });

  await Promise.all(items.map(async ({ file, el }) => {
    try {
      const fd = new FormData();
      fd.append('file', file);
      const resp = await fetch('/api/images', { method: 'POST', body: fd });
      if (resp.status === 201) {
        el.textContent = `✓ ${file.name}`;
        el.classList.add('ok');
      } else {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.detail || resp.status);
      }
    } catch (e) {
      el.textContent = `✗ ${file.name}: ${e.message}`;
      el.classList.add('err');
    }
    setTimeout(() => el.remove(), 4000);
  }));

  await loadImages();
}

// FNV-1a approximation instead of sha256 because SubtleCrypto is async.
// Only used for the "TODAY" badge — server result is authoritative.
function dailyIndex(count) {
  const today = new Date().toISOString().slice(0, 10);
  let h = 2166136261;
  for (let i = 0; i < today.length; i++) {
    h ^= today.charCodeAt(i);
    h = (Math.imul(h, 16777619) >>> 0);
  }
  return h % count;
}

function setOnline(v) {
  document.getElementById('dot').className = `dot ${v ? 'online' : 'offline'}`;
}

function fmtDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function toast(msg, type = 'ok') {
  const c = document.getElementById('toast-container');
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = msg;
  c.appendChild(t);
  requestAnimationFrame(() => requestAnimationFrame(() => t.classList.add('show')));
  setTimeout(() => {
    t.classList.remove('show');
    setTimeout(() => t.remove(), 300);
  }, 3500);
}
