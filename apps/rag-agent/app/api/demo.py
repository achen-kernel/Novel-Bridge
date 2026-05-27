"""NovelBridge reading agent chat UI — fully functional."""
from __future__ import annotations
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app.config import settings

router = APIRouter(tags=["demo"])

import json as _json
_Q_DATA = {
    6: ["火焰山的火是怎么来的？","分析孙悟空的人物形象","分析孙悟空和唐僧的关系","追踪孙悟空和唐僧关系变化","猪八戒为什么会被贬下凡？","孙悟空大闹天宫的原因是什么？","观音在取经中的作用是什么？","芭蕉扇在火焰山情节中有什么作用？","唐僧取经路上最大的矛盾是什么？","孙悟空从齐天大圣到行者有什么变化？"],
    7: ["《聊斋志异》如何写狐鬼故事？","崂山道士说明了什么道理？","画皮故事的核心冲突是什么？","聊斋中的书生形象有什么特点？","聊斋如何表现人鬼关系？","聊斋故事为什么常有讽刺意味？"],
    8: ["搜神记中的神异故事有什么特点？","董永和七仙女故事讲了什么？","搜神记如何组织民间传说？","搜神记中的报应观念是什么？","搜神记和山海经的神话叙述有什么不同？","追踪一个神异事件的发展"],
    9: ["《山海经》如何组织山川地理与神话？","山海经分为哪些部分？","昆仑在山海经中有什么意义？","夸父逐日讲了什么？","精卫填海体现了什么精神？","山海经中的异兽有什么功能？","追踪昆仑相关线索","《山经》和《海经》有什么区别？"],
    10: ["宋江为什么能成为梁山核心人物？","分析林冲的人物转变","鲁智深倒拔垂杨柳体现了什么性格？","追踪宋江上梁山前后的变化","分析宋江和晁盖的关系","武松的性格有哪些矛盾？","梁山好汉为什么会聚义？","招安对梁山意味着什么？"],
}
_Q_JSON = _json.dumps(_Q_DATA, ensure_ascii=False)
_BOOKS = [[6,"西游记"],[7,"聊斋志异"],[8,"搜神记"],[9,"山海经"],[10,"水浒传"]]
_B_JSON = _json.dumps(_BOOKS, ensure_ascii=False)

BASE_DIR = Path(__file__).resolve().parent.parent


@router.get("/demo", response_class=HTMLResponse)
async def demo_page():
    html = Path(BASE_DIR / "static" / "demo.html").read_text(encoding="utf-8")
    html = html.replace("DS_DISABLED", "" if settings.deepseek_api_key.strip() else 'disabled')
    html = html.replace("Q_JSON_PLACEHOLDER", _Q_JSON)
    html = html.replace("B_JSON_PLACEHOLDER", _B_JSON)
    return HTMLResponse(html)
