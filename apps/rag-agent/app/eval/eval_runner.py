"""
评估运行器。
遍历所有 eval cases，调用 QA 管线评分。
"""
import json
import logging
import traceback
from typing import Optional

from app.clients.mysql_client import MysqlClient
from app.qa.qa_runner import QaRunner
from app.stores.eval_store import EvalStore

logger = logging.getLogger(__name__)


class EvalRunner:
    def __init__(self, db: MysqlClient):
        self.db = db

    async def run_all(self, book_id: int = None, category: str = None,
                      use_deepseek: bool = False) -> dict:
        """运行所有匹配的 eval cases"""
        conn = self.db.connect()
        store = EvalStore(conn)

        # 1. 获取 cases
        cases = store.find_cases(book_id=book_id, category=category)
        if not cases:
            return {'status': 'error', 'message': 'No cases found'}

        # 2. 创建 run
        run_id = store.create_run('QA_EVAL')
        logger.info(f"Eval run {run_id}: {len(cases)} cases")

        passed = 0
        failed = 0
        qa_runner = QaRunner(conn)

        for case in cases:
            try:
                result = await qa_runner.answer(
                    session_id=0,
                    book_id=case['book_id'],
                    question=case['question'],
                    use_deepseek=use_deepseek,
                )

                answer = result.get('answer', '')
                citations = result.get('citations', [])

                # 精细评分
                is_empty = not answer or '无法回答' in answer or answer.startswith('抱歉')
                has_answer = 0 if is_empty else 1
                citation_count = len(citations)
                answer_length = len(answer) if answer else 0

                # 评分维度
                scores = {
                    'has_answer': has_answer,
                    'citation_count': min(citation_count, 5),  # 最高5分
                    'answer_quality': min(answer_length // 50, 3),  # 长度分 0-3
                }
                # 综合分 (0-9)
                total = scores['has_answer'] * 3 + scores['citation_count'] + scores['answer_quality']
                scores['total'] = total

                if is_empty:
                    failed += 1
                elif citation_count == 0:
                    failed += 1  # 无引用的回答视为失败
                else:
                    passed += 1

                store.insert_result(
                    run_id=run_id,
                    case_id=case['id'],
                    question=case['question'],
                    actual_answer=answer[:1000],
                    citations=citations,
                    scores=scores,
                    error_type='' if not is_empty else 'no_answer',
                )

            except Exception as e:
                logger.error(f"Eval case {case['id']} failed: {e}")
                failed += 1
                store.insert_result(
                    run_id=run_id,
                    case_id=case['id'],
                    question=case['question'],
                    error_type=type(e).__name__,
                )

        # 3. 更新 run
        summary = {
            'total': len(cases),
            'passed': passed,
            'failed': failed,
            'pass_rate': round(passed / len(cases), 2) if cases else 0,
        }
        store.update_run(run_id, 'SUCCESS', summary)

        logger.info(f"Eval run {run_id} complete: {summary}")
        return {'run_id': run_id, **summary}
