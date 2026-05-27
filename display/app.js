// ============================================================
// FILE: display/app.js
//
// PURPOSE:
//   WebSocket client and UI controller for Amma's iPad display.
//   Manages four screens: Home, Gallery, Gallery Fullscreen,
//   and Interrupt (new message overlay).
//
//   Bug fixes in this version (2026-05-25):
//     Bug 4 — videoContainer click is stopped so native controls
//              do not bubble up to the ack listener.
//     Bug 5 — console.log added at every step of storeItem →
//              updateBadges flow to confirm execution; badge-inline
//              element referenced by same ID (no JS change needed,
//              CSS change made it inline and always visible).
//     Bug 6 — Single #mic-button DOM element (position:fixed in CSS),
//              all homeMicEl references removed.
//
//   Screen flow:
//     Home ──[📷/🎥 button]──→ Gallery ──[tap thumb]──→ Fullscreen
//     Fullscreen ──[tap]──→ Gallery
//     Gallery ──[🏠]──→ Home
//     Any screen ──[new WS message]──→ Interrupt ──[tap]──→ previous
//
//   Gallery storage:
//     Last 20 photos + last 10 videos in memory.
//     Resets on page refresh (intentional — no localStorage).
//
// INPUTS:
//   - WebSocket messages from display_server.py
//
// OUTPUTS:
//   - WebSocket messages: ack, heartbeat, voice_reply
//   - DOM: screen switching, gallery grid render, badge updates
//
// DEPENDENCIES:
//   - display/index.html, display/style.css
//   - MediaRecorder API, WebSocket API (Safari built-in)
//
// CALLED BY:
//   - display/index.html (<script src="app.js">)
//
// AUTHOR: AmmaHome
// LAST UPDATED: 2026-05-27 (single-port: ws path /ws, wss on https)
// ============================================================

'use strict';

// ── WebSocket config ──────────────────────────────────────────

// Use the same host:port the page was loaded from, with wss:// on https.
// This works on localhost, on the home Wi-Fi, and on Railway (single port).
const WS_PROTOCOL = location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_URL      = `${WS_PROTOCOL}//${location.host}/ws`;

const HEARTBEAT_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes
const RECONNECT_DELAY_MS    = 3000;

// ── Gallery limits ────────────────────────────────────────────

const PHOTO_LIMIT = 20;
const VIDEO_LIMIT = 10;

// ── Gallery state ─────────────────────────────────────────────

/**
 * Photo items: { id, sender, data, mime_type, timestamp, viewed }
 * Newest first. Max PHOTO_LIMIT entries.
 */
const photoGallery = [];

/**
 * Video items: same shape as photoGallery.
 * Max VIDEO_LIMIT entries.
 */
const videoGallery = [];

let unreadPhotos = 0;
let unreadVideos = 0;

// ── Screen navigation state ───────────────────────────────────

// 'home' | 'gallery' | 'fullscreen' | 'interrupt'
let currentScreen = 'home';
// 'photo' | 'video'
let galleryMode = 'photo';
// The gallery item currently shown in the fullscreen screen
let selectedItem = null;

// Where to return after an interrupt is dismissed
let preInterruptScreen       = 'home';
let preInterruptGalleryMode  = 'photo';
let preInterruptSelectedItem = null;

// ── WebSocket / recording state ───────────────────────────────

let socket           = null;
let heartbeatTimer   = null;
let reconnectTimer   = null;
let mediaRecorder    = null;
let audioChunks      = [];
let currentMessageId = null;

// ── Safari audio unlock state ─────────────────────────────────
// Safari blocks audio.play() until the user has touched the page.
// audioUnlocked flips to true after the first user gesture fires
// unlockAudio(). All audio.play() calls succeed after that.
let audioUnlocked = false;

// Blob URLs — revoked before creating new ones to prevent memory leaks
let interruptBlobUrl  = null;
let fullscreenBlobUrl = null;
let galleryBlobUrls   = [];

// ── DOM references ────────────────────────────────────────────

const waitingScreen      = document.getElementById('waiting-screen');
const galleryScreen      = document.getElementById('gallery-screen');
const fullscreenScreen   = document.getElementById('fullscreen-screen');
const messageScreen      = document.getElementById('message-screen');

const galleryGrid        = document.getElementById('gallery-grid');
const galleryTitle       = document.getElementById('gallery-title');

const fullscreenSender   = document.getElementById('fullscreen-sender');
const fullscreenFooter   = document.getElementById('fullscreen-footer');
const fullscreenImg      = document.getElementById('fullscreen-img');
const fullscreenVideo    = document.getElementById('fullscreen-video');

// Bug 5: badge elements referenced by same IDs; now inline in button (CSS fix)
const badgePhotos        = document.getElementById('badge-photos');
const badgeVideos        = document.getElementById('badge-videos');

const senderName         = document.getElementById('sender-name');
const photoContainer     = document.getElementById('photo-container');
const photoImg           = document.getElementById('photo-img');
const videoContainer     = document.getElementById('video-container');
const videoPlayer        = document.getElementById('video-player');
const textContainer      = document.getElementById('text-container');
const textMessage        = document.getElementById('text-message');
const audioPlayer        = document.getElementById('audio-player');

// Bug 6: single fixed mic button — no separate homeMicEl
const micButton          = document.getElementById('mic-button');
const recordingIndicator = document.getElementById('recording-indicator');

// ── SECTION: WebSocket ────────────────────────────────────────

/**
 * Opens the WebSocket connection to the AmmaHome server.
 *
 * Steps:
 *   1. Create a new WebSocket instance
 *   2. On open: clear reconnect timer, start heartbeat
 *   3. On close: stop heartbeat, schedule reconnect
 *   4. On message: route to handleServerMessage
 */
function connect() {
  console.log(`[AmmaHome] Connecting to ${WS_URL}...`);  // e.g. ws://192.168.0.10:8080/ws
  socket = new WebSocket(WS_URL);

  socket.addEventListener('open', () => {
    console.log('[AmmaHome] Connected to server');
    clearTimeout(reconnectTimer);
    startHeartbeat();
  });

  socket.addEventListener('close', (event) => {
    console.warn(`[AmmaHome] Disconnected (code=${event.code}) — reconnecting in ${RECONNECT_DELAY_MS / 1000}s`);
    stopHeartbeat();
    reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
  });

  socket.addEventListener('error', () => {
    // 'close' fires right after 'error' and triggers reconnect
  });

  socket.addEventListener('message', (event) => {
    handleServerMessage(event.data);
  });
}

/**
 * Parses and routes an incoming WebSocket message from the server.
 *
 * Steps:
 *   1. Parse JSON
 *   2. Dispatch by type
 *
 * @param {string} rawData - Raw JSON string from the server
 */
function handleServerMessage(rawData) {
  let payload;
  try {
    payload = JSON.parse(rawData);
  } catch (err) {
    console.error('[AmmaHome] Invalid JSON from server:', err);
    return;
  }

  console.log(`[AmmaHome] Received type=${payload.type} sender=${payload.sender} id=${payload.message_id}`);

  switch (payload.type) {
    case 'photo':  showPhoto(payload); break;
    case 'video':  showVideo(payload); break;
    case 'voice':  showVoice(payload); break;
    case 'text':   showText(payload);  break;
    case 'chime':  playChime();        break;
    case 'clear':  showHome();         break;
    default:
      console.warn(`[AmmaHome] Unknown message type: ${payload.type}`);
  }
}

// ── SECTION: Incoming content handlers ───────────────────────

/**
 * Handles an incoming photo — stores in gallery, shows interrupt.
 *
 * @param {Object} payload - Server payload with type="photo"
 */
function showPhoto(payload) {
  console.log(`[AmmaHome] showPhoto: calling storeItem for message_id=${payload.message_id}`);
  storeItem('photo', payload);
  showInterrupt(payload, 'photo');
}

/**
 * Handles an incoming video — stores in gallery, shows interrupt.
 *
 * @param {Object} payload - Server payload with type="video"
 */
function showVideo(payload) {
  console.log(`[AmmaHome] showVideo: calling storeItem for message_id=${payload.message_id}`);
  storeItem('video', payload);
  showInterrupt(payload, 'video');
}

/**
 * Handles an incoming voice message — plays on interrupt screen (not stored in gallery).
 *
 * @param {Object} payload - Server payload with type="voice"
 */
function showVoice(payload) {
  showInterrupt(payload, 'voice');
}

/**
 * Handles an incoming text message — shows on interrupt screen (not stored in gallery).
 *
 * @param {Object} payload - Server payload with type="text"
 */
function showText(payload) {
  showInterrupt(payload, 'text');
}

// ── SECTION: Interrupt screen ─────────────────────────────────

/**
 * Shows the interrupt screen over whatever Amma is currently viewing.
 *
 * Steps:
 *   1. Save the current screen so we can return to it after ack
 *   2. Set currentMessageId and sender name in control bar
 *   3. Load the content into the media pane
 *   4. Switch to the interrupt screen and play chime
 *
 * @param {Object} payload - The full server payload
 * @param {string} type    - 'photo' | 'video' | 'voice' | 'text'
 */
function showInterrupt(payload, type) {
  if (currentScreen !== 'interrupt') {
    preInterruptScreen       = currentScreen;
    preInterruptGalleryMode  = galleryMode;
    preInterruptSelectedItem = selectedItem;
  }

  currentMessageId = payload.message_id;
  senderName.textContent = payload.sender;

  // Revoke any previous interrupt blob URL
  if (interruptBlobUrl) {
    URL.revokeObjectURL(interruptBlobUrl);
    interruptBlobUrl = null;
  }

  hideAllMedia();

  if (type === 'photo') {
    photoImg.src = `data:${payload.mime_type};base64,${payload.data}`;
    photoContainer.classList.remove('hidden');

  } else if (type === 'video') {
    const blob = base64ToBlob(payload.data, payload.mime_type);
    interruptBlobUrl = URL.createObjectURL(blob);
    videoPlayer.src = interruptBlobUrl;
    videoContainer.classList.remove('hidden');
    videoPlayer.play().catch(() => {});

  } else if (type === 'voice') {
    textMessage.textContent = '🎙️ Voice message';
    textContainer.classList.remove('hidden');
    const voiceBlob = base64ToBlob(payload.data, payload.mime_type);
    interruptBlobUrl = URL.createObjectURL(voiceBlob);
    playAudio(interruptBlobUrl, 'voice');

  } else if (type === 'text') {
    console.log(`[AmmaHome] showInterrupt: text message received, data="${payload.data}"`);
    textMessage.textContent = payload.data;
    textContainer.classList.remove('hidden');

    console.log(`[AmmaHome] showInterrupt: tts_audio present=${!!payload.tts_audio} length=${payload.tts_audio ? payload.tts_audio.length : 0}`);
    if (payload.tts_audio) {
      console.log('[AmmaHome] showInterrupt: decoding tts_audio base64 → Blob → Object URL');
      const ttsBlob = base64ToBlob(payload.tts_audio, 'audio/mpeg');
      console.log(`[AmmaHome] showInterrupt: ttsBlob size=${ttsBlob.size} bytes`);
      interruptBlobUrl = URL.createObjectURL(ttsBlob);
      playAudio(interruptBlobUrl, 'TTS');
    } else {
      console.warn('[AmmaHome] showInterrupt: no tts_audio in payload — nothing to play');
    }
  }

  switchToScreen(messageScreen);
  currentScreen = 'interrupt';
  playChime();
}

/**
 * Handles a tap on the interrupt screen — sends ack and returns to previous screen.
 *
 * Steps:
 *   1. Guard against taps with no active message
 *   2. Mark the item as viewed (updates badge)
 *   3. Send ack to server
 *   4. Stop any media
 *   5. Return to the pre-interrupt screen
 */
function handleInterruptTap() {
  if (!currentMessageId) return;

  markViewed(currentMessageId);

  sendToServer({
    type: 'ack',
    message_id: currentMessageId,
    timestamp: new Date().toISOString(),
  });

  console.log(`[AmmaHome] Ack sent for message: ${currentMessageId}`);
  currentMessageId = null;

  videoPlayer.pause();
  audioPlayer.pause();

  returnFromInterrupt();
}

/**
 * Returns to the screen Amma was on before the interrupt.
 *
 * Steps:
 *   1. Read and reset the pre-interrupt navigation state
 *   2. Navigate to gallery, fullscreen, or home accordingly
 */
function returnFromInterrupt() {
  const dest     = preInterruptScreen;
  const destMode = preInterruptGalleryMode;
  const destItem = preInterruptSelectedItem;

  preInterruptScreen       = 'home';
  preInterruptGalleryMode  = 'photo';
  preInterruptSelectedItem = null;

  if (dest === 'gallery') {
    openGallery(destMode);
  } else if (dest === 'fullscreen' && destItem) {
    openFullscreen(destItem);
  } else {
    showHome();
  }
}

// ── SECTION: Home screen ──────────────────────────────────────

/**
 * Navigates to the home (idle) screen and clears media state.
 *
 * Steps:
 *   1. Reset all state variables
 *   2. Clear media elements
 *   3. Switch to the waiting screen element
 */
function showHome() {
  currentScreen    = 'home';
  selectedItem     = null;
  currentMessageId = null;

  hideAllMedia();
  videoPlayer.src = '';
  audioPlayer.src = '';

  switchToScreen(waitingScreen);
}

// ── SECTION: Gallery screen ───────────────────────────────────

/**
 * Opens the gallery screen for the given media type.
 *
 * Steps:
 *   1. Set galleryMode and currentScreen
 *   2. Update the title text
 *   3. Render thumbnails
 *   4. Switch to gallery screen
 *
 * @param {string} mode - 'photo' | 'video'
 */
function openGallery(mode) {
  galleryMode   = mode;
  currentScreen = 'gallery';
  galleryTitle.textContent = mode === 'photo' ? '📷 Photos' : '🎥 Videos';
  renderGallery();
  switchToScreen(galleryScreen);
}

/**
 * Renders the thumbnail grid for the current galleryMode.
 *
 * Steps:
 *   1. Revoke previous gallery blob URLs
 *   2. Clear the grid innerHTML
 *   3. Show empty state if no items
 *   4. Create a thumbnail div for each item (image or video)
 *   5. Attach click listener to each thumbnail
 *
 * @returns {void}
 */
function renderGallery() {
  galleryBlobUrls.forEach(url => URL.revokeObjectURL(url));
  galleryBlobUrls = [];

  const gallery = galleryMode === 'photo' ? photoGallery : videoGallery;
  galleryGrid.innerHTML = '';

  if (gallery.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'gallery-empty';
    empty.textContent = galleryMode === 'photo' ? '📷\nNo photos yet' : '🎥\nNo videos yet';
    galleryGrid.appendChild(empty);
    return;
  }

  gallery.forEach(item => {
    const thumb = document.createElement('div');
    thumb.className = 'gallery-thumb' + (item.viewed ? '' : ' unread');

    if (item.mime_type.startsWith('image/')) {
      const img = document.createElement('img');
      img.src = `data:${item.mime_type};base64,${item.data}`;
      img.alt = `Photo from ${item.sender}`;
      thumb.appendChild(img);
    } else {
      const vid = document.createElement('video');
      vid.preload = 'metadata';
      vid.muted   = true;
      const blob = base64ToBlob(item.data, item.mime_type);
      const blobUrl = URL.createObjectURL(blob);
      galleryBlobUrls.push(blobUrl);
      vid.src = blobUrl;
      thumb.appendChild(vid);

      const playIcon = document.createElement('div');
      playIcon.className = 'thumb-play-icon';
      playIcon.textContent = '▶';
      thumb.appendChild(playIcon);
    }

    const overlay = document.createElement('div');
    overlay.className = 'thumb-overlay';
    const senderEl = document.createElement('div');
    senderEl.className = 'thumb-sender';
    senderEl.textContent = item.sender;
    overlay.appendChild(senderEl);
    thumb.appendChild(overlay);

    if (!item.viewed) {
      const pill = document.createElement('div');
      pill.className = 'thumb-new-pill';
      pill.textContent = 'NEW';
      thumb.appendChild(pill);
    }

    thumb.addEventListener('click', (e) => {
      e.stopPropagation();
      openFullscreen(item);
    });

    galleryGrid.appendChild(thumb);
  });
}

// ── SECTION: Gallery fullscreen ───────────────────────────────

/**
 * Opens a single gallery item in the fullscreen viewer.
 *
 * Steps:
 *   1. Revoke previous fullscreen blob URL
 *   2. Set selectedItem and currentScreen
 *   3. Load photo or video into the fullscreen elements
 *   4. Mark item as viewed and switch screen
 *
 * @param {Object} item - A gallery item object
 */
function openFullscreen(item) {
  if (fullscreenBlobUrl) {
    URL.revokeObjectURL(fullscreenBlobUrl);
    fullscreenBlobUrl = null;
  }

  selectedItem  = item;
  currentScreen = 'fullscreen';

  fullscreenSender.textContent = item.sender;

  if (item.mime_type.startsWith('image/')) {
    fullscreenImg.src = `data:${item.mime_type};base64,${item.data}`;
    fullscreenImg.classList.remove('hidden');
    fullscreenVideo.classList.add('hidden');
    fullscreenVideo.src = '';
  } else {
    const blob = base64ToBlob(item.data, item.mime_type);
    fullscreenBlobUrl = URL.createObjectURL(blob);
    fullscreenVideo.src = fullscreenBlobUrl;
    fullscreenVideo.classList.remove('hidden');
    fullscreenImg.classList.add('hidden');
    fullscreenImg.src = '';
    fullscreenVideo.play().catch(() => {});
  }

  markViewed(item.id);
  switchToScreen(fullscreenScreen);
}

/**
 * Returns from the fullscreen viewer back to the gallery.
 *
 * Steps:
 *   1. Pause any video
 *   2. Open the gallery in the same mode
 */
function handleFullscreenTap() {
  fullscreenVideo.pause();
  openGallery(galleryMode);
}

/**
 * Shows the fullscreen footer overlay (tap-to-go-back hint).
 * Called when a fullscreen video is paused, ended, or a photo is shown.
 */
function showFullscreenFooter() {
  fullscreenFooter.classList.remove('video-playing');
}

/**
 * Hides the fullscreen footer overlay while video is actively playing.
 * Called on the fullscreen video 'play' event.
 */
function hideFullscreenFooter() {
  fullscreenFooter.classList.add('video-playing');
}

// ── SECTION: Gallery state management ────────────────────────

/**
 * Stores an incoming media item in the appropriate gallery array.
 *
 * Bug 5 fix: console.log added at each step so the flow is
 * visible in the browser console during testing.
 *
 * Steps:
 *   1. Skip if message_id already stored (dedup)
 *   2. Build item object and prepend (newest first)
 *   3. Trim to configured limit
 *   4. Increment unread counter
 *   5. Call updateBadges()
 *
 * @param {string} type    - 'photo' | 'video'
 * @param {Object} payload - The server payload
 */
function storeItem(type, payload) {
  const gallery = type === 'photo' ? photoGallery : videoGallery;
  const limit   = type === 'photo' ? PHOTO_LIMIT  : VIDEO_LIMIT;

  console.log(`[AmmaHome] storeItem: type=${type} id=${payload.message_id} current_count=${gallery.length}`);

  // Deduplicate
  if (gallery.some(item => item.id === payload.message_id)) {
    console.log(`[AmmaHome] storeItem: SKIPPED — already stored id=${payload.message_id}`);
    return;
  }

  const item = {
    id:        payload.message_id,
    sender:    payload.sender,
    data:      payload.data,
    mime_type: payload.mime_type,
    timestamp: payload.timestamp,
    viewed:    false,
  };

  gallery.unshift(item);
  console.log(`[AmmaHome] storeItem: stored OK, gallery now has ${gallery.length} items`);

  if (gallery.length > limit) {
    gallery.pop();
    console.log(`[AmmaHome] storeItem: trimmed to limit=${limit}`);
  }

  if (type === 'photo') {
    unreadPhotos++;
    console.log(`[AmmaHome] storeItem: unreadPhotos is now ${unreadPhotos}`);
  } else {
    unreadVideos++;
    console.log(`[AmmaHome] storeItem: unreadVideos is now ${unreadVideos}`);
  }

  updateBadges();
}

/**
 * Marks a gallery item as viewed and decrements the unread counter.
 *
 * Steps:
 *   1. Search photo gallery — if found and unread, mark and decrement
 *   2. Otherwise search video gallery
 *   3. Call updateBadges
 *
 * @param {string} id - The message_id of the item to mark as viewed
 */
function markViewed(id) {
  const photo = photoGallery.find(item => item.id === id);
  if (photo && !photo.viewed) {
    photo.viewed = true;
    unreadPhotos = Math.max(0, unreadPhotos - 1);
    console.log(`[AmmaHome] markViewed: photo id=${id} marked viewed, unreadPhotos=${unreadPhotos}`);
    updateBadges();
    return;
  }

  const video = videoGallery.find(item => item.id === id);
  if (video && !video.viewed) {
    video.viewed = true;
    unreadVideos = Math.max(0, unreadVideos - 1);
    console.log(`[AmmaHome] markViewed: video id=${id} marked viewed, unreadVideos=${unreadVideos}`);
    updateBadges();
  }
}

/**
 * Updates the badge count elements on the home screen buttons.
 *
 * Bug 5 fix: badges are now inline inside the button (no absolute
 * positioning), so they are never clipped. Console.log confirms values.
 *
 * Steps:
 *   1. Photos badge: show count if > 0, hide if 0
 *   2. Videos badge: show count if > 0, hide if 0
 */
function updateBadges() {
  console.log(`[AmmaHome] updateBadges: photos=${unreadPhotos} videos=${unreadVideos}`);

  if (unreadPhotos > 0) {
    badgePhotos.textContent = unreadPhotos;
    badgePhotos.classList.remove('hidden');
  } else {
    badgePhotos.classList.add('hidden');
  }

  if (unreadVideos > 0) {
    badgeVideos.textContent = unreadVideos;
    badgeVideos.classList.remove('hidden');
  } else {
    badgeVideos.classList.add('hidden');
  }
}

// ── SECTION: Screen switching ─────────────────────────────────

/**
 * Shows one screen and hides all others.
 * Also shows the mic button only on the home screen.
 *
 * Steps:
 *   1. Remove 'active' from all four screen elements
 *   2. Add 'active' to the target element
 *   3. Show mic if target is home; hide it otherwise
 *
 * @param {HTMLElement} targetEl - The screen element to activate
 */
function switchToScreen(targetEl) {
  [waitingScreen, galleryScreen, fullscreenScreen, messageScreen].forEach(el => {
    el.classList.remove('active');
  });
  targetEl.classList.add('active');

  // Mic is home-screen only
  if (targetEl === waitingScreen) {
    micButton.classList.remove('mic-hidden');
  } else {
    micButton.classList.add('mic-hidden');
  }
}

// ── SECTION: Chime ────────────────────────────────────────────

/**
 * Briefly flashes the screen as a visual chime cue.
 *
 * Steps:
 *   1. Add 'chime' class to body (CSS animation runs)
 *   2. Remove it after animation completes
 */
function playChime() {
  document.body.classList.add('chime');
  setTimeout(() => document.body.classList.remove('chime'), 1500);
  console.log('[AmmaHome] Chime played');
}

// ── SECTION: Voice recording ──────────────────────────────────

/**
 * Starts recording Amma's voice when she holds the mic button.
 *
 * Steps:
 *   1. Request microphone permission
 *   2. Create MediaRecorder and collect chunks
 *   3. Show recording indicator; style mic button red
 */
async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks  = [];

    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
    mediaRecorder.addEventListener('dataavailable', event => {
      if (event.data.size > 0) audioChunks.push(event.data);
    });
    mediaRecorder.addEventListener('stop', sendVoiceReply);
    mediaRecorder.start();

    micButton.classList.add('recording');
    recordingIndicator.classList.remove('hidden');
    console.log('[AmmaHome] Recording started');
  } catch (err) {
    console.error('[AmmaHome] Microphone access denied:', err);
  }
}

/**
 * Stops recording when Amma releases the mic button.
 *
 * Steps:
 *   1. Stop MediaRecorder (fires 'stop' → sendVoiceReply)
 *   2. Stop all mic tracks
 *   3. Reset mic button styling and hide indicator
 */
function stopRecording() {
  if (!mediaRecorder || mediaRecorder.state === 'inactive') return;

  mediaRecorder.stop();
  mediaRecorder.stream.getTracks().forEach(track => track.stop());
  micButton.classList.remove('recording');
  recordingIndicator.classList.add('hidden');
  console.log('[AmmaHome] Recording stopped');
}

/**
 * Encodes Amma's recorded audio as base64 and sends it to the server.
 *
 * Steps:
 *   1. Combine audio chunks into one Blob
 *   2. Convert to base64
 *   3. Send voice_reply payload to server
 */
async function sendVoiceReply() {
  if (audioChunks.length === 0) return;

  const audioBlob   = new Blob(audioChunks, { type: 'audio/webm' });
  const base64Audio = await blobToBase64(audioBlob);

  sendToServer({
    type:      'voice_reply',
    data:      base64Audio,
    timestamp: new Date().toISOString(),
  });

  console.log('[AmmaHome] Voice reply sent to server');
  audioChunks = [];
}

// ── SECTION: Heartbeat ────────────────────────────────────────

/**
 * Starts periodic heartbeat pings after connecting.
 *
 * Steps:
 *   1. Send an immediate heartbeat
 *   2. Set interval for subsequent heartbeats
 */
function startHeartbeat() {
  sendHeartbeat();
  heartbeatTimer = setInterval(sendHeartbeat, HEARTBEAT_INTERVAL_MS);
}

/** Stops the heartbeat timer when disconnected. */
function stopHeartbeat() {
  clearInterval(heartbeatTimer);
  heartbeatTimer = null;
}

/** Sends a single heartbeat ping to the server. */
function sendHeartbeat() {
  sendToServer({ type: 'heartbeat', timestamp: new Date().toISOString() });
  console.debug('[AmmaHome] Heartbeat sent');
}

// ── SECTION: Utilities ────────────────────────────────────────

/**
 * Sends a JSON payload to the server if the socket is open.
 *
 * @param {Object} payload - The object to serialise and send
 */
function sendToServer(payload) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(payload));
  } else {
    console.warn('[AmmaHome] Cannot send — socket not open');
  }
}

/**
 * Converts a base64 string to a Blob.
 *
 * @param {string} base64   - Base64 encoded string
 * @param {string} mimeType - MIME type e.g. "image/jpeg"
 * @returns {Blob}
 */
function base64ToBlob(base64, mimeType) {
  const byteString = atob(base64);
  const byteArray  = new Uint8Array(byteString.length);
  for (let i = 0; i < byteString.length; i++) {
    byteArray[i] = byteString.charCodeAt(i);
  }
  return new Blob([byteArray], { type: mimeType });
}

/**
 * Converts a Blob to a base64 string (without the data: prefix).
 *
 * @param {Blob} blob - The Blob to encode
 * @returns {Promise<string>}
 */
function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result.split(',')[1]);
    reader.onerror   = reject;
    reader.readAsDataURL(blob);
  });
}

/** Hides all media containers inside the interrupt media pane. */
function hideAllMedia() {
  photoContainer.classList.add('hidden');
  videoContainer.classList.add('hidden');
  textContainer.classList.add('hidden');
}

// ── SECTION: Safari audio unlock ─────────────────────────────

/**
 * Unlocks audio on Safari by resuming a silent AudioContext on the
 * first user gesture. Safari blocks audio.play() until this runs.
 *
 * Steps:
 *   1. Guard — do nothing if already unlocked
 *   2. Create an AudioContext and resume it
 *   3. Set audioUnlocked flag so we log this only once
 *
 * Called from a touchstart/click listener on document (see below).
 */
function unlockAudio() {
  if (audioUnlocked) return;
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (AudioCtx) {
      const ctx = new AudioCtx();
      ctx.resume().then(() => {
        console.log('[AmmaHome] unlockAudio: AudioContext resumed — Safari audio unlocked');
      });
    }
    audioUnlocked = true;
    console.log('[AmmaHome] unlockAudio: audio unlock triggered by user gesture');
  } catch (err) {
    console.warn('[AmmaHome] unlockAudio: could not create AudioContext:', err);
  }
}

/**
 * Sets the audio source and plays it, with full diagnostic logging.
 *
 * Steps:
 *   1. Log whether Safari audio is unlocked
 *   2. Set audioPlayer.src to the blob URL
 *   3. Call audioPlayer.play() and log success or rejection reason
 *
 * @param {string} blobUrl   - Object URL created from a Blob
 * @param {string} label     - Short description for log messages (e.g. "TTS", "voice")
 */
function playAudio(blobUrl, label) {
  console.log(`[AmmaHome] playAudio: label=${label} audioUnlocked=${audioUnlocked} blobUrl=${blobUrl}`);
  audioPlayer.src = blobUrl;
  audioPlayer.play()
    .then(() => {
      console.log(`[AmmaHome] playAudio: ${label} playback started OK`);
    })
    .catch((err) => {
      console.error(`[AmmaHome] playAudio: ${label} play() rejected — ${err.name}: ${err.message}`);
      console.error('[AmmaHome] playAudio: Fix — ensure the user has tapped the page at least once before audio arrives (Safari autoplay policy)');
    });
}

// ── SECTION: Event listeners ──────────────────────────────────

// Interrupt screen — tap anywhere on the screen to acknowledge.
messageScreen.addEventListener('click', handleInterruptTap);

// Bug 4 fix: stop clicks on the video container and video element
// from bubbling up to messageScreen's ack listener.
// This lets Amma use the native video controls (play/pause/seek)
// without accidentally dismissing the interrupt.
// She taps OUTSIDE the video area to acknowledge.
videoContainer.addEventListener('click', (e) => {
  e.stopPropagation();
});
videoPlayer.addEventListener('click', (e) => {
  e.stopPropagation();
});

// Gallery fullscreen — tap on black area around video or photo to go back.
// Tapping the video element itself toggles play/pause (handled below).
fullscreenScreen.addEventListener('click', handleFullscreenTap);

// Fullscreen video — tap on video to toggle play/pause (not navigate back).
fullscreenVideo.addEventListener('click', (e) => {
  e.stopPropagation();
  if (fullscreenVideo.paused) {
    fullscreenVideo.play().catch(() => {});
  } else {
    fullscreenVideo.pause();
  }
});

// Fullscreen video — hide footer while playing, show when paused or ended.
fullscreenVideo.addEventListener('play',   hideFullscreenFooter);
fullscreenVideo.addEventListener('pause',  showFullscreenFooter);
fullscreenVideo.addEventListener('ended',  showFullscreenFooter);

// Gallery 🏠 home button
document.getElementById('btn-gallery-home').addEventListener('click', (e) => {
  e.stopPropagation();
  showHome();
});

// Home screen — 📷 Photos button
document.getElementById('btn-photos').addEventListener('click', (e) => {
  e.stopPropagation();
  openGallery('photo');
});

// Home screen — 🎥 Videos button
document.getElementById('btn-videos').addEventListener('click', (e) => {
  e.stopPropagation();
  openGallery('video');
});

// ── Fixed mic button (Bug 6 fix: single element, both screens) ─

// Touch events: prevent default (stops iOS long-press menu),
// stop propagation (stops ack firing on interrupt screen).
micButton.addEventListener('touchstart', (e) => {
  e.preventDefault();
  e.stopPropagation();
  startRecording();
}, { passive: false });

micButton.addEventListener('touchend', (e) => {
  e.preventDefault();
  e.stopPropagation();
  stopRecording();
}, { passive: false });

// Mouse events for desktop / simulator testing
micButton.addEventListener('mousedown', (e) => {
  e.stopPropagation();
  startRecording();
});
micButton.addEventListener('mouseup', (e) => {
  e.stopPropagation();
  stopRecording();
});

// ── Safari audio unlock — first user gesture anywhere on page ──
// touchstart fires before click on iOS, so it unlocks audio
// before any play() call triggered by the same gesture.
// { once: true } removes both listeners after first fire.
document.addEventListener('touchstart', unlockAudio, { once: true, passive: true });
document.addEventListener('click',      unlockAudio, { once: true, passive: true });

// ── Start ─────────────────────────────────────────────────────

connect();
