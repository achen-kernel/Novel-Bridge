"""Python-first demo console for ReaderAgent modes.

Redesigned as a three-column research reading workspace:
- Left sidebar: book selector + preset questions
- Center: chat-style conversation
- Right panel (collapsible): context + debug details
"""

from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.config import settings

router = APIRouter(tags=["demo"])


_BOOK_QUESTIONS: dict[int, list[str]] = {
    6: [
        "火焰山的火是怎么来的？",
        "分析孙悟空的人物形象",
        "分析孙悟空和唐僧的关系",
        "追踪孙悟空和唐僧关系变化",
        "猪八戒为什么会被贬下凡？",
        "孙悟空大闹天宫的原因是什么？",
        "观音在取经中的作用是什么？",
        "芭蕉扇在火焰山情节中有什么作用？",
        "唐僧取经路上最大的矛盾是什么？",
        "孙悟空从齐天大圣到行者有什么变化？",
    ],
    7: [
        "《聊斋志异》如何写狐鬼故事？",
        "崂山道士说明了什么道理？",
        "画皮故事的核心冲突是什么？",
        "聊斋中的书生形象有什么特点？",
        "聊斋如何表现人鬼关系？",
        "聊斋故事为什么常有讽刺意味？",
    ],
    8: [
        "搜神记中的神异故事有什么特点？",
        "董永和七仙女故事讲了什么？",
        "搜神记如何组织民间传说？",
        "搜神记中的报效观念是什么？",
        "搜神记和山海经的神话叙述有什么不同？",
        "追踪一个神异事件的发展",
    ],
    9: [
        "《山海经》如何组织山川地理与神话？",
        "山海经分为哪些部分？",
        "昆仑在山海经中有什么意义？",
        "夸父逐日讲了什么？",
        "精卫填海体现了什么精神？",
        "山海经中的异兽有什么功能？",
        "追踪昆仑相关线索",
        "《山经》和《海经》有什么区别？",
    ],
    10: [
        "宋江为什么能成为梁山核心人物？",
        "分析林冲的人物转变",
        "鲁智深倒拔垂杨柳体现了什么性格？",
        "追踪宋江上梁山前后的变化",
        "分析宋江和晁盖的关系",
        "武松的性格有哪些矛盾？",
        "梁山好汉为什么会聚义？",
        "招安对梁山意味着什么？",
    ],
}

_BOOK_NAMES = ["西游记", "聊斋志异", "搜神记", "山海经", "水浒传"]
_BOOK_IDS = [6, 7, 8, 9, 10]


STYLE = """
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; background: #f4f6f2; color: #18201c;
  font-family: "PingFang SC","Microsoft YaHei",system-ui,sans-serif;
  font-size: 15px; line-height: 1.6; overflow: hidden; }
button { font-family: inherit; cursor: pointer; }
:focus-visible { outline: 3px solid rgba(31,111,91,0.28); }

/* Layout */
.app-shell { display: flex; flex-direction: column; height: 100vh; }

/* Health strip */
.health-strip { display: flex; align-items: center; gap: 6px;
  padding: 5px 14px; background: #fff; border-bottom: 1px solid #d8ded7;
  font-size: 12px; flex-shrink: 0; overflow-x: auto; }
.health-dot { width: 7px; height: 7px; border-radius: 50%;
  display: inline-block; margin-right: 2px; flex-shrink: 0; }
.health-dot.ok { background: #1f6f5b; }
.health-dot.bad { background: #a33535; }
.health-dot.warn { background: #a15c16; }
.health-name { color: #607069; }
.health-link { color: #1f6f5b; text-decoration: none; font-size: 12px; }
.health-link:hover { text-decoration: underline; }

/* 3-column grid */
.app-body { flex: 1; display: grid;
  grid-template-columns: 240px 1fr 0px; overflow: hidden; min-height: 0; }

/* Sidebar */
.sidebar { display: flex; flex-direction: column; background: #fff;
  border-right: 1px solid #d8ded7; overflow: hidden; }
.sidebar h2 { font-size: 13px; padding: 14px 14px 8px; color: #174f42; }
.book-btn { display: block; width: 100%; text-align: left; padding: 8px 14px;
  border: none; border-left: 3px solid transparent; background: transparent;
  font-size: 14px; color: #18201c; }
.book-btn:hover { background: #f0f7f4; }
.book-btn.active { border-left-color: #1f6f5b; background: #e8f2ee;
  font-weight: 700; }
.presets { flex: 1; overflow-y: auto; border-top: 1px solid #d8ded7;
  padding: 6px 0; }
.presets h3 { font-size: 11px; text-transform: uppercase; letter-spacing: .06em;
  color: #607069; padding: 8px 14px 4px; }
.preset-btn { display: block; width: 100%; text-align: left; padding: 6px 14px;
  border: none; background: transparent; font-size: 13px; color: #18201c;
  line-height: 1.4; }
.preset-btn:hover { background: #f0f7f4; color: #1f6f5b; }

/* Center chat */
.chat-main { display: flex; flex-direction: column; overflow: hidden; }
.chat-header { display: flex; align-items: center; gap: 12px;
  padding: 10px 16px; border-bottom: 1px solid #d8ded7; background: #fff;
  flex-shrink: 0; }
.chat-header h1 { font-size: 16px; color: #174f42; }
.chat-header p { font-size: 12px; color: #607069; }
.header-actions { margin-left: auto; display: flex; gap: 6px; }
.header-btn { padding: 4px 10px; border: 1px solid #d8ded7; border-radius: 6px;
  background: #fff; font-size: 12px; color: #607069; }
.header-btn:hover { border-color: #1f6f5b; color: #174f42; }

.chat-msgs { flex: 1; overflow-y: auto; padding: 16px 20px; }
.msg { margin-bottom: 16px; max-width: 85%; }
.msg.user { margin-left: auto; }
.msg.user .bubble { background: #1f6f5b; color: #fff;
  border-radius: 16px 16px 4px 16px; padding: 10px 16px; }
.msg.assistant .bubble { background: #fff; border: 1px solid #d8ded7;
  border-radius: 16px 16px 16px 4px; padding: 12px 16px; line-height: 1.65; }
.msg.assistant .bubble p { margin: 6px 0; }
.msg.assistant .bubble ul, .msg.assistant .bubble ol { margin: 6px 0;
  padding-left: 20px; }
.msg.assistant .bubble li { margin: 3px 0; }
.msg.assistant .bubble strong { color: #174f42; }
.mode-chip { display: inline-block; font-size: 10px; font-weight: 700;
  letter-spacing: .04em; text-transform: uppercase; color: #607069;
  margin-bottom: 4px; }
.msg-detail-toggle { font-size: 11px; color: #607069; background: none;
  border: none; text-decoration: underline dotted; cursor: pointer;
  padding: 2px 0; margin-top: 4px; }
.msg-detail-toggle:hover { color: #174f42; }

/* Input */
.chat-input { flex-shrink: 0; padding: 10px 16px 14px; border-top: 1px solid #d8ded7;
  background: #fff; }
.input-row { display: flex; gap: 8px; }
.input-row input { flex: 1; padding: 10px 14px; border: 1px solid #d8ded7;
  border-radius: 24px; font-size: 14px; background: #f8faf7;
  outline: none; }
.input-row input:focus { border-color: #1f6f5b; background: #fff; }
.send-btn { padding: 10px 20px; border: none; border-radius: 24px;
  background: #1f6f5b; color: #fff; font-size: 14px; font-weight: 700;
  white-space: nowrap; }
.send-btn:hover { background: #174f42; }
.send-btn:disabled { opacity: .5; cursor: wait; }
.input-hint { font-size: 11px; color: #607069; margin-top: 4px; }

/* Loading */
@keyframes pulse { 0%,100% { opacity: .5; } 50% { opacity: 1; } }
.msg.loading .bubble { animation: pulse 1.2s ease-in-out infinite; }

/* Detail overlay */
.detail-overlay { position: fixed; right: 0; top: 0; bottom: 0; width: 320px;
  background: #fff; border-left: 1px solid #d8ded7; z-index: 50;
  transform: translateX(100%); transition: transform .25s; overflow-y: auto;
  padding: 16px; }
.detail-overlay.open { transform: translateX(0); }
.detail-overlay h3 { font-size: 12px; color: #174f42; margin-bottom: 8px; }
.detail-overlay .row { display: flex; justify-content: space-between;
  padding: 3px 0; font-size: 12px; border-bottom: 1px dotted #d8ded7; }
.detail-overlay .row .l { color: #607069; }
.detail-overlay .row .r { text-align: right; word-break: break-all; }
.detail-evidence { font-size: 12px; background: #fafbfa;
  padding: 8px; border: 1px solid #d8ded7; border-radius: 6px;
  margin: 4px 0; }
.detail-evidence b { color: #174f42; }

@media (max-width: 800px) {
  .app-body { grid-template-columns: 0 1fr 0; }
  .sidebar { display: none; }
  .msg { max-width: 100%; }
}
</style>
"""
  font-weight: 600;
  color: var(--ink);
  background: none;
  width: 100%;
  text-align: left;
  transition: all 0.15s;
  user-select: none;
}

.book-item:hover { background: var(--accent-pale); }

.book-item.active {
  border-left-color: var(--accent);
  background: var(--accent-soft);
  color: var(--accent-strong);
}

.book-item .book-icon {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  background: var(--accent-pale);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  flex-shrink: 0;
  transition: all 0.15s;
}

.book-item.active .book-icon {
  background: var(--accent);
  color: #fff;
}

.presets-section {
  flex: 1;
  overflow-y: auto;
  padding: 10px 8px;
  min-height: 0;
}

.presets-section h3 {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted);
  padding: 0 12px;
  margin-bottom: 8px;
  font-weight: 700;
}

.preset-card {
  display: block;
  width: 100%;
  text-align: left;
  padding: 9px 12px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--ink);
  font-size: 13px;
  line-height: 1.5;
  cursor: pointer;
  transition: all 0.15s;
  margin-bottom: 2px;
  user-select: none;
}

.preset-card:hover {
  background: var(--accent-soft);
  border-color: var(--accent);
  color: var(--accent-strong);
}

/* === Chat Main === */
.chat-main {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
  min-width: 0;
}

.chat-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 20px;
  background: rgba(255,255,255,0.92);
  border-bottom: 1px solid var(--line);
}

.chat-hamburger {
  display: none;
  background: none;
  border: none;
  font-size: 22px;
  cursor: pointer;
  color: var(--muted);
  padding: 2px;
  line-height: 1;
  flex-shrink: 0;
}

.chat-brand {
  flex: 1;
  min-width: 0;
}

.chat-brand h1 {
  font-family: "Noto Serif SC", "Source Han Serif SC", Georgia, "Times New Roman", serif;
  font-size: 19px;
  font-weight: 700;
  color: var(--accent-strong);
  letter-spacing: 0.02em;
  line-height: 1.3;
  margin: 0;
}

.chat-brand p {
  font-size: 12px;
  color: var(--muted);
  margin-top: 1px;
}

.chat-toolbar {
  display: flex;
  gap: 5px;
  flex-shrink: 0;
  align-items: center;
}

.tool-btn {
  padding: 5px 10px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: #fff;
  color: var(--muted);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.tool-btn:hover {
  background: var(--accent-soft);
  border-color: var(--accent);
  color: var(--accent-strong);
}

.tool-btn.danger:hover {
  background: #fdf0f0;
  border-color: var(--danger);
  color: var(--danger);
}

.advanced-panel {
  padding: 8px 20px;
  background: #fafbf9;
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 12px;
  flex-shrink: 0;
}

.advanced-panel select {
  padding: 4px 8px;
  border: 1px solid var(--line);
  border-radius: 4px;
  font-size: 12px;
  background: #fff;
  color: var(--ink);
}

.advanced-panel label {
  color: var(--muted);
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.session-id-label code {
  font-family: "SF Mono", "Cascadia Mono", Consolas, monospace;
  background: var(--accent-pale);
  padding: 1px 6px;
  border-radius: 3px;
  color: var(--accent-strong);
  font-size: 11px;
}

/* === Chat Messages === */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  scroll-behavior: smooth;
  min-height: 0;
  overscroll-behavior: contain;
}

.welcome-msg {
  max-width: 560px;
  margin: 80px auto;
  text-align: center;
  padding: 40px 32px;
  border: 1px dashed var(--line);
  border-radius: var(--radius);
  background: rgba(255,255,255,0.45);
}

.welcome-msg .welcome-icon {
  font-size: 36px;
  margin-bottom: 16px;
  opacity: 0.8;
}

.welcome-msg h2 {
  font-family: "Noto Serif SC", serif;
  font-size: 20px;
  color: var(--accent-strong);
  margin-bottom: 8px;
  font-weight: 700;
}

.welcome-msg p {
  color: var(--muted);
  font-size: 14px;
  line-height: 1.7;
  margin-bottom: 6px;
}

.welcome-msg .welcome-hint {
  margin-top: 14px;
  font-size: 12px;
  color: var(--muted);
}

/* === Message Bubbles === */
.msg {
  max-width: 740px;
  margin-bottom: 18px;
  animation: msgIn 0.3s ease-out;
}

@keyframes msgIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.msg.user {
  margin-left: auto;
  margin-right: 0;
}

.msg.user .msg-wrapper {
  display: flex;
  justify-content: flex-end;
}

.msg.user .msg-bubble {
  background: var(--accent-soft);
  border: 1px solid rgba(31,111,91,0.12);
  border-radius: var(--radius) var(--radius) 4px var(--radius);
  padding: 11px 16px;
  font-size: 15px;
  line-height: 1.6;
  color: var(--accent-strong);
  max-width: 540px;
  word-break: break-word;
}

.msg.user .msg-meta {
  text-align: right;
  font-size: 11px;
  color: var(--muted);
  margin-top: 3px;
  padding-right: 4px;
}

.msg.assistant .msg-bubble {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius) var(--radius) var(--radius) 4px;
  padding: 18px 22px;
  box-shadow: var(--shadow);
}

.msg-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--line);
  gap: 10px;
}

.mode-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.mode-chip.answer  { background: #e8f2ee; color: var(--accent-strong); }
.mode-chip.analyze { background: #f0ecf6; color: #5b3a8c; }
.mode-chip.trace   { background: #fef3e4; color: var(--warn); }
.mode-chip.enrich  { background: #e8f0f8; color: #2a5d8c; }

.msg-status {
  font-size: 11px;
  color: var(--muted);
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-toggle {
  padding: 3px 10px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
  color: var(--muted);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.detail-toggle:hover {
  background: var(--accent-soft);
  border-color: var(--accent);
  color: var(--accent-strong);
}

.detail-toggle.active {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}

.msg-content {
  font-size: 15px;
  line-height: 1.82;
  word-break: break-word;
}

.msg-content p { margin-bottom: 12px; }
.msg-content p:last-child { margin-bottom: 0; }
.msg-content strong { color: var(--accent-strong); font-weight: 700; }
.msg-content h3 {
  margin: 18px 0 8px;
  font-size: 16px;
  color: var(--accent-strong);
  font-weight: 700;
}
.msg-content h3:first-child { margin-top: 0; }
.msg-content ul, .msg-content ol {
  margin: 10px 0 14px;
  padding-left: 22px;
}
.msg-content li { margin: 5px 0; padding-left: 2px; }
.msg-content code {
  background: var(--accent-pale);
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 0.9em;
  color: var(--accent-strong);
}

.msg-content .insufficient {
  padding: 16px 18px;
  background: var(--warn-bg);
  border: 1px solid #eed8a8;
  border-radius: var(--radius-sm);
  color: var(--warn);
  font-size: 14px;
  line-height: 1.7;
}

.msg-content .patch-count-notice {
  padding: 12px 16px;
  background: var(--accent-pale);
  border-radius: var(--radius-sm);
  color: var(--accent-strong);
  font-size: 14px;
  border: 1px solid rgba(31,111,91,0.15);
}

.msg-content .error-notice {
  padding: 12px 16px;
  background: #fdf0f0;
  border: 1px solid #e8c0c0;
  border-radius: var(--radius-sm);
  color: var(--danger);
  font-size: 14px;
}

/* Loading pulse */
.msg.loading .msg-bubble {
  animation: pulse 1.3s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.45; }
  50% { opacity: 1; }
}

/* === Chat Input === */
.chat-input-bar {
  flex-shrink: 0;
  padding: 12px 20px 16px;
  background: rgba(255,255,255,0.92);
  border-top: 1px solid var(--line);
}

.input-form {
  display: flex;
  gap: 10px;
  align-items: center;
}

.input-form input {
  flex: 1;
  padding: 11px 16px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: #fff;
  font-size: 15px;
  color: var(--ink);
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  min-width: 0;
}

.input-form input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(31,111,91,0.08);
}

.input-form input::placeholder { color: #b0bdb5; }

.input-form .send-btn {
  padding: 11px 22px;
  border: none;
  border-radius: var(--radius);
  background: var(--accent);
  color: #fff;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s, opacity 0.2s;
  white-space: nowrap;
  flex-shrink: 0;
}

.input-form .send-btn:hover { background: var(--accent-strong); }
.input-form .send-btn:disabled { opacity: 0.55; cursor: not-allowed; }

.input-hint {
  font-size: 11px;
  color: var(--muted);
  margin-top: 5px;
  padding-left: 4px;
}

/* === Right Detail Panel === */
.detail-panel {
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: rgba(255,255,255,0.97);
  border-left: 1px solid var(--line);
  min-height: 0;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 13px 16px;
  border-bottom: 1px solid var(--line);
  flex-shrink: 0;
}

.detail-header h3 {
  font-size: 14px;
  font-weight: 700;
  color: var(--accent-strong);
  letter-spacing: 0.04em;
}

.detail-close {
  background: none;
  border: none;
  font-size: 18px;
  color: var(--muted);
  cursor: pointer;
  padding: 2px;
  line-height: 1;
}

.detail-close:hover { color: var(--danger); }

.detail-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px 16px;
  min-height: 0;
}

.detail-section {
  margin-bottom: 18px;
}

.detail-section h4 {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted);
  margin-bottom: 6px;
  padding-bottom: 5px;
  border-bottom: 1px solid var(--line);
  font-weight: 700;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 13px;
  color: var(--ink);
  border-bottom: 1px dotted var(--line);
  gap: 8px;
}

.detail-row .dl { color: var(--muted); flex-shrink: 0; }
.detail-row .dv { text-align: right; word-break: break-all; }
.detail-row code {
  font-family: "SF Mono", "Cascadia Mono", Consolas, monospace;
  font-size: 11px;
  background: var(--accent-pale);
  padding: 1px 4px;
  border-radius: 3px;
  white-space: nowrap;
}

.confidence-bar {
  height: 4px;
  border-radius: 2px;
  background: var(--line);
  margin-top: 2px;
  overflow: hidden;
}

.confidence-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.4s ease;
}
.confidence-high   { background: var(--accent); }
.confidence-medium { background: var(--warn); }
.confidence-low    { background: var(--danger); }

.evidence-item {
  padding: 8px 10px;
  margin-bottom: 5px;
  background: #fafbfa;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  font-size: 12px;
  line-height: 1.5;
}

.evidence-item .ev-label {
  font-weight: 700;
  color: var(--accent-strong);
  margin-bottom: 2px;
  font-size: 11px;
}

.show-all-btn {
  display: block;
  width: 100%;
  padding: 5px;
  border: 1px dashed var(--line);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--muted);
  font-size: 12px;
  cursor: pointer;
  text-align: center;
  margin-top: 4px;
  transition: all 0.15s;
}

.show-all-btn:hover { border-color: var(--accent); color: var(--accent-strong); }

.raw-toggle {
  display: block;
  width: 100%;
  padding: 6px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--muted);
  font-size: 12px;
  cursor: pointer;
  text-align: center;
  margin-top: 8px;
  transition: all 0.15s;
}

.raw-toggle:hover { border-color: var(--accent); color: var(--accent-strong); }

.raw-json {
  display: none;
  margin-top: 8px;
  padding: 12px;
  background: #111816;
  color: #d7eadf;
  border-radius: var(--radius-sm);
  font-family: "SF Mono", "Cascadia Mono", Consolas, monospace;
  font-size: 11px;
  line-height: 1.55;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  max-height: 400px;
  overflow-y: auto;
}

.raw-json.visible { display: block; }

.tool-step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 0;
  font-size: 13px;
}

.tool-step .step-num {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--accent-soft);
  color: var(--accent-strong);
  font-size: 10px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.tool-step .step-name { color: var(--ink); }
.tool-step .step-desc { color: var(--muted); font-size: 11px; }

/* === Responsive === */
@media (max-width: 900px) {
  .chat-hamburger { display: block; }

  /* Sidebar overlay */
  .sidebar {
    position: fixed;
    top: 0; left: 0; bottom: 0;
    width: 280px;
    z-index: var(--sidebar-overlay-z);
    transform: translateX(-100%);
    transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 4px 0 20px rgba(0,0,0,0.12);
    background: #fff;
  }

  .sidebar.open { transform: translateX(0); }
  .sidebar-close { display: block; }
  .sidebar-backdrop.active { display: block; }

  /* Detail panel overlay */
  .detail-panel {
    position: fixed;
    top: 0; right: 0; bottom: 0;
    width: 320px;
    z-index: var(--sidebar-overlay-z);
    transform: translateX(100%);
    transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: -4px 0 20px rgba(0,0,0,0.12);
    background: #fff;
  }

  .detail-panel.open { transform: translateX(0); }
  .detail-backdrop.active { display: block; }

  /* Kill grid columns on mobile */
  .app-body {
    grid-template-columns: 0px 1fr 0px !important;
  }
  .app-body.detail-open {
    grid-template-columns: 0px 1fr 0px !important;
  }

  .chat-messages { padding: 16px; }
  .msg { max-width: 100%; }
  .chat-input-bar { padding: 10px 12px 14px; }
  .chat-brand h1 { font-size: 16px; }
  .chat-brand p { font-size: 11px; }
  .welcome-msg { margin: 40px 12px; padding: 28px 20px; }

  .chat-header { padding: 10px 14px; }
  .msg.assistant .msg-bubble { padding: 14px 16px; }
  .msg.user .msg-bubble { max-width: 100%; }
}

@media (max-width: 480px) {
  .chat-toolbar .tool-btn { font-size: 11px; padding: 3px 6px; }
  .chat-brand h1 { font-size: 15px; }
  .msg.assistant .msg-bubble { padding: 12px 14px; }
  .input-form input { font-size: 14px; padding: 10px 12px; }
  .input-form .send-btn { padding: 10px 14px; font-size: 14px; }
  .detail-panel { width: 100vw; max-width: 100vw; }
}

@media (prefers-reduced-motion: reduce) {
  .msg { animation: none; }
  .msg.loading .msg-bubble { animation: none; opacity: 0.6; }
  .app-body, .sidebar, .detail-panel { transition: none; }
  .confidence-bar-fill { transition: none; }
}
</style>
"""


SCRIPT = """
<script>
// Pass data from Python
var NB_BOOK_NAMES = """ + json.dumps(_BOOK_NAMES, ensure_ascii=False) + """;
var NB_BOOK_IDS = """ + json.dumps(_BOOK_IDS) + """;
var NB_QUESTIONS = """ + json.dumps(_BOOK_QUESTIONS, ensure_ascii=False) + """;

(function() {
  'use strict';

  var SID = 'sess_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 8);
  var BOOK_ID = 6;
  var MSGS = [];
  var SENDING = false;

  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  // ==============================
  // Book Data
  // ==============================
      presets: [
        '火焰山的火是怎么来的？',
        '分析孙悟空的人物形象',
        '分析孙悟空和唐僧的关系',
        '追踪孙悟空和唐僧关系变化',
        '猪八戒为什么会被贬下凡？',
        '孙悟空大闹天宫的原因是什么？',
        '观音在取经中的作用是什么？',
        '芭蕉扇在火焰山情节中有什么作用？',
        '唐僧取经路上最大的矛盾是什么？',
        '孙悟空从齐天大圣到行者有什么变化？'
      ]
    },
    7: {
      name: '聊斋志异',
      icon: '\U0001F98A',
      presets: [
        '《聊斋志异》如何写狐鬼故事？',
        '崂山道士说明了什么道理？',
        '画皮故事的核心冲突是什么？',
        '聊斋中的书生形象有什么特点？',
        '聊斋如何表现人鬼关系？',
        '聊斋故事为什么常有讽刺意味？'
      ]
    },
    8: {
      name: '搜神记',
      icon: '\U0001F4DC',
      presets: [
        '搜神记中的神异故事有什么特点？',
        '董永和七仙女故事讲了什么？',
        '搜神记如何组织民间传说？',
        '搜神记中的报应观念是什么？',
        '搜神记和山海经的神话叙述有什么不同？',
        '追踪一个神异事件的发展'
      ]
    },
    9: {
      name: '山海经',
      icon: '\u26f0\ufe0f',
      presets: [
        '《山海经》如何组织山川地理与神话？',
        '山海经分为哪些部分？',
        '昆仑在山海经中有什么意义？',
        '夸父逐日讲了什么？',
        '精卫填海体现了什么精神？',
        '山海经中的异兽有什么功能？',
        '追踪昆仑相关线索',
        '《山经》和《海经》有什么区别？'
      ]
    },
    10: {
      name: '水浒传',
      icon: '\u2694\ufe0f',
      presets: [
        '宋江为什么能成为梁山核心人物？',
        '分析林冲的人物转变',
        '鲁智深倒拔垂杨柳体现了什么性格？',
        '追踪宋江上梁山前后的变化',
        '分析宋江和晁盖的关系',
        '武松的性格有哪些矛盾？',
        '梁山好汉为什么会聚义？',
        '招安对梁山意味着什么？'
      ]
    }
  };

  const MODE_LABELS = {
    answer: '问答',
    analyze: '分析',
    trace: '追踪',
    enrich: '知识反馈',
    auto: '智能'
  };

  const TOOL_LABELS = {
    hybrid_search: '检索证据',
    answer: '生成回答',
    analyze: '结构化分析',
    trace: '跨章节追踪',
    enrich: '知识反馈',
    audit: '审核润色'
  };

  // ==============================
  // DOM helpers
  // ==============================
  dbg('defining helpers');
  function $(id) { var el = document.getElementById(id); if (!el) dbg('$("'+id+'")=null'); return el; }
  function esc(s) {
    return String(s ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // ==============================
  // Sidebar
  // ==============================
  function renderSidebar() {
    dbg('renderSidebar start');
    try {
    var bl = $('bookList');
    if (!bl) { dbg('FATAL: bookList null'); return; }
    dbg('bookList found, books=' + Object.keys(BOOKS).length);
    bl.innerHTML = '';
    Object.entries(BOOKS).forEach(function(entry) {
      var id = Number(entry[0]);
      var book = entry[1];
      var active = id === NB.selectedBookId ? ' active' : '';
      var btn = document.createElement('button');
      btn.className = 'book-item' + active;
      btn.dataset.bookId = String(id);
      btn.innerHTML = '<span class="book-icon">' + esc(book.icon) + '</span>' + esc(book.name);
      btn.addEventListener('click', function() { NB_UI.selectBook(id); });
      bl.appendChild(btn);
    });
    renderPresets();
  }

    dbg('renderSidebar done, items=' + bl.children.length);
    } catch(e) { dbg('renderSidebar ERROR: '+e); }
  }

  function renderPresets() {
    dbg('renderPresets start, bookId='+NB.selectedBookId);
    try {
    var book = BOOKS[NB.selectedBookId];
    var list = $('presetList');
    list.innerHTML = '';
    if (!book || !book.presets) {
      list.innerHTML = '<p style="color:var(--muted);font-size:13px;padding:12px;">暂无预设问题</p>';
      return;
    }
    if (list) {
      book.presets.forEach(function(q) {
        var btn = document.createElement('button');
        btn.className = 'preset-card';
        btn.textContent = q;
        btn.addEventListener('click', function() { NB_UI.usePreset(q); });
        list.appendChild(btn);
      });
    }
    } catch(e) { console.error('renderPresets failed:', e); }
  }

  function selectBook(id) {
    NB.selectedBookId = id;
    renderSidebar();
    closeSidebarMobile();
  }

  function usePreset(question) {
    $('chatInput').value = question;
    $('chatInput').focus();
    closeSidebarMobile();
  }

  // ==============================
  // Mobile sidebar toggle
  // ==============================
  function toggleSidebar() {
    var sidebar = $('sidebar');
    var backdrop = $('sidebarBackdrop');
    var isOpen = sidebar.classList.contains('open');
    if (isOpen) {
      closeSidebarMobile();
    } else {
      sidebar.classList.add('open');
      backdrop.classList.add('active');
    }
  }

  function closeSidebarMobile() {
    $('sidebar').classList.remove('open');
    $('sidebarBackdrop').classList.remove('active');
  }

  // ==============================
  // Advanced panel
  // ==============================
  function toggleAdvanced() {
    var panel = $('advancedPanel');
    var shown = panel.style.display !== 'none';
    panel.style.display = shown ? 'none' : 'flex';
  }

  function getProvider() {
    return ($('providerSelect') && $('providerSelect').value) || 'local';
  }

  // ==============================
  // Detail panel
  // ==============================
  function showDetail(idx) {
    NB.activeDetailIdx = idx;
    var msg = NB.messages[idx];
    if (!msg || msg.role !== 'assistant') return;
    renderDetailContent(msg);
    $('appBody').classList.add('detail-open');
    var panel = $('detailPanel');
    if (window.innerWidth <= 900) {
      panel.classList.add('open');
      $('detailBackdrop').classList.add('active');
    }
    // Update active state on all detail toggles
    document.querySelectorAll('.detail-toggle').forEach(function(btn) {
      btn.classList.toggle('active', Number(btn.dataset.msgIdx) === idx);
    });
  }

  function hideDetail() {
    NB.activeDetailIdx = -1;
    $('appBody').classList.remove('detail-open');
    $('detailPanel').classList.remove('open');
    $('detailBackdrop').classList.remove('active');
    document.querySelectorAll('.detail-toggle').forEach(function(btn) {
      btn.classList.remove('active');
    });
  }

  function renderDetailContent(msg) {
    var raw = msg.raw || {};
    var plan = msg.plan || {};
    var body = $('detailBody');
    var html = '';

    // Mode & confidence
    html += '<div class="detail-section">';
    html += '<h4>运行信息</h4>';
    html += '<div class="detail-row"><span class="dl">模式</span><span class="dv">' + esc(MODE_LABELS[msg.mode] || msg.mode) + '</span></div>';
    if (raw.run_id) {
      html += '<div class="detail-row"><span class="dl">Run ID</span><span class="dv"><code>' + esc(String(raw.run_id)) + '</code></span></div>';
    }
    if (raw.trace_id) {
      html += '<div class="detail-row"><span class="dl">Trace ID</span><span class="dv"><code>' + esc(String(raw.trace_id)) + '</code></span></div>';
    }
    if (raw.run_id) {
      html += '<div style="margin-top:6px;"><a href="/agent-runs/' + esc(String(raw.run_id)) + '" target="_blank" rel="noopener" style="font-size:12px;">打开 Trace Inspector &rarr;</a></div>';
    }

    // Plan info
    if (plan.target_name) {
      html += '<div class="detail-row"><span class="dl">目标</span><span class="dv">' + esc(String(plan.target_name)) + '</span></div>';
    }
    if (plan.target_type) {
      html += '<div class="detail-row"><span class="dl">目标类型</span><span class="dv">' + esc(String(plan.target_type)) + '</span></div>';
    }
    if (plan.analysis_type) {
      html += '<div class="detail-row"><span class="dl">分析类型</span><span class="dv">' + esc(String(plan.analysis_type)) + '</span></div>';
    }
    if (plan.trace_target_type) {
      html += '<div class="detail-row"><span class="dl">追踪对象</span><span class="dv">' + esc(String(plan.trace_target_type)) + '</span></div>';
    }

    // Confidence
    if (plan.confidence != null) {
      var pct = Math.round(plan.confidence * 100);
      var cl = pct >= 70 ? 'confidence-high' : (pct >= 40 ? 'confidence-medium' : 'confidence-low');
      html += '<div class="detail-row"><span class="dl">规划置信度</span><span class="dv">' + pct + '%</span></div>';
      html += '<div class="confidence-bar"><div class="confidence-bar-fill ' + cl + '" style="width:' + pct + '%"></div></div>';
    }

    // Reason
    if (plan.reason) {
      html += '<div class="detail-row"><span class="dl">理由</span><span class="dv">' + esc(String(plan.reason)) + '</span></div>';
    }

    // Status
    if (raw.status) {
      html += '<div class="detail-row"><span class="dl">状态</span><span class="dv">' + esc(String(raw.status)) + '</span></div>';
    }

    html += '</div>';

    // Tool sequence
    var toolSeq = plan.tool_sequence || msg.toolSequence || [];
    if (toolSeq.length > 0) {
      html += '<div class="detail-section"><h4>工具调用序列</h4>';
      toolSeq.forEach(function(step, i) {
        var name = (typeof step === 'string') ? step : (step.tool_name || step.name || '');
        var desc = (typeof step === 'object') ? (step.description || '') : '';
        html += '<div class="tool-step">';
        html += '<span class="step-num">' + (i + 1) + '</span>';
        html += '<span class="step-name">' + esc(TOOL_LABELS[name] || name) + '</span>';
        if (desc) html += '<span class="step-desc">' + esc(desc) + '</span>';
        html += '</div>';
      });
      html += '</div>';
    }

    // Evidence citations
    var evidence = raw.citations || raw.evidence || [];
    if (evidence.length > 0) {
      html += '<div class="detail-section"><h4>证据引用 (' + evidence.length + ')</h4>';
      var showCount = Math.min(evidence.length, 3);
      for (var i = 0; i < showCount; i++) {
        var item = evidence[i];
        html += '<div class="evidence-item">';
        html += '<div class="ev-label">E' + (i + 1) + ' &middot; ' + esc(item.source_type || 'citation') + '</div>';
        html += esc(String(item.excerpt || item.snippet || item.text || '').slice(0, 200));
        html += '</div>';
      }
      if (evidence.length > 3) {
        html += '<button class="show-all-btn" onclick="NB_UI._showAllEvidence(this)" data-hidden="true">显示全部 ' + evidence.length + ' 条证据</button>';
        html += '<div class="hidden-evidence" style="display:none;">';
        for (var j = 3; j < evidence.length; j++) {
          var it = evidence[j];
          html += '<div class="evidence-item">';
          html += '<div class="ev-label">E' + (j + 1) + ' &middot; ' + esc(it.source_type || 'citation') + '</div>';
          html += esc(String(it.excerpt || it.snippet || it.text || '').slice(0, 200));
          html += '</div>';
        }
        html += '</div>';
      }
      html += '</div>';
    }

    // Warnings
    if (plan.warnings && plan.warnings.length > 0) {
      html += '<div class="detail-section"><h4>警告</h4>';
      plan.warnings.forEach(function(w) {
        html += '<div style="font-size:12px;color:var(--warn);margin:2px 0;">\u26a0\ufe0f ' + esc(String(w)) + '</div>';
      });
      html += '</div>';
    }

    // Errors
    if (raw.errors && raw.errors.length > 0) {
      html += '<div class="detail-section"><h4>错误</h4>';
      raw.errors.forEach(function(e) {
        html += '<div style="font-size:12px;color:var(--danger);margin:2px 0;">' + esc(String(e)) + '</div>';
      });
      html += '</div>';
    }

    // Raw JSON toggle
    html += '<button class="raw-toggle" onclick="NB_UI._toggleRawJson(this)">展开原始 JSON</button>';
    html += '<pre class="raw-json" id="detailRawJson">' + esc(JSON.stringify(raw, null, 2)) + '</pre>';

    body.innerHTML = html;
  }

  // Exposed for onclick in detail panel
  window.NB_UI = window.NB_UI || {};
  NB_UI.selectBook = selectBook;
  NB_UI.usePreset = usePreset;
  NB_UI._showAllEvidence = function(btn) {
    var hidden = btn.nextElementSibling;
    if (hidden) {
      hidden.style.display = 'block';
      btn.style.display = 'none';
    }
  };
  NB_UI._toggleRawJson = function(btn) {
    var pre = btn.nextElementSibling;
    if (pre) {
      pre.classList.toggle('visible');
      btn.textContent = pre.classList.contains('visible') ? '收起原始 JSON' : '展开原始 JSON';
    }
  };

  // ==============================
  // Markdown / Answer rendering
  // ==============================
  function stripCiteTags(text) {
    if (!text) return '';
    // Use DOM parser for reliable HTML stripping
    var div = document.createElement('div');
    div.innerHTML = String(text);
    div.querySelectorAll('cite').forEach(function(el) { el.remove(); });
    var result = div.textContent || div.innerText || '';
    // Clean up extra whitespace around punctuation
    result = result.replace(/\s+([，。；：、,\.!\?])/g, '$1');
    return result.trim();
  }

  function renderMarkdown(text) {
    if (!text) return '';
    var cleaned = stripCiteTags(text);
    if (!cleaned) return '<p>暂无内容。</p>';

    var lines = cleaned.split('\n');
    var blocks = [];
    var listType = null;
    var listItems = [];

    function flushList() {
      if (listType) {
        blocks.push('<' + listType + '>' + listItems.join('') + '</' + listType + '>');
        listType = null;
        listItems = [];
      }
    }

    function inlineFormat(s) {
      var out = esc(s);
      // Bold **text**
      out = out.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      // Code `text`
      out = out.replace(/`([^`]+)`/g, '<code>$1</code>');
      return out;
    }

    for (var i = 0; i < lines.length; i++) {
      var line = lines[i].trim();
      if (!line) {
        flushList();
        continue;
      }

      // Headings: ### text or # text
      var hMatch = line.match(/^#{1,3}\s+(.+)$/);
      if (hMatch) {
        flushList();
        blocks.push('<h3>' + inlineFormat(hMatch[1]) + '</h3>');
        continue;
      }

      // Chinese-style headings: 关键词：内容
      var zhHeading = line.match(/^(综合判断|关键结论|核心判断|证据局限|局限|小结|总结|摘要)[：:]\s*(.*)$/);
      if (zhHeading) {
        flushList();
        blocks.push('<h3>' + inlineFormat(zhHeading[1]) + '</h3>');
        if (zhHeading[2]) blocks.push('<p>' + inlineFormat(zhHeading[2]) + '</p>');
        continue;
      }

      // Unordered list: - text or * text
      var bullet = line.match(/^[-*]\s+(.+)$/);
      if (bullet) {
        if (listType !== 'ul') flushList();
        listType = 'ul';
        listItems.push('<li>' + inlineFormat(bullet[1]) + '</li>');
        continue;
      }

      // Ordered list: 1. text or 1、text
      var numbered = line.match(/^\d+[.、]\s+(.+)$/);
      if (numbered) {
        if (listType !== 'ol') flushList();
        listType = 'ol';
        listItems.push('<li>' + inlineFormat(numbered[1]) + '</li>');
        continue;
      }

      flushList();
      blocks.push('<p>' + inlineFormat(line) + '</p>');
    }
    flushList();
    return blocks.join('') || '<p>' + esc(cleaned) + '</p>';
  }

  function buildAnswerContent(data, mode) {
    mode = mode || data.mode || 'answer';

    // INSUFFICIENT_EVIDENCE
    if (data.status === 'INSUFFICIENT_EVIDENCE') {
      return '<div class="insufficient">\u26a0\ufe0f 检索未找到足够证据来回答这个问题。您可以尝试换个问法，或者选择其他书籍。</div>';
    }

    // analyze mode
    if (mode === 'analyze') {
      var analysis = data.analysis || {};
      var parts = [];
      if (analysis.summary && analysis.summary.length > 5) {
        parts.push('<h3>摘要</h3><p>' + esc(stripCiteTags(analysis.summary)) + '</p>');
      }
      if (analysis.key_points && analysis.key_points.length > 0) {
        parts.push('<h3>关键结论</h3><ol>');
        analysis.key_points.forEach(function(p) {
          var point = (typeof p === 'string') ? p : (p.point || p.summary || p.claim || '');
          parts.push('<li>' + esc(stripCiteTags(String(point))) + '</li>');
        });
        parts.push('</ol>');
      }
      if (analysis.limitations && analysis.limitations.length > 0) {
        parts.push('<h3>局限</h3><ul>');
        analysis.limitations.forEach(function(l) {
          parts.push('<li>' + esc(stripCiteTags(String(l))) + '</li>');
        });
        parts.push('</ul>');
      }
      if (data.answer && !analysis.summary) {
        // Fallback to raw answer
        return renderMarkdown(data.answer);
      }
      return parts.length > 0 ? parts.join('') : renderMarkdown(data.answer || '已完成分析。');
    }

    // trace mode
    if (mode === 'trace') {
      var timeline = data.timeline || [];
      if (timeline.length > 0) {
        var items = [];
        items.push('<h3>时间线</h3><ol>');
        timeline.forEach(function(item) {
          var ch = item.chapter_number ? '第 ' + item.chapter_number + ' 回' : (item.chapter_id ? '章节 ' + item.chapter_id : '');
          var title = item.chapter_title || '';
          var label = ch + (title ? ' ' + title : '');
          var summary = item.summary || item.kind || '';
          items.push('<li><strong>' + esc(label) + '</strong>：' + esc(stripCiteTags(String(summary))) + '</li>');
        });
        items.push('</ol>');
        return items.join('');
      }
      return renderMarkdown(data.answer || '已完成追踪，但未形成可展示的时间线。');
    }

    // enrich mode
    if (mode === 'enrich') {
      var patchCount = (data.patches || []).length;
      if (patchCount > 0) {
        return '<div class="patch-count-notice">已生成 <strong>' + patchCount + '</strong> 个 KnowledgePatch 候选，状态为待审核；系统不会自动合并到知识库。</div>';
      }
      return renderMarkdown(data.answer || '未生成 KnowledgePatch 候选。');
    }

    // Default: render answer as markdown
    return renderMarkdown(data.answer || '暂无回答。');
  }

  // ==============================
  // Chat rendering
  // ==============================
  function renderChat() {
    var container = $('chatMessages');
    var html = '';
    if (NB.messages.length === 0) {
      html = '<div class="welcome-msg">'
        + '<div class="welcome-icon">\U0001F4D6</div>'
        + '<h2>NovelBridge 阅读智能体</h2>'
        + '<p>文学知识库问答与分析</p>'
        + '<p class="welcome-hint">选择左侧书库中的书籍和参考问题，或直接输入您的问题开始分析。</p>'
        + '</div>';
    } else {
      NB.messages.forEach(function(msg, idx) {
        html += renderMessage(msg, idx);
      });
    }
    container.innerHTML = html;
    scrollToBottom();
  }

  function renderMessage(msg, idx) {
    if (msg.role === 'user') {
      return '<div class="msg user">'
        + '<div class="msg-wrapper"><div class="msg-bubble">' + esc(msg.content) + '</div></div>'
        + '<div class="msg-meta">' + esc(NB.sessionId.slice(-6)) + '</div>'
        + '</div>';
    }

    // Assistant message
    var mode = msg.mode || 'answer';
    var modeChip = '<span class="mode-chip ' + mode + '">' + esc(MODE_LABELS[mode] || mode) + '</span>';
    var status = msg.raw && msg.raw.status ? ' \u00b7 ' + esc(msg.raw.status) : '';
    var detailBtn = '<button class="detail-toggle' + (NB.activeDetailIdx === idx ? ' active' : '') + '" data-msg-idx="' + idx + '">调试详情</button>';

    return '<div class="msg assistant">'
      + '<div class="msg-bubble">'
      + '<div class="msg-header">' + modeChip + '<div class="msg-status">' + detailBtn + '</div></div>'
      + '<div class="msg-content">' + msg.content + '</div>'
      + '</div>'
      + '</div>';
  }

  function appendLoadingMessage() {
    var idx = NB.messages.length;
    var el = document.createElement('div');
    el.className = 'msg assistant loading';
    el.id = 'loadingMsg';
    el.innerHTML = '<div class="msg-bubble">'
      + '<div class="msg-header"><span class="mode-chip answer">规划中...</span></div>'
      + '<div class="msg-content"><p style="color:var(--muted);">正在分析问题并检索证据...</p></div>'
      + '</div>';
    $('chatMessages').appendChild(el);
    scrollToBottom();
    return el;
  }

  function removeLoadingMessage() {
    var el = $('loadingMsg');
    if (el) el.remove();
  }

  function scrollToBottom() {
    var container = $('chatMessages');
    requestAnimationFrame(function() {
      container.scrollTop = container.scrollHeight;
    });
  }

  // ==============================
  // API calls
  // ==============================
  async function callPlan(question, bookId) {
    try {
      var resp = await fetch('/api/reader-agent/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          book_id: bookId,
          question: question.trim(),
          preferred_mode: 'auto',
          provider: getProvider(),
          session_id: NB.sessionId,
          model_mode: 'deterministic'
        })
      });
      if (!resp.ok) return null;
      return await resp.json();
    } catch (e) {
      console.warn('Plan API call failed:', e);
      return null;
    }
  }

  async function callRun(payload) {
    var resp = await fetch('/api/reader-agent/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!resp.ok) {
      var errText = await resp.text().catch(function() { return 'Unknown error'; });
      throw new Error('Run API returned ' + resp.status + ': ' + errText.slice(0, 200));
    }
    return await resp.json();
  }

  // ==============================
  // Send message flow
  // ==============================
  async function sendMessage(questionText) {
    if (NB.isSending) return;
    var q = String(questionText || '').trim();
    if (!q) return;

    NB.isSending = true;
    $('sendBtn').disabled = true;
    $('sendBtn').textContent = '...';

    // Add user message
    NB.messages.push({ role: 'user', content: q });
    renderChat();
    var loadingEl = appendLoadingMessage();

    try {
      // Step 1: Plan
      var plan = await callPlan(q, NB.selectedBookId);
      if (!plan) {
        // Fallback plan
        plan = {
          mode: 'answer',
          reason: '使用前端规则（后端 planner 不可用）',
          optimized_question: '请基于证据直接回答：' + q,
          confidence: 0.4,
          warnings: ['后端 planner 不可用，使用前端规则替代。'],
          tool_sequence: [
            { tool_name: 'hybrid_search', description: '检索相关文本' },
            { tool_name: 'answer', description: '生成回答' },
            { tool_name: 'audit', description: '审核润色' }
          ],
          request_patch: { mode: 'answer', question: '请基于证据直接回答：' + q, target_name: '', target_type: '', analysis_type: null, trace_target_type: null, tool_sequence: null }
        };
      }

      // Update loading message
      if (loadingEl) {
        var loadingBubble = loadingEl.querySelector('.msg-bubble');
        if (loadingBubble) {
          var modeLabel = MODE_LABELS[plan.mode] || plan.mode || 'answer';
          loadingBubble.innerHTML = '<div class="msg-header">'
            + '<span class="mode-chip ' + (plan.mode || 'answer') + '">' + esc(modeLabel) + '</span></div>'
            + '<div class="msg-content"><p style="color:var(--muted);">正在检索证据并生成回答...</p></div>';
        }
      }

      // Build payload from plan
      var patch = plan.request_patch || {};
      var payload = {
        mode: patch.mode || plan.mode || 'answer',
        book_id: NB.selectedBookId,
        question: patch.question || plan.optimized_question || q,
        target_name: patch.target_name || plan.target_name || undefined,
        target_type: patch.target_type || plan.target_type || undefined,
        analysis_type: patch.analysis_type || plan.analysis_type || undefined,
        trace_target_type: patch.trace_target_type || plan.trace_target_type || undefined,
        session_id: NB.sessionId,
        options: {
          provider: getProvider(),
          require_citations: true,
          top_k: 8
        },
        tool_sequence: plan.tool_sequence || undefined
      };

      // Step 2: Run
      var data = await callRun(payload);

      // Build answer content
      var mode = data.mode || plan.mode || 'answer';
      var answerHtml = buildAnswerContent(data, mode);

      // Append assistant message
      NB.messages.push({
        role: 'assistant',
        content: answerHtml,
        mode: mode,
        raw: data,
        plan: plan,
        toolSequence: plan.tool_sequence || [],
        runId: data.run_id
      });
    } catch (err) {
      NB.messages.push({
        role: 'assistant',
        content: '<div class="error-notice">请求失败：' + esc(String(err.message || err)) + '</div>',
        mode: 'answer',
        raw: { errors: [String(err)] },
        plan: {},
        toolSequence: []
      });
    } finally {
      removeLoadingMessage();
      renderChat();
      NB.isSending = false;
      $('sendBtn').disabled = false;
      $('sendBtn').textContent = '发送';
      $('chatInput').focus();
    }
  }

  // ==============================
  // Session management
  // ==============================
  function clearSession() {
    NB.messages = [];
    NB.activeDetailIdx = -1;
    hideDetail();
    renderChat();
  }

  function newSession() {
    NB.sessionId = 'sess_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 8);
    $('sessionIdDisplay').textContent = NB.sessionId.slice(0, 16) + '...';
    clearSession();
  }

  // ==============================
  // Health check
  // ==============================
  async function refreshHealth() {
    var services = [
      { id: 'health-mysql', name: 'MySQL', endpoint: 'mysql' },
      { id: 'health-qdrant', name: 'Qdrant', endpoint: 'qdrant' },
      { id: 'health-neo4j', name: 'Neo4j', endpoint: 'neo4j' },
      { id: 'health-llm', name: '9B', endpoint: 'llm' },
      { id: 'health-embedding', name: 'Embed', endpoint: 'embedding' }
    ];

    services.forEach(function(svc) {
      var el = $(svc.id);
      if (!el) return;
      var nameSpan = el.querySelector('.health-name');
      var dot = el.querySelector('.health-dot');
      if (nameSpan) nameSpan.textContent = svc.name;
      if (dot) { dot.className = 'health-dot'; }
      el.title = '检查中...';
    });

    for (var i = 0; i < services.length; i++) {
      var svc = services[i];
      var el = $(svc.id);
      var dot = el ? el.querySelector('.health-dot') : null;
      try {
        var resp = await fetch('/health/' + svc.endpoint);
        var data = await resp.json();
        var ok = data.status === 'ok';
        if (dot) dot.className = 'health-dot ' + (ok ? 'ok' : 'bad');
        el.title = data.detail || (ok ? '正常' : '异常');
      } catch (e) {
        if (dot) dot.className = 'health-dot bad';
        el.title = '连接失败: ' + String(e);
      }
    }
  }

  // ==============================
  // Init DeepSeek toggle
  // ==============================
  function initDeepSeek() {
    if (window.NB_DEEPSEEK_CONFIGURED) {
      var opt = document.querySelector('#providerSelect option[value="deepseek"]');
      if (opt) {
        opt.disabled = false;
        opt.textContent = 'DeepSeek';
        $('providerSelect').value = 'deepseek';
      }
    } else {
      var opt = document.querySelector('#providerSelect option[value="deepseek"]');
      if (opt) {
        opt.disabled = true;
        opt.textContent = 'DeepSeek（未配置）';
      }
    }
  }

  // ==============================
  // Event binding
  // ==============================
  function bindEvents() {
    // Chat form submit
    $('chatForm').addEventListener('submit', function(e) {
      e.preventDefault();
      var input = $('chatInput');
      var q = input.value.trim();
      if (!q || NB.isSending) return;
      input.value = '';
      sendMessage(q);
    });

    // Sidebar hamburger
    $('chatHamburger').addEventListener('click', toggleSidebar);
    $('sidebarClose').addEventListener('click', closeSidebarMobile);
    $('sidebarBackdrop').addEventListener('click', closeSidebarMobile);

    // Detail close
    $('detailClose').addEventListener('click', hideDetail);
    $('detailBackdrop').addEventListener('click', hideDetail);

    // Detail toggle buttons (delegation)
    $('chatMessages').addEventListener('click', function(e) {
      var btn = e.target.closest('.detail-toggle');
      if (!btn) return;
      var idx = parseInt(btn.dataset.msgIdx);
      if (isNaN(idx)) return;
      if (NB.activeDetailIdx === idx) {
        hideDetail();
      } else {
        showDetail(idx);
      }
    });

    // Toolbar buttons
    $('clearSessionBtn').addEventListener('click', clearSession);
    $('newSessionBtn').addEventListener('click', newSession);
    $('advancedToggleBtn').addEventListener('click', toggleAdvanced);
    $('refreshHealthBtn').addEventListener('click', refreshHealth);

    // Input Enter key (submit handled by form)
    $('chatInput').addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        $('chatForm').dispatchEvent(new Event('submit'));
      }
    });

    // Close sidebar on Escape
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        closeSidebarMobile();
        hideDetail();
      }
    });

    // Handle window resize for detail panel
    window.addEventListener('resize', function() {
      if (window.innerWidth > 900) {
        $('detailPanel').classList.remove('open');
        $('detailBackdrop').classList.remove('active');
        $('sidebar').classList.remove('open');
        $('sidebarBackdrop').classList.remove('active');
      }
    });
  }

  // ==============================
  // Initialization
  // ==============================
  function init() {
    dbg('init() start');
    try {
    $('sessionIdDisplay').textContent = NB.sessionId.slice(0, 16) + '...';
    dbg('init: done sessionId');
    initDeepSeek();
    dbg('init: done initDeepSeek');
    renderSidebar();
    dbg('init: done renderSidebar');
    renderChat();
    dbg('init: done renderChat');
    bindEvents();
    dbg('init: done bindEvents');
    refreshHealth();
    dbg('init: done refreshHealth');
    } catch(e) { dbg('init ERROR: '+e); }
  }

  dbg('registering DOMContentLoaded');
  document.addEventListener('DOMContentLoaded', init);
  dbg('script end (waiting for DOM)');

})();
</script>
"""


@router.get("/demo", response_class=HTMLResponse)
async def demo_page():
    """@NB-ENTRYPOINT Stage 6C browser demo — research reading workspace."""
    deepseek_configured = "true" if settings.deepseek_api_key.strip() else "false"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f4f6f2">
  <title>NovelBridge 阅读智能体</title>
  {STYLE}
</head>
<body>
<a href="#chatInput" style="position:absolute;left:-999px;top:0;color:var(--muted);">跳到输入框</a>

<div class="app-shell">
  <!-- Health Strip -->
  <div class="health-strip" aria-label="服务健康状态">
    <span class="health-title">服务状态</span>
    <span class="health-sep">|</span>
    <span class="health-item" id="health-mysql"><span class="health-dot"></span><span class="health-name">MySQL</span></span>
    <span class="health-item" id="health-qdrant"><span class="health-dot"></span><span class="health-name">Qdrant</span></span>
    <span class="health-item" id="health-neo4j"><span class="health-dot"></span><span class="health-name">Neo4j</span></span>
    <span class="health-item" id="health-llm"><span class="health-dot"></span><span class="health-name">9B</span></span>
    <span class="health-item" id="health-embedding"><span class="health-dot"></span><span class="health-name">Embed</span></span>
    <span class="health-sep">|</span>
    <a href="/browse" style="font-size:12px;color:var(--accent);white-space:nowrap;">书库</a>
    <a href="/agent-runs" style="font-size:12px;color:var(--accent);white-space:nowrap;">Trace</a>
    <button class="health-refresh" id="refreshHealthBtn" type="button">刷新</button>
  </div>

  <!-- Main App Body -->
  <div class="app-body" id="appBody">

    <!-- ===== Left Sidebar ===== -->
    <aside class="sidebar" id="sidebar" aria-label="书库与问题">
      <div class="sidebar-header">
        <button class="sidebar-close" id="sidebarClose" type="button" aria-label="关闭侧边栏">✕</button>
        <h2>书库</h2>
      </div>
      <div class="book-list" id="bookList" role="listbox" aria-label="选择书籍"></div>
      <div class="presets-section">
        <h3>参考问题</h3>
        <div class="preset-list" id="presetList"></div>
      </div>
    </aside>

    <!-- ===== Center Chat ===== -->
    <main class="chat-main" aria-label="对话区域">
      <header class="chat-header">
        <button class="chat-hamburger" id="chatHamburger" type="button" aria-label="打开书库">☰</button>
        <div class="chat-brand">
          <h1>NovelBridge 阅读智能体</h1>
          <p>文学知识库问答与分析</p>
        </div>
        <div class="chat-toolbar">
          <button class="tool-btn" id="advancedToggleBtn" type="button" title="高级选项">⚙</button>
          <button class="tool-btn" id="clearSessionBtn" type="button">清空会话</button>
          <button class="tool-btn" id="newSessionBtn" type="button">新建会话</button>
        </div>
      </header>

      <!-- Advanced options panel -->
      <div class="advanced-panel" id="advancedPanel" style="display:none;">
        <label>模型来源
          <select id="providerSelect" name="provider">
            <option value="local">本地 9B</option>
            <option value="deepseek">DeepSeek</option>
          </select>
        </label>
        <span class="session-id-label">会话 <code id="sessionIdDisplay">---</code></span>
      </div>

      <!-- Messages area -->
      <div class="chat-messages" id="chatMessages" aria-live="polite" aria-label="消息列表"></div>

      <!-- Input bar -->
      <div class="chat-input-bar">
        <form class="input-form" id="chatForm" autocomplete="off">
          <input
            type="text"
            id="chatInput"
            placeholder="输入关于本书的问题..."
            autocomplete="off"
            aria-label="输入问题"
          >
          <button type="submit" class="send-btn" id="sendBtn">发送</button>
        </form>
        <div class="input-hint">模式自动选择 · 同一会话支持追问</div>
      </div>
    </main>

    <!-- ===== Right Detail Panel ===== -->
    <aside class="detail-panel" id="detailPanel" aria-label="调试详情">
      <div class="detail-header">
        <h3>调试详情</h3>
        <button class="detail-close" id="detailClose" type="button" aria-label="关闭详情">✕</button>
      </div>
      <div class="detail-body" id="detailBody">
        <p style="color:var(--muted);font-size:13px;text-align:center;margin-top:40px;">
          点击回答中的「调试详情」查看运行信息
        </p>
      </div>
    </aside>

    <!-- Overlay backdrops -->
    <div class="sidebar-backdrop" id="sidebarBackdrop"></div>
    <div class="detail-backdrop" id="detailBackdrop"></div>
  </div>
</div>

<script>window.NB_DEEPSEEK_CONFIGURED = {deepseek_configured};</script>
{SCRIPT}
</body>
</html>"""
