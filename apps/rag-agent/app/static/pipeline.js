/* ============================================================
   NovelBridge Pipeline JS — Three-Stage Layout
   Vanilla JS, modular functions, no frameworks.
   ============================================================ */

// ── Globals ──────────────────────────────────────────────────────
var AUTO_REFRESH = true;
var USE_MODEL = false;
var PHASE_NAMES  = {P1:'分章',P2:'梗概',P3:'提取',P4:'治理',P5:'叙事',P6:'索引',P7:'图谱',P8:'导出'};
var PHASE_ORDER  = ['P1','P2','P3','P4','P5','P6','P7','P8'];
var BOOKS_DATA   = [];
var _cancelFullPipeline = false;
var _refreshTimer       = null;
var _stageStartTimes    = {};   // { 'bookId_stageN': timestamp_ms }
var _queueVisible       = false;
var _runningPollTimers  = {};   // { 'bookId_phase': intervalId }
var _maxStageRetries    = 5;    // max retries for stage 2 chapters

// Stage definitions
var STAGES = {
  '1': { name: '阶段一：分章 + 梗概', phases: ['P1','P2'], label: 'S1' },
  '2': { name: '阶段二：事实提取',     phases: ['P3'],     label: 'S2' },
  '3': { name: '阶段三：治理 + 导出',  phases: ['P4','P5','P6','P7','P8'], label: 'S3' }
};

// ── Initialisation ───────────────────────────────────────────────
loadPipeline();
_refreshTimer = setInterval(function(){ if(AUTO_REFRESH) refreshStatus(); }, 5000);

// ── Core: Load & Render ─────────────────────────────────────────
async function loadPipeline(){
  var container = document.getElementById('pipeline-container');
  try {
    var r = await fetch('/api/v2/pipeline/books');
    if (!r.ok) throw new Error('HTTP ' + r.status);
    var data = await r.json();
    BOOKS_DATA = data.books || [];
    renderPipeline();
  } catch(e) {
    container.innerHTML = '<div class="loading">加载失败: ' + esc(e.message) + '</div>';
  }
}

async function refreshStatus(){
  try {
    var r = await fetch('/api/v2/pipeline/books');
    if (!r.ok) return;
    var data = await r.json();
    var books = data.books || [];
    for (var i = 0; i < books.length; i++) {
      updateBookInPlace(books[i]);
    }
    BOOKS_DATA = books;
    // Also refresh queue if visible
    if (_queueVisible) fetchQueue(true);
  } catch(e) { /* silent */ }
}

function renderPipeline(){
  var el = document.getElementById('pipeline-container');
  if (!BOOKS_DATA || BOOKS_DATA.length === 0) {
    el.innerHTML = '<div class="loading">暂无书籍，请先上传 TXT 文件</div>';
    return;
  }
  var h = '';
  for (var b = 0; b < BOOKS_DATA.length; b++) {
    h += renderBookCard(BOOKS_DATA[b]);
  }
  el.innerHTML = h;
  updateBatchBtn();
}

// ── Stage State Computation ─────────────────────────────────────
// Data sources:
//   book.phases        — task_manager: real-time per-phase progress + RUNNING status (updates every 2s via poll)
//   book.pipeline_state — pipeline_state store: authoritative stage-level status (SUCCESS/FAILED/PENDING)
// Strategy: use phases for real-time RUNNING detection + progress, pipeline_state for authoritative completed status
function computeStageState(book){
  var ps = book.pipeline_state;
  var phases = book.phases || {};

  // Get stage progress: weighted sum of phase progresses (never decreases)
  // Stage 1 (P1+P2): each phase contributes 50% weight
  // Stage 2 (P3): P3 contributes 100%
  // Stage 3 (P4-P8): each phase contributes 20% weight
  function phaseProgress(phaseList) {
    var weight = 100 / phaseList.length;  // equal weight per phase
    var total = 0;
    for (var i = 0; i < phaseList.length; i++) {
      var p = phases[phaseList[i]];
      if (p) { total += weight * ((p.latest_progress || 0) / 100); }
    }
    return Math.round(total);
  }

  // Check if any phase in a stage is RUNNING
  function hasRunning(phaseList) {
    for (var i = 0; i < phaseList.length; i++) {
      var p = phases[phaseList[i]];
      if (p && p.latest_status === 'RUNNING') return true;
    }
    return false;
  }

  // Check if all phases SUCCESS
  function allSuccess(phaseList) {
    for (var i = 0; i < phaseList.length; i++) {
      var p = phases[phaseList[i]];
      if (!p || p.latest_status !== 'SUCCESS') return false;
    }
    return phaseList.length > 0;
  }

  // Combine: start with task_manager phases, override with pipeline_state
  function mergeStage(phaseList, stageState) {
    var running = hasRunning(phaseList);
    var progress = phaseProgress(phaseList);
    var status;

    if (running) {
      status = 'RUNNING';
    } else if (allSuccess(phaseList)) {
      status = 'SUCCESS';
    } else if (stageState) {
      // Use pipeline_state for authoritative status (FAILED, COMPLETED_WITH_ERRORS)
      status = stageState.status;
    } else {
      status = 'PENDING';
    }

    return { status: status, progress: progress };
  }

  if (ps) {
    var s1 = mergeStage(['P1','P2'], ps.stage1);
    var s2 = mergeStage(['P3'], ps.stage2);
    // Stage 2: pass through detail
    s2.detail = ps.stage2.detail || {};
    s2.checkpoint_summary = ps.stage2.checkpoint_summary || {};
    var s3 = mergeStage(['P4','P5','P6','P7','P8'], ps.stage3);
    s3.force_override = ps.stage3.force_override || false;

    return { stage1: s1, stage2: s2, stage3: s3 };
  }

  // Fallback: phases only
  var st1 = combinePhaseStates(['P1','P2'], phases);
  var st2 = combinePhaseStates(['P3'], phases);
  var st3 = combinePhaseStates(['P4','P5','P6','P7','P8'], phases);
  return { stage1: st1, stage2: st2, stage3: st3 };
}

function combinePhaseStates(phaseList, phases){
  var statuses = [];
  var progressSum = 0;
  var count = 0;
  for (var i = 0; i < phaseList.length; i++) {
    var p = phases[phaseList[i]] || { latest_status: 'PENDING', latest_progress: 0 };
    statuses.push(p.latest_status);
    progressSum += (p.latest_progress || 0);
    count++;
  }
  var avgProgress = count > 0 ? Math.round(progressSum / count) : 0;

  if (statuses.every(function(s){ return s === 'SUCCESS'; }))
    return { status: 'SUCCESS', progress: 100 };
  if (statuses.includes('RUNNING'))
    return { status: 'RUNNING', progress: avgProgress, runningPhase: phaseList[statuses.indexOf('RUNNING')] };
  if (statuses.includes('FAILED'))
    return { status: 'FAILED', progress: avgProgress };
  // Some success, some pending = partial
  if (statuses.some(function(s){ return s === 'SUCCESS'; }))
    return { status: 'COMPLETED_WITH_ERRORS', progress: avgProgress };
  return { status: 'PENDING', progress: 0 };
}

// Determine stage2 enriched status (SUCCESS with some failed chapters = COMPLETED_WITH_ERRORS)
function stage2EnrichedStatus(book){
  var st = computeStageState(book).stage2;
  // From pipeline_state: check if Stage 2 has failed chapters
  if (st.detail && st.detail.total_failed > 0) {
    st.status = 'COMPLETED_WITH_ERRORS';
  }
  // From checkpoint summary: if there are permanent failures
  if (st.checkpoint_summary && st.checkpoint_summary.permanent_failed > 0) {
    st.status = 'COMPLETED_WITH_ERRORS';
  }
  return st;
}

// ── Render Book Card ────────────────────────────────────────────
function renderBookCard(book){
  var st = computeStageState(book);
  var s1 = st.stage1, s2 = stage2EnrichedStatus(book), s3 = st.stage3;
  var bid = book.id;

  var h = '';
  h += '<div class="book-card" id="book-card-' + bid + '">';

  // ── Card Header ──
  h += '<div class="card-header">';
  h += '<input type="checkbox" class="book-checkbox" value="' + bid + '" onchange="updateBatchBtn()">';
  h += '<span class="book-title">' + esc(book.title || '未命名') + '</span>';
  h += '<span class="badge ' + esc(book.status || 'IMPORTED') + '">' + esc(book.status || 'IMPORTED') + '</span>';
  h += '<span class="book-meta">' + (book.chapter_count || 0) + '章 · ' + (book.chunk_count || 0) + '块</span>';
  h += '<span class="spacer"></span>';
  h += '<label class="model-toggle"><input type="checkbox" class="model-cb" value="' + bid + '" checked> 使用模型</label>';
  h += '<select class="provider-sel" data-book="' + bid + '">';
  h += '<option value="local">9B 本地</option><option value="deepseek">DeepSeek</option>';
  h += '</select>';
  h += '</div>';

  // ── Stages ──
  h += '<div class="stages">';
  h += renderStageCard(bid, 1, s1, book);
  h += renderStageCard(bid, 2, s2, book);
  h += renderStageCard(bid, 3, s3, book);
  h += '</div>';

  // ── Action Bar ──
  h += '<div class="action-bar" id="actions-' + bid + '">';
  // Stage 1 group
  h += '<div class="action-group">';
  h += '<span class="action-label">阶段一</span>';
  h += '<button class="btn-run" onclick="runStage1(' + bid + ')" id="run-s1-' + bid + '"' + (s1.status==='RUNNING'?' disabled':'') + '>&#9654; 运行阶段一</button>';
  h += '<button onclick="resumeStage1(' + bid + ')" id="resume-s1-' + bid + '"' + (s1.status==='RUNNING'||s1.status==='SUCCESS'?' disabled':'') + '>&#9654; 续跑阶段一</button>';
  h += '<button class="btn-clean" onclick="cleanupStage1(' + bid + ')" id="clean-s1-' + bid + '"' + (s1.status==='RUNNING'?' disabled':'') + '>清阶段一</button>';
  h += '</div>';

  // Stage 2 group
  var s2Running = s2.status === 'RUNNING';
  h += '<div class="action-group">';
  h += '<span class="action-label">阶段二</span>';
  h += '<button class="btn-run" onclick="runStage2(' + bid + ')" id="run-s2-' + bid + '"' + (s2Running?' disabled':'') + '>&#9654; 运行阶段二</button>';
  h += '<button onclick="resumeStage2(' + bid + ')" id="resume-s2-' + bid + '"' + (s2Running?' disabled':'') + '>&#9654; 续跑失败章节</button>';
  h += '<button class="btn-warn" onclick="rerunAllStage2(' + bid + ')" id="rerun-s2-' + bid + '"' + (s2Running?' disabled':'') + '>&#9654; 强制重跑全部</button>';
  h += '<button class="btn-clean" onclick="cleanupStage2(' + bid + ')" id="clean-s2-' + bid + '"' + (s2Running?' disabled':'') + '>清阶段二</button>';
  h += '</div>';

  // Stage 3 group
  var s3Running = s3.status === 'RUNNING';
  var s3Blocked = !isStage2Ok(s2) && !isStage2Error(s2);  // Stage 2 PENDING/RUNNING
  var s3Error = isStage2Error(s2);  // Stage 2 FAILED or COMPLETED_WITH_ERRORS
  h += '<div class="action-group">';
  h += '<span class="action-label">阶段三</span>';
  h += '<button class="btn-run" onclick="runStage3(' + bid + ')" id="run-s3-' + bid + '"' + (s3Running || s3Blocked || s3Error?' disabled':'') + '>&#9654; 运行阶段三</button>';
  h += '<button class="btn-warn" onclick="forceStage3(' + bid + ')" id="force-s3-' + bid + '" style="display:' + (s3Error?'':'none') + '">&#9654; 忽略继续</button>';
  h += '<button class="btn-clean" onclick="cleanupStage3(' + bid + ')" id="clean-s3-' + bid + '"' + (s3Running?' disabled':'') + '>清阶段三</button>';
  h += '</div>';

  // Global group
  h += '<div class="action-group">';
  h += '<span class="action-label">全局</span>';
  var anyRunning = s1.status==='RUNNING' || s2.status==='RUNNING' || s3.status==='RUNNING';
  h += '<button class="btn-run" onclick="fullPipelineResume(' + bid + ')" id="full-' + bid + '"' + (anyRunning?' disabled':'') + '>&#9654; 全流程续跑</button>';
  h += '<button class="btn-clean danger" onclick="cleanupAll(' + bid + ')" id="clean-all-' + bid + '"' + (anyRunning?' disabled':'') + '>清全部</button>';
  h += '</div>';

  h += '</div>'; // end action-bar
  h += '</div>'; // end book-card
  return h;
}

function isStage2Ok(s2){ return s2.status === 'SUCCESS'; }
function isStage2Error(s2){ return s2.status === 'COMPLETED_WITH_ERRORS' || s2.status === 'FAILED'; }

function renderStageCard(bid, stageNum, state, book){
  var n = stageNum;
  var statusClass = state.status;
  var statusText  = statusLabel(state.status);
  var timeId      = 'stage-time-' + bid + '-' + n;
  var timeDisplay = '';

  // Track start time for running stages
  var startKey = bid + '_stage' + n;
  if (state.status === 'RUNNING' && !_stageStartTimes[startKey]) {
    _stageStartTimes[startKey] = Date.now();
  } else if (state.status !== 'RUNNING') {
    delete _stageStartTimes[startKey];
  }
  if (_stageStartTimes[startKey]) {
    var elapsed = Math.round((Date.now() - _stageStartTimes[startKey]) / 1000);
    timeDisplay = elapsed + 's';
  }

  var h = '';
  h += '<div class="stage-card" id="stage-card-' + bid + '-' + n + '">';
  // Header (click to expand Stage 2 detail)
  h += '<div class="stage-header" onclick="toggleStageExpand(' + bid + ',' + n + ')">';
  h += '<span class="stage-number s' + n + '">' + n + '</span>';
  h += '<span class="stage-name">' + STAGES[String(n)].name + '</span>';
  // Status badge: colored dot + text
  h += '<span class="stage-status ' + statusClass + '" id="stage-status-' + bid + '-' + n + '">' + statusText + '</span>';
  // Elapsed time (only shown when running or completed)
  if (timeDisplay || state.status === 'SUCCESS' || state.status === 'FAILED' || state.status === 'COMPLETED_WITH_ERRORS') {
    h += '<span class="stage-time" id="' + timeId + '">' + timeDisplay + '</span>';
  } else {
    h += '<span class="stage-time" id="' + timeId + '" style="display:none"></span>';
  }
  // Cancel button for running stages
  h += '<button class="stage-cancel" id="cancel-stage-' + bid + '-' + n + '" onclick="cancelRunningStage(' + bid + ',' + n + ')" style="display:' + (state.status === 'RUNNING' ? '' : 'none') + '" title="取消">✕</button>';
  h += '<span class="stage-expand" id="stage-expand-' + bid + '-' + n + '">&#9660;</span>';
  h += '</div>';

  // Detail (expandable — only Stage 2 has chapter list)
  h += '<div class="stage-detail" id="stage-detail-' + bid + '-' + n + '">';
  h += '<div class="stage-detail-inner" id="stage-detail-inner-' + bid + '-' + n + '">';
  if (n === 2) {
    h += '<div class="chapter-summary" id="chapter-summary-' + bid + '">点击展开查看章节详情</div>';
    h += '<div class="chapter-table-wrap" id="chapter-table-wrap-' + bid + '" style="display:none"></div>';
  } else {
    h += '<span id="stage-msg-' + bid + '-' + n + '">' + esc(state.message || '') + '</span>';
  }
  h += '</div></div>';

  h += '</div>';
  return h;
}

function statusLabel(s){
  var map = {
    'PENDING':    '○ 等待',
    'RUNNING':    '⏳ 运行中',
    'SUCCESS':    '✓ 完成',
    'COMPLETED_WITH_ERRORS': '⚠ 部分失败',
    'FAILED':     '✗ 失败'
  };
  return map[s] || s;
}

// ── In-Place Update (refresh) ───────────────────────────────────
function updateBookInPlace(book){
  var bid = book.id;
  var st = computeStageState(book);
  var s2 = stage2EnrichedStatus(book);
  var stages = { '1': st.stage1, '2': s2, '3': st.stage3 };

  // Check card exists
  if (!document.getElementById('book-card-' + bid)) return;

  for (var n = 1; n <= 3; n++) {
    var state = stages[String(n)];
    var statusEl    = document.getElementById('stage-status-' + bid + '-' + n);
    var timeEl      = document.getElementById('stage-time-' + bid + '-' + n);
    var msgEl       = document.getElementById('stage-msg-' + bid + '-' + n);

    if (statusEl) {
      var newClass = 'stage-status ' + state.status;
      if (statusEl.className !== newClass) statusEl.className = newClass;
      var newLabel = statusLabel(state.status);
      if (statusEl.textContent !== newLabel) statusEl.textContent = newLabel;
    }
    // Elapsed time
    var startKey = bid + '_stage' + n;
    if (state.status === 'RUNNING' && !_stageStartTimes[startKey]) {
      _stageStartTimes[startKey] = Date.now();
    } else if (state.status !== 'RUNNING') {
      delete _stageStartTimes[startKey];
    }
    if (timeEl) {
      if (_stageStartTimes[startKey]) {
        var elapsed = Math.round((Date.now() - _stageStartTimes[startKey]) / 1000);
        var mins = Math.floor(elapsed / 60);
        var secs = elapsed % 60;
        timeEl.textContent = mins > 0 ? mins + '分' + secs + '秒' : elapsed + '秒';
        timeEl.style.display = '';
      } else if (state.status === 'SUCCESS' || state.status === 'FAILED' || state.status === 'COMPLETED_WITH_ERRORS') {
        // Keep last known time
      } else {
        timeEl.style.display = 'none';
      }
    }
    if (msgEl && n !== 2 && state.message) {
      msgEl.textContent = state.message;
    }

    // Update cancel button visibility
    var cancelStageBtn = document.getElementById('cancel-stage-' + bid + '-' + n);
    if (cancelStageBtn) {
      cancelStageBtn.style.display = state.status === 'RUNNING' ? '' : 'none';
    }

    // Update action buttons
    updateActionButtons(bid, stages);
  }

  // Update stage 2 detail if expanded
  var detailEl = document.getElementById('stage-detail-' + bid + '-2');
  if (detailEl && detailEl.classList.contains('expanded')) {
    // Refresh chapter data silently
    refreshChapterTable(bid);
  }
}

function updateActionButtons(bid, stages){
  // Support both numeric keys ('1') and named keys ('stage1')
  var s1 = stages['1'] || stages['stage1'] || {status:'PENDING',progress:0};
  var s2 = stages['2'] || stages['stage2'] || {status:'PENDING',progress:0};
  var s3 = stages['3'] || stages['stage3'] || {status:'PENDING',progress:0};
  var anyRunning = s1.status==='RUNNING' || s2.status==='RUNNING' || s3.status==='RUNNING';

  setDisabled('run-s1-' + bid, s1.status === 'RUNNING');
  setDisabled('resume-s1-' + bid, s1.status === 'RUNNING' || s1.status === 'SUCCESS');
  setDisabled('clean-s1-' + bid, s1.status === 'RUNNING');

  setDisabled('run-s2-' + bid, s2.status === 'RUNNING');
  setDisabled('resume-s2-' + bid, s2.status === 'RUNNING');
  setDisabled('rerun-s2-' + bid, s2.status === 'RUNNING');
  setDisabled('clean-s2-' + bid, s2.status === 'RUNNING');

  setDisabled('run-s3-' + bid, s3.status === 'RUNNING' || (!isStage2Ok(s2) && !isStage2Error(s2)));
  setDisabled('clean-s3-' + bid, s3.status === 'RUNNING');
  // force button visibility
  var forceBtn = document.getElementById('force-s3-' + bid);
  if (forceBtn) forceBtn.style.display = isStage2Error(s2) ? '' : 'none';

  setDisabled('full-' + bid, anyRunning);
  setDisabled('clean-all-' + bid, anyRunning);
}

function setDisabled(id, disabled){
  var el = document.getElementById(id);
  if (el) el.disabled = !!disabled;
}

// ── Stage 2 Expand / Chapter Table ──────────────────────────────
async function toggleStageExpand(bid, n){
  var detailEl  = document.getElementById('stage-detail-' + bid + '-' + n);
  var expandEl  = document.getElementById('stage-expand-' + bid + '-' + n);
  if (!detailEl) return;

  var isOpen = detailEl.classList.contains('expanded');
  if (isOpen) {
    detailEl.classList.remove('expanded');
    if (expandEl) expandEl.classList.remove('open');
  } else {
    detailEl.classList.add('expanded');
    if (expandEl) expandEl.classList.add('open');
    // For Stage 2, load chapter checkpoint data
    if (n === 2) {
      await loadChapterTable(bid);
    }
  }
}

async function loadChapterTable(bid){
  var wrap = document.getElementById('chapter-table-wrap-' + bid);
  var summaryEl = document.getElementById('chapter-summary-' + bid);
  if (!wrap) return;

  wrap.innerHTML = '<div class="loading-sm">加载章节数据...</div>';
  wrap.style.display = 'block';

  try {
    var r = await fetch('/api/v2/books/' + bid + '/stage2/checkpoint');
    if (!r.ok) throw new Error('HTTP ' + r.status);
    var data = await r.json();
    var chapters = data.checkpoints || {};
    var failed = data.failed_chapters || [];
    var totalChapters = data.total_chapters || Object.keys(chapters).length;

    // Build summary
    var successCount = 0, failedCount = 0, pendingCount = 0, runningCount = 0;
    var chapterRows = '';
    var keys = Object.keys(chapters).sort(function(a,b){ return parseInt(a)-parseInt(b); });

    for (var i = 0; i < keys.length; i++) {
      var cn = keys[i];
      var cp = chapters[cn];
      var st = (cp.status || 'PENDING').toUpperCase();
      if (st === 'SUCCESS') successCount++;
      else if (st === 'FAILED') failedCount++;
      else if (st === 'RUNNING') runningCount++;
      else pendingCount++;

      var statusClass = '', statusText = '';
      if (st === 'SUCCESS') { statusClass = 's'; statusText = '✓ 成功'; }
      else if (st === 'FAILED') { statusClass = 'f'; statusText = '✗ 失败'; }
      else if (st === 'RUNNING') { statusClass = 'r'; statusText = '⏳ 运行中'; }
      else { statusClass = 'p'; statusText = '○ 等待'; }

      var retries = cp.retries || 0;
      var maxRetries = cp.max_retries || _maxStageRetries;
      var exhausted = retries >= maxRetries;
      var errorMsg = esc((cp.error || '').slice(0, 60));

      var rowClass = '';
      if (st === 'FAILED') rowClass = 'ch-failed';
      else if (st === 'RUNNING') rowClass = 'ch-running';
      else if (st === 'SUCCESS') rowClass = 'ch-success';

      chapterRows += '<tr class="' + rowClass + '">';
      chapterRows += '<td style="width:60px">' + cn + '</td>';
      chapterRows += '<td style="width:80px"><span class="ch-status ' + statusClass + '">' + statusText + '</span></td>';
      chapterRows += '<td>' + errorMsg + '</td>';
      chapterRows += '<td style="width:60px;text-align:center">' + retries + '/' + maxRetries + '</td>';
      chapterRows += '<td style="width:60px">';
      if (st === 'FAILED' && !exhausted) {
        chapterRows += '<button class="ch-retry-btn" onclick="retryChapter(' + bid + ',' + cn + ',this)">重试</button>';
      } else if (st === 'FAILED' && exhausted) {
        chapterRows += '<span style="color:var(--muted);font-size:11px">已用尽</span>';
      } else {
        chapterRows += '<span style="color:var(--muted);font-size:11px">—</span>';
      }
      chapterRows += '</td>';
      chapterRows += '</tr>';
    }

    // Summary
    var summaryParts = [];
    if (successCount > 0) summaryParts.push('<span class="cs-ok">✓ ' + successCount + ' 成功</span>');
    if (failedCount > 0) summaryParts.push('<span class="cs-fail">✗ ' + failedCount + ' 失败</span>');
    if (runningCount > 0) summaryParts.push('<span class="cs-running">⏳ ' + runningCount + ' 运行中</span>');
    if (pendingCount > 0) summaryParts.push('<span class="cs-pending">○ ' + pendingCount + ' 等待</span>');
    if (totalChapters) summaryParts.unshift('<span>共 ' + totalChapters + ' 章</span>');
    if (summaryEl) summaryEl.innerHTML = summaryParts.join(' &nbsp;|&nbsp; ');

    // Table
    wrap.innerHTML = chapterRows.length > 0 ?
      '<table class="chapter-table"><thead><tr>' +
      '<th style="width:60px">章节</th>' +
      '<th style="width:80px">状态</th>' +
      '<th>错误信息</th>' +
      '<th style="width:60px">重试</th>' +
      '<th style="width:60px">操作</th>' +
      '</tr></thead><tbody>' + chapterRows + '</tbody></table>' :
      '<div class="loading-sm">暂无章节数据</div>';
  } catch(e) {
    wrap.innerHTML = '<div class="loading-sm">加载失败: ' + esc(e.message) + '</div>';
  }
}

async function refreshChapterTable(bid){
  var detailEl = document.getElementById('stage-detail-' + bid + '-2');
  if (!detailEl || !detailEl.classList.contains('expanded')) return;
  await loadChapterTable(bid);
}

// ── Stage Actions ────────────────────────────────────────────────
function getModelConfig(bookId){
  var cb = document.querySelector('.model-cb[value="' + bookId + '"]');
  var sel = document.querySelector('.provider-sel[data-book="' + bookId + '"]');
  return {
    use_model: !!(cb && cb.checked),
    provider: sel ? sel.value : 'local'
  };
}

function setStageRunningUI(bid, n){
  var statusEl = document.getElementById('stage-status-' + bid + '-' + n);
  var timeEl   = document.getElementById('stage-time-' + bid + '-' + n);
  if (statusEl) { statusEl.className = 'stage-status RUNNING'; statusEl.textContent = statusLabel('RUNNING'); }
  if (timeEl) { timeEl.style.display = ''; timeEl.textContent = '0秒'; }
  var startKey = bid + '_stage' + n;
  _stageStartTimes[startKey] = Date.now();
}

async function runStage1(bookId){
  if (!confirm('将运行阶段一（分章 + 梗概）？')) return;
  setStageRunningUI(bookId, 1);
  updateActionButtons(bookId, computeStageState({phases:{}}));
  await runPhases(bookId, ['P1','P2']);
  loadPipeline();
}

async function resumeStage1(bookId){
  if (!confirm('将续跑阶段一中未完成的步骤？')) return;
  setStageRunningUI(bookId, 1);
  // Determine which phases need running
  var book = findBook(bookId);
  var phases = book ? book.phases || {} : {};
  var toRun = [];
  for (var i = 0; i < STAGES['1'].phases.length; i++) {
    var p = STAGES['1'].phases[i];
    var info = phases[p] || { latest_status: 'PENDING' };
    if (info.latest_status !== 'SUCCESS') toRun.push(p);
  }
  if (toRun.length === 0) { loadPipeline(); return; }
  await runPhases(bookId, toRun);
  loadPipeline();
}

async function runStage2(bookId){
  if (!confirm('将运行阶段二（事实提取）。此阶段耗时较长（约 2-4 小时/百章），确认继续？')) return;
  setStageRunningUI(bookId, 2);
  updateActionButtons(bookId, computeStageState({phases:{}}));
  await runPhases(bookId, ['P3']);
  loadPipeline();
}

async function resumeStage2(bookId){
  if (!confirm('将重试阶段二中失败的章节？')) return;
  setStageRunningUI(bookId, 2);
  try {
    var r = await fetch('/api/v2/books/' + bookId + '/stage2/resume', { method: 'POST' });
    var d = await r.json();
    if (d.status === 'started' && d.task_id) {
      await waitTask(d.task_id, bookId, 'P3');
    }
  } catch(e) { alert('续跑失败: ' + e.message); }
  loadPipeline();
}

async function rerunAllStage2(bookId){
  if (!confirm('将清空阶段二所有检查点，强制重跑全部章节。确认继续？')) return;
  setStageRunningUI(bookId, 2);
  try {
    var r = await fetch('/api/v2/books/' + bookId + '/stage2/rerun-all', { method: 'POST' });
    var d = await r.json();
    if (d.status === 'started' && d.task_id) {
      await waitTask(d.task_id, bookId, 'P3');
    }
  } catch(e) { alert('重跑失败: ' + e.message); }
  loadPipeline();
}

async function retryChapter(bookId, chapterNum, btnEl){
  if (btnEl) { btnEl.disabled = true; btnEl.textContent = '重试中...'; }
  try {
    var r = await fetch('/api/v2/books/' + bookId + '/stage2/retry-chapter/' + chapterNum, { method: 'POST' });
    var d = await r.json();
    if (d.status === 'started') {
      // Refresh chapter table after a short delay
      setTimeout(function(){ refreshChapterTable(bookId); }, 2000);
    }
  } catch(e) {
    if (btnEl) { btnEl.disabled = false; btnEl.textContent = '重试'; }
  }
}

async function runStage3(bookId){
  if (!confirm('将运行阶段三（治理 + 叙事 + 索引 + 图谱 + 导出）？')) return;
  setStageRunningUI(bookId, 3);
  updateActionButtons(bookId, computeStageState({phases:{}}));
  await runPhases(bookId, ['P4','P5','P6','P7','P8']);
  loadPipeline();
}

async function forceStage3(bookId){
  if (!confirm('将忽略阶段二的错误，强制运行阶段三。确认继续？')) return;
  // 先设置 force override 标记
  await fetch('/api/v2/books/' + bookId + '/stage3/force', { method: 'POST' });
  // 再运行阶段三
  setStageRunningUI(bookId, 3);
  try {
    await runPhases(bookId, ['P4','P5','P6','P7','P8']);
  } catch(e) { alert('运行失败: ' + e.message); }
  loadPipeline();
}

async function fullPipelineResume(bookId){
  if (!confirm('将从此书的当前进度继续运行全流程（跳过已完成的阶段）。确认继续？')) return;
  _cancelFullPipeline = false;
  var fullBtn = document.getElementById('full-' + bookId);
  var cancelBtn = document.getElementById('cancelFullBtn');
  if (fullBtn) { fullBtn.disabled = true; fullBtn.textContent = '运行中...'; }
  if (cancelBtn) cancelBtn.style.display = 'inline-block';

  // Read book state from pipeline_state (not old task_manager phases)
  var book = findBook(bookId);
  var st = book ? computeStageState(book) : null;

  // Determine which stages need running based on pipeline_state
  var allPhases = [];
  if (!st || st.stage1.status !== 'SUCCESS') allPhases = allPhases.concat(['P1','P2']);
  if (!st || st.stage2.status !== 'SUCCESS') allPhases.push('P3');
  if (!st || st.stage3.status !== 'SUCCESS') allPhases = allPhases.concat(['P4','P5','P6','P7','P8']);

  if (allPhases.length > 0) {
    await runPhases(bookId, allPhases);
  }

  if (fullBtn) { fullBtn.textContent = '全流程续跑'; fullBtn.disabled = false; }
  if (cancelBtn) { cancelBtn.style.display = 'none'; cancelBtn.textContent = '✕ 取消全流程'; }
  _cancelFullPipeline = false;
  loadPipeline();
}

// ── Phase Runner ─────────────────────────────────────────────────
async function runPhases(bookId, phaseList){
  var mc = getModelConfig(bookId);
  for (var i = 0; i < phaseList.length; i++) {
    if (_cancelFullPipeline) break;
    var phase = phaseList[i];
    try {
      var r = await fetch('/api/v2/books/' + bookId + '/phase/' + phase, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ use_model: mc.use_model, provider: mc.provider })
      });
      var d = await r.json();
      if (d.status === 'started') {
        // Update cancel button
        var cancelBtn = document.getElementById('cancelFullBtn');
        if (cancelBtn) cancelBtn.setAttribute('data-current-task', d.task_id);
        var result = await waitTask(d.task_id, bookId, phase);
        if (result === 'CANCELLED' || result === 'FAILED') break;
      }
    } catch(e) { break; }
  }
}

async function waitTask(taskId, bookId, phase){
  var t0 = Date.now();
  for (var i = 0; i < 600; i++) {
    await sleep(2000);
    if (_cancelFullPipeline) {
      fetch('/api/v2/tasks/' + taskId + '/cancel-hard', { method: 'POST' }).catch(function(){});
      return 'CANCELLED';
    }
    try {
      var r = await fetch('/api/v2/tasks/' + taskId);
      if (!r.ok) continue;
      var t = await r.json();
      if (t.status === 'SUCCESS') return 'SUCCESS';
      if (t.status === 'FAILED') return 'FAILED';
      // Progress updates
      var stageNum = phaseToStage(phase);
      if (stageNum) {
        var progEl = document.getElementById('stage-progress-' + bookId + '-' + stageNum);
        if (progEl) progEl.style.width = (t.progress || 0) + '%';
      }
    } catch(e) { /* continue polling */ }
  }
  return 'FAILED';
}

function phaseToStage(phase){
  if (phase === 'P1' || phase === 'P2') return 1;
  if (phase === 'P3') return 2;
  if (phase === 'P4' || phase === 'P5' || phase === 'P6' || phase === 'P7' || phase === 'P8') return 3;
  return null;
}

// ── Queue Monitoring ─────────────────────────────────────────────
async function monitorQueueItem(bookId){
  for (var i = 0; i < 300; i++) {
    await sleep(3000);
    if (_cancelFullPipeline) {
      await fetch('/api/v2/pipeline/cancel/' + bookId, { method: 'POST' }).catch(function(){});
      return;
    }
    try {
      var r = await fetch('/api/v2/pipeline/queue');
      var d = await r.json();
      var queue = d.queue || [];
      var found = false;
      for (var j = 0; j < queue.length; j++) {
        if (queue[j].book_id === bookId) { found = true; break; }
      }
      if (!found) return; // Done
    } catch(e) { /* continue */ }
  }
}

function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }

// ── Cleanup ──────────────────────────────────────────────────────
async function cleanupStage1(bookId){
  if (!confirm('确认清理 ' + bookId + ' 的阶段一数据？')) return;
  await fetch('/api/v2/books/' + bookId + '/cleanup/stage1', { method: 'POST' });
  loadPipeline();
}

async function cleanupStage2(bookId){
  if (!confirm('确认清理 ' + bookId + ' 的阶段二数据（含检查点）？')) return;
  await fetch('/api/v2/books/' + bookId + '/cleanup/stage2', { method: 'POST' });
  loadPipeline();
}

async function cleanupStage3(bookId){
  if (!confirm('确认清理 ' + bookId + ' 的阶段三数据？')) return;
  await fetch('/api/v2/books/' + bookId + '/cleanup/stage3', { method: 'POST' });
  loadPipeline();
}

async function cleanupAll(bookId){
  if (!confirm('确认清理书籍 ' + bookId + ' 的全部数据（数据库+向量+图谱）？\n原始文本不受影响。此操作不可恢复！')) return;
  await fetch('/api/v2/books/' + bookId + '/cleanup', { method: 'POST' });
  await fetch('/api/v2/books/' + bookId + '/cleanup/qdrant', { method: 'POST' });
  await fetch('/api/v2/books/' + bookId + '/cleanup/neo4j', { method: 'POST' });
  loadPipeline();
}

// ── Batch & Queue ────────────────────────────────────────────────
function updateBatchBtn(){
  var cbs = document.querySelectorAll('.book-checkbox:checked');
  var btn = document.getElementById('batchBtn');
  if (btn) btn.textContent = '批量运行选中' + (cbs.length > 0 ? ' (' + cbs.length + '本)' : '');
}

async function batchEnqueue(){
  var cbs = document.querySelectorAll('.book-checkbox:checked');
  if (cbs.length === 0) { alert('请先勾选要处理的书籍'); return; }
  if (!confirm('将 ' + cbs.length + ' 本书加入批量处理队列？')) return;
  var ids = [];
  for (var i = 0; i < cbs.length; i++) ids.push(parseInt(cbs[i].value));
  try {
    var r = await fetch('/api/v2/pipeline/enqueue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ book_ids: ids, mode: 'full' })
    });
    var d = await r.json();
    if (d.status === 'ok' || d.status === 'success' || d.status === 'queued') {
      showQueue();
      fetchQueue();
    }
  } catch(e) { alert('批量排队失败: ' + e.message); }
}

async function fetchQueue(silent){
  try {
    var r = await fetch('/api/v2/pipeline/queue');
    if (!r.ok) return;
    var d = await r.json();
    renderQueue(d.queue || []);
  } catch(e) { if (!silent) console.error(e); }
}

function renderQueue(queue){
  var list = document.getElementById('queueList');
  var countEl = document.getElementById('queueCount');
  var badgeEl = document.getElementById('queueBadge');
  var count = queue.length;

  if (countEl) countEl.textContent = count;
  if (badgeEl) {
    badgeEl.textContent = count;
    badgeEl.style.display = count > 0 ? '' : 'none';
  }

  if (count === 0) {
    list.innerHTML = '<div class="loading-sm">暂无排队任务</div>';
    return;
  }

  var h = '';
  for (var i = 0; i < queue.length; i++) {
    var item = queue[i];
    var stageText = item.stage ? ('→ ' + (item.stage === 'stage1' ? '阶段一' : item.stage === 'stage2' ? '阶段二' : '阶段三')) : '';
    var statusText = '';
    if (item.status === 'running') {
      statusText = (item.message || '运行中') + ' ' + (item.progress || 0) + '%';
    } else if (item.status === 'completed') {
      statusText = '✓ 完成，等待下一阶段';
    } else {
      statusText = '排队中';
    }
    h += '<div class="queue-item" id="queue-item-' + item.book_id + '">';
    h += '<span class="qi-title">' + esc(item.title || 'Book ' + item.book_id) + '</span>';
    h += '<span class="qi-stage">' + stageText + ' ' + statusText + '</span>';
    h += '<span class="qi-progress">' + (item.progress ? item.progress + '%' : '') + '</span>';
    h += '<button class="qi-cancel" onclick="cancelQueuedBook(' + item.book_id + ',this)">✕ 取消</button>';
    h += '</div>';
  }
  list.innerHTML = h;
}

async function cancelQueuedBook(bookId, btnEl){
  if (!confirm('确认取消 Book ' + bookId + ' 的排队/运行任务？')) return;
  if (btnEl) { btnEl.disabled = true; btnEl.textContent = '取消中...'; }
  try {
    var r = await fetch('/api/v2/pipeline/cancel/' + bookId, { method: 'POST' });
    var d = await r.json();
    fetchQueue();
  } catch(e) { alert('取消失败: ' + e.message); }
}

async function clearQueue(){
  if (!confirm('确认清空整个任务队列？')) return;
  try {
    await fetch('/api/v2/pipeline/queue/clear', { method: 'POST' });
    fetchQueue();
  } catch(e) { alert('清空失败: ' + e.message); }
}

function toggleQueue(){
  _queueVisible = !_queueVisible;
  var panel = document.getElementById('queuePanel');
  if (_queueVisible) {
    panel.style.display = '';
    panel.classList.add('show');
    fetchQueue();
  } else {
    panel.style.display = 'none';
    panel.classList.remove('show');
  }
}

function showQueue(){
  _queueVisible = true;
  var panel = document.getElementById('queuePanel');
  if (panel) { panel.style.display = ''; panel.classList.add('show'); }
}

// ── Cancel Running Stage ─────────────────────────────────────────
async function cancelRunningStage(bookId, stageNum){
  // Phase names for this stage
  var phaseNames = stageNum === 1 ? ['P1','P2'] : stageNum === 2 ? ['P3'] : ['P4','P5','P6','P7','P8'];

  // Try 1: Get current task ID from global cancel button (set by runPhases)
  var fullBtn = document.getElementById('cancelFullBtn');
  var taskId = fullBtn ? fullBtn.getAttribute('data-current-task') : null;

  // Try 2: Fallback to task_id from book.phases (for stale tasks from previous runs)
  if (!taskId) {
    var book = findBook(bookId);
    if (book) {
      for (var i = 0; i < phaseNames.length; i++) {
        var phaseInfo = (book.phases || {})[phaseNames[i]];
        if (phaseInfo && phaseInfo.latest_task_id) {
          taskId = phaseInfo.latest_task_id;
          break;
        }
      }
    }
  }

  if (taskId) {
    try { await fetch('/api/v2/tasks/' + taskId + '/cancel-hard', { method: 'POST' }); } catch(e) {}
  } else {
    // Try 3: Direct cancel via pipeline queue endpoint
    try { await fetch('/api/v2/pipeline/cancel/' + bookId, { method: 'POST' }); } catch(e) {}
  }

  _cancelFullPipeline = true;
  // Hide cancel button
  var stageCancel = document.getElementById('cancel-stage-' + bookId + '-' + stageNum);
  if (stageCancel) stageCancel.style.display = 'none';
  setTimeout(function(){ loadPipeline(); }, 1500);
}

// ── Cancel Full Pipeline ─────────────────────────────────────────
async function cancelFullPipeline(){
  _cancelFullPipeline = true;
  var btn = document.getElementById('cancelFullBtn');
  if (btn) btn.textContent = '正在取消...';
  var taskId = btn ? btn.getAttribute('data-current-task') : null;
  if (taskId) {
    try { await fetch('/api/v2/tasks/' + taskId + '/cancel-hard', { method: 'POST' }); }
    catch(e) { /* silent */ }
  }
  setTimeout(function(){
    if (btn) { btn.style.display = 'none'; btn.textContent = '✕ 取消全流程'; }
  }, 2000);
}

// ── Upload (kept from original) ──────────────────────────────────
async function uploadBook(){
  var fi    = document.getElementById('book-file');
  var title = document.getElementById('book-title').value || '未命名';
  var author = document.getElementById('book-author').value || '';
  var re    = document.getElementById('upload-result');
  if (!fi.files.length) { re.textContent = '请选择文件'; return; }
  var fd = new FormData();
  fd.append('title', title);
  fd.append('author', author);
  for (var f = 0; f < fi.files.length; f++) fd.append('files', fi.files[f]);
  re.textContent = '上传中...';
  try {
    var r = await fetch('/api/books/upload', { method: 'POST', body: fd });
    var d = await r.json();
    re.textContent = '上传成功: book_id=' + d.book_id + ' chapters=' + d.chapters;
    loadPipeline();
  } catch(e) { re.textContent = '上传失败: ' + e.message; }
}

// ── Modal (for future use) ───────────────────────────────────────
function closeChapterModal(event){
  if (event && event.target !== document.getElementById('chapterModal')) return;
  document.getElementById('chapterModal').style.display = 'none';
}

// ── Helpers ──────────────────────────────────────────────────────
function findBook(bookId){
  for (var i = 0; i < BOOKS_DATA.length; i++) {
    if (BOOKS_DATA[i].id === bookId) return BOOKS_DATA[i];
  }
  return null;
}

function esc(s){
  return String(s || '').replace(/[&<>"]/g, function(m){
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m] || m;
  });
}
