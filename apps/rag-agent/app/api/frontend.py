"""Modern browser UI for the Python-first NovelBridge demo."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.demo import demo_page

router = APIRouter(tags=["frontend"])

db_client = None
API_BASE = "http://127.0.0.1:18079"


def init_router(db):
    global db_client
    db_client = db


CSS_LINK = '<link rel="stylesheet" href="/static/shared.css">'


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _json_block(data: Any) -> str:
    text = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    return f"<pre>{_esc(text)}</pre>"


def _badge(status: str) -> str:
    cls = "warn"
    if status in {"SUCCESS", "RESPONDED", "DONE", "ok", "COMPLETED"}:
        cls = "ok"
    elif status in {"FAILED", "INSUFFICIENT_EVIDENCE", "error", "degraded"}:
        cls = "bad"
    return f"<span class='pill {cls}'>{_esc(status)}</span>"


def _page(title: str, body: str, subtitle: str = "") -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f4f6f2">
  <title>{_esc(title)} - NovelBridge</title>
  {CSS_LINK}
</head>
<body>
  <a href="#main" class="muted" style="position:absolute;left:-999px;">跳到主要内容</a>
  <main id="main" class="shell">
    <header class="topbar">
      <div class="brand">
        <h1>{_esc(title)}</h1>
        <p>{_esc(subtitle)}</p>
      </div>
      <nav class="nav" aria-label="主导航">
        <a href="/demo">演示台</a>
        <a href="/pipeline">流水线</a>
        <a href="/browse">书库</a>
        <a href="/search">搜索</a>
        <a href="/agent-runs">Trace Inspector</a>
        <a href="/config">⚙ 配置</a>
        <a href="/docs">API 文档</a>
      </nav>
    </header>
    {body}
  </main>
</body>
</html>"""


async def _get_json(path: str, timeout: int = 15):
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(f"{API_BASE}{path}")
        response.raise_for_status()
        return response.json()


@router.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/demo")


@router.get("/demo", response_class=HTMLResponse)
async def demo_console():
    return await demo_page()


@router.get("/qa", include_in_schema=False)
async def qa_redirect():
    return RedirectResponse(url="/demo")


@router.get("/upload", include_in_schema=False)
async def upload_redirect():
    return RedirectResponse(url="/demo")


@router.get("/pipeline/{book_id}", include_in_schema=False)
async def pipeline_redirect(book_id: int):
    return RedirectResponse(url=f"/browse/book/{book_id}")


@router.get("/browse", response_class=HTMLResponse)
async def browse_index():
    """New compact book browser for the demo."""
    try:
        books = await _get_json("/api/books")
    except Exception as exc:
        body = f"<section class='panel'><div class='panel-body'>{_badge('error')} {_esc(exc)}</div></section>"
        return _page("书库", body, "书籍数据来自 Python API 和结构化知识库。")

    rows = []
    total_chapters = 0
    total_chunks = 0
    for book in books:
        total_chapters += int(book.get("chapter_count") or 0)
        total_chunks += int(book.get("chunk_count") or 0)
        rows.append(
            "<tr>"
            f"<td><a href='/browse/book/{_esc(book.get('id'))}'>{_esc(book.get('title'))}</a>"
            f"<div class='muted'>{_esc(book.get('author') or '')}</div></td>"
            f"<td>{_esc(book.get('chapter_count'))}</td>"
            f"<td>{_esc(book.get('chunk_count'))}</td>"
            f"<td>{_esc(book.get('entity_count'))}</td>"
            f"<td>{_esc(book.get('relation_count'))}</td>"
            "</tr>"
        )

    body = f"""
    <section class="grid" aria-label="语料指标">
      <div class="metric"><b>书籍</b><span>{len(books)}</span></div>
      <div class="metric"><b>章节</b><span>{total_chapters}</span></div>
      <div class="metric"><b>文本块</b><span>{total_chunks}</span></div>
    </section>
    <section class="panel">
      <div class="panel-head"><h2>语料库</h2><a href="/demo">运行 ReaderAgent</a></div>
      <div class="panel-body">
        <table>
          <thead><tr><th>书籍</th><th>章节</th><th>文本块</th><th>实体</th><th>关系</th></tr></thead>
          <tbody>{''.join(rows) if rows else "<tr><td colspan='5' class='muted'>暂无书籍。</td></tr>"}</tbody>
        </table>
      </div>
    </section>
    """
    return _page("书库", body, "已处理经典小说的语料概览。")


@router.get("/browse/book/{book_id}", response_class=HTMLResponse)
async def browse_book(book_id: int):
    try:
        book = await _get_json(f"/api/books/{book_id}")
        chapters = await _get_json(f"/api/books/{book_id}/chapters")
        entities = await _get_json(f"/api/books/{book_id}/entities?min_mentions=2&limit=30")
    except Exception as exc:
        body = f"<section class='panel'><div class='panel-body'>{_badge('error')} {_esc(exc)}</div></section>"
        return _page(f"书籍 {book_id}", body)

    chapter_rows = "".join(
        f"<tr><td>{_esc(ch.get('chapter_number'))}</td>"
        f"<td><a href='/browse/chapter/{_esc(ch.get('id'))}'>{_esc(ch.get('title'))}</a></td>"
        f"<td>{_esc(ch.get('raw_length'))}</td><td>{_esc(ch.get('chunk_count', 0))}</td></tr>"
        for ch in chapters[:60]
    )
    entity_rows = "".join(
        f"<tr><td>{_esc(e.get('canonical_name'))}</td><td>{_esc(e.get('entity_type'))}</td>"
        f"<td>{_esc(e.get('mention_count'))}</td><td class='muted'>{_esc(', '.join(e.get('aliases') or [])[:80])}</td></tr>"
        for e in entities[:30]
    )
    body = f"""
    <section class="grid" aria-label="书籍指标">
      <div class="metric"><b>章节</b><span>{_esc(book.get('chapter_count'))}</span></div>
      <div class="metric"><b>文本块</b><span>{_esc(book.get('chunk_count'))}</span></div>
      <div class="metric"><b>实体</b><span>{_esc(book.get('entity_count'))}</span></div>
      <div class="metric"><b>关系</b><span>{_esc(book.get('relation_count'))}</span></div>
    </section>
    <section class="panel">
      <div class="panel-head"><h2>章节</h2><a href="/demo">询问 ReaderAgent</a></div>
      <div class="panel-body"><table><thead><tr><th>#</th><th>标题</th><th>字数</th><th>文本块</th></tr></thead><tbody>{chapter_rows}</tbody></table></div>
    </section>
    <section class="panel">
      <div class="panel-head"><h2>高频实体</h2></div>
      <div class="panel-body"><table><thead><tr><th>名称</th><th>类型</th><th>提及</th><th>别名</th></tr></thead><tbody>{entity_rows}</tbody></table></div>
    </section>
    """
    title = str(book.get("title") or f"Book {book_id}")
    return _page(title, body, "结构化数据预览。证据问答和分析请使用演示控制台。")


@router.get("/browse/chapter/{chapter_id}", response_class=HTMLResponse)
async def browse_chapter(chapter_id: int):
    try:
        fact = await _get_json(f"/api/chapters/{chapter_id}/fact")
    except Exception as exc:
        body = f"<section class='panel'><div class='panel-body'>{_badge('error')} {_esc(exc)}</div></section>"
        return _page(f"章节 {chapter_id}", body)
    body = f"""
    <section class="panel">
      <div class="panel-head"><h2>章节事实</h2>{_badge(str(fact.get('evidence_status') or 'unknown'))}</div>
      <div class="panel-body">
        <p>{_esc(fact.get('summary') or '暂无摘要。')}</p>
        {_json_block({k: fact.get(k) for k in ('characters', 'relations', 'events')})}
      </div>
    </section>
    """
    title = f"Ch. {fact.get('chapter_number', chapter_id)}"
    return _page(title, body, str(fact.get("chapter_title") or ""))


@router.get("/search", response_class=HTMLResponse)
async def search_page(q: str = ""):
    rows = ""
    if q:
        try:
            data = await _get_json(f"/api/search?q={quote_plus(q)}&limit=30")
            for item in data.get("results", []):
                rows += (
                    "<tr>"
                    f"<td>{_esc(item.get('type'))}</td>"
                    f"<td>{_esc(item.get('title'))}<div class='muted'>{_esc((item.get('snippet') or '')[:220])}</div></td>"
                    "</tr>"
                )
        except Exception as exc:
            rows = f"<tr><td colspan='2'>{_badge('error')} {_esc(exc)}</td></tr>"
    body = f"""
    <section class="panel">
      <div class="panel-head"><h2>搜索</h2></div>
      <div class="panel-body">
        <form class="search" method="get" action="/search">
          <label style="position:absolute;left:-999px;" for="q">搜索关键词</label>
          <input id="q" name="q" autocomplete="off" value="{_esc(q)}" placeholder="搜索人物、地点、事件或原文片段...">
          <button type="submit">搜索</button>
        </form>
      </div>
    </section>
    <section class="panel">
      <div class="panel-head"><h2>结果</h2></div>
      <div class="panel-body"><table><thead><tr><th>类型</th><th>命中</th></tr></thead><tbody>{rows or "<tr><td colspan='2' class='muted'>请输入搜索词。</td></tr>"}</tbody></table></div>
    </section>
    """
    return _page("搜索", body, "跨文本块和结构化数据快速查找。")


@router.get("/agent-runs", response_class=HTMLResponse)
async def agent_runs_page(limit: int = 50, run_type: str | None = None):
    params = f"?limit={limit}"
    if run_type:
        params += f"&run_type={run_type}"
    try:
        runs = await _get_json(f"/api/reader-agent/runs{params}")
    except Exception as exc:
        runs = []
        error = str(exc)
    else:
        error = ""
    rows = ""
    for run in runs:
        run_id = run.get("id")
        rows += (
            "<tr>"
            f"<td class='mono'>{_esc(run_id)}</td>"
            f"<td>{_esc(run.get('run_type'))}</td>"
            f"<td>{_badge(str(run.get('status') or ''))}</td>"
            f"<td class='muted'>{_esc(run.get('started_at'))}</td>"
            f"<td><a href='/agent-runs/{_esc(run_id)}'>查看</a></td>"
            "</tr>"
        )
    if not rows:
        rows = "<tr><td colspan='5' class='muted'>暂无运行记录。</td></tr>"

    # — Sessions section —
    session_rows = ""
    try:
        async with httpx.AsyncClient(base_url=API_BASE, timeout=10) as client:
            sessions = await _get_json("/api/reader-agent/sessions")
            for sess in (sessions or [])[:20]:
                sid = sess.get("session_id")
                sess_id = _esc(sid)
                last_q = _esc(sess.get("last_question", "")[:80])
                last_mode = _esc(sess.get("last_mode", ""))
                turn_count = sess.get("turn_count", 0)
                target = _esc(sess.get("current_target", ""))
                session_rows += (
                    f"<tr><td class='mono'>{sess_id}</td>"
                    f"<td>{turn_count}</td>"
                    f"<td>{_badge(last_mode) if last_mode else '-'}</td>"
                    f"<td class='muted'>{last_q or '-'}</td>"
                    f"<td class='muted'>{target or '-'}</td>"
                    f"<td><a href='/agent-runs/sessions/{sess_id}'>查看</a></td></tr>"
                )
    except Exception:
        pass
    if not session_rows:
        session_rows = "<tr><td colspan='6' class='muted'>暂无活跃会话。</td></tr>"

    body = f"""
    <section class="panel">
      <div class="panel-head"><h2>筛选</h2></div>
      <div class="panel-body">
        <form class="search" method="get" action="/agent-runs">
          <label style="position:absolute;left:-999px;" for="run_type">运行类型</label>
          <input id="run_type" name="run_type" autocomplete="off" value="{_esc(run_type or '')}" placeholder="ReaderAgent 或 PreprocessAgent...">
          <button type="submit">筛选</button>
        </form>
      </div>
    </section>
    {'<section class="panel"><div class="panel-body">' + _badge('error') + ' ' + _esc(error) + '</div></section>' if error else ''}
    <section class="panel">
      <div class="panel-head"><h2>会话记忆</h2><a href="/demo">新会话</a></div>
      <div class="panel-body"><table><thead><tr><th>会话 ID</th><th>轮次</th><th>模式</th><th>最近提问</th><th>当前目标</th><th>详情</th></tr></thead><tbody>{session_rows}</tbody></table></div>
    </section>
    <section class="panel">
      <div class="panel-head"><h2>运行记录</h2><a href="/demo">创建运行</a></div>
      <div class="panel-body"><table><thead><tr><th>ID</th><th>类型</th><th>状态</th><th>开始时间</th><th>Trace</th></tr></thead><tbody>{rows}</tbody></table></div>
    </section>
    """
    return _page("Trace Inspector", body, "查看 AgentRun、AgentStep、ModelCall、ToolCall、RetrievalTrace、KnowledgePatch 和会话记忆。")


@router.get("/agent-runs/{run_id}", response_class=HTMLResponse)
async def agent_run_detail_page(run_id: int):
    try:
        trace = await _get_json(f"/api/reader-agent/runs/{run_id}/trace", timeout=20)
    except Exception as exc:
        body = f"<section class='panel'><div class='panel-body'>{_badge('error')} {_esc(exc)}</div></section>"
        return _page(f"Run {run_id}", body)

    run = trace.get("run") or {}
    steps = trace.get("steps") or []
    model_calls = trace.get("model_calls") or []
    tool_calls = trace.get("tool_calls") or []
    retrieval_traces = trace.get("retrieval_traces") or []
    patches = trace.get("patches") or []
    output = run.get("output_json") if isinstance(run.get("output_json"), dict) else {}
    timeline = output.get("timeline_preview") or []

    step_rows = "".join(
        f"<tr><td>{_esc(s.get('step_order'))}</td><td>{_esc(s.get('step_type'))}</td><td>{_badge(str(s.get('status') or ''))}</td></tr>"
        for s in steps
    ) or "<tr><td colspan='3' class='muted'>暂无步骤。</td></tr>"
    timeline_rows = "".join(
        f"<tr><td>{_esc(item.get('chapter_number') or item.get('chapter_id'))}</td><td>{_esc(item.get('kind'))}</td><td>{_esc(item.get('summary'))}<div class='muted'>{_esc(item.get('chapter_title') or '')}</div></td></tr>"
        for item in timeline
    ) or "<tr><td colspan='3' class='muted'>暂无时间线预览。</td></tr>"

    body = f"""
    <section class="grid">
      <div class="metric"><b>状态</b><span>{_esc(run.get('status'))}</span></div>
      <div class="metric"><b>步骤</b><span>{len(steps)}</span></div>
      <div class="metric"><b>模型调用</b><span>{len(model_calls)}</span></div>
      <div class="metric"><b>工具调用</b><span>{len(tool_calls)}</span></div>
      <div class="metric"><b>检索</b><span>{len(retrieval_traces)}</span></div>
      <div class="metric"><b>补丁</b><span>{len(patches)}</span></div>
    </section>
    <section class="panel">
      <div class="panel-head"><h2>时间线预览</h2></div>
      <div class="panel-body"><table><thead><tr><th>章节</th><th>类型</th><th>摘要</th></tr></thead><tbody>{timeline_rows}</tbody></table></div>
    </section>
    <section class="panel">
      <div class="panel-head"><h2>步骤</h2></div>
      <div class="panel-body"><table><thead><tr><th>#</th><th>类型</th><th>状态</th></tr></thead><tbody>{step_rows}</tbody></table></div>
    </section>
    <section class="panel">
      <div class="panel-head"><h2>原始 Trace JSON</h2></div>
      <div class="panel-body">{_json_block(trace)}</div>
    </section>
    """
    return _page(f"Run {run_id}", body, str(run.get("run_type") or "Agent trace"))


@router.get("/agent-runs/sessions/{session_id}", response_class=HTMLResponse)
async def agent_session_page(session_id: int):
    try:
        session = await _get_json(f"/api/reader-agent/sessions/{session_id}")
    except Exception as exc:
        body = f"<section class='panel'><div class='panel-body'>{_badge('error')} {_esc(exc)}</div></section>"
        return _page(f"Session {session_id}", body)

    turns = session.get("turns") or []
    turn_rows = "".join(
        f"<tr><td>{_esc(t.get('mode'))}</td>"
        f"<td>{_esc(t.get('question')[:100])}</td>"
        f"<td class='muted'>{_esc(t.get('answer_preview')[:80])}</td>"
        f"<td>{_esc(t.get('target_name') or '-')}</td>"
        f"<td>{_esc(t.get('evidence_count'))}</td>"
        f"<td><a href='/agent-runs/{t.get('run_id')}'>#{t.get('run_id')}</a></td></tr>"
        for t in turns[-20:]
    ) or "<tr><td colspan='6' class='muted'>暂无记录。</td></tr>"

    body = f"""
    <section class="grid">
      <div class="metric"><b>会话 ID</b><span>{_esc(session_id)}</span></div>
      <div class="metric"><b>轮次</b><span>{session.get('turn_count', 0)}</span></div>
      <div class="metric"><b>当前目标</b><span>{_esc(session.get('current_target_name') or '-')}</span></div>
      <div class="metric"><b>上次 Run</b><span>#{_esc(session.get('last_run_id') or '-')}</span></div>
    </section>
    <section class="panel">
      <div class="panel-head"><h2>会话上下文</h2></div>
      <div class="panel-body"><p class="muted">{_esc(session.get('context_summary', ''))}</p></div>
    </section>
    <section class="panel">
      <div class="panel-head"><h2>问答记录</h2></div>
      <div class="panel-body"><table><thead><tr><th>模式</th><th>问题</th><th>回答预览</th><th>目标</th><th>证据</th><th>Run</th></tr></thead><tbody>{turn_rows}</tbody></table></div>
    </section>
    """
    return _page(f"Session {session_id}", body, "会话记忆详情")


@router.get("/pipeline", response_class=HTMLResponse)
async def pipeline_page():
    html = Path("app/static/pipeline.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@router.get("/config", response_class=HTMLResponse)
async def config_page():
    html = Path("app/static/config.html").read_text(encoding="utf-8")
    return HTMLResponse(html)
