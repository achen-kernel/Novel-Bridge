docker exec -i novelbridge-mysql mysql -u"${MYSQL_USER:-novel_bridge}" -p"${MYSQL_PASSWORD}" novel_bridge --default-character-set=utf8mb4 -e "
SELECT c.id, c.book_id, c.question, c.difficulty, r.error_type
FROM novel_eval_result r
JOIN novel_eval_case c ON r.case_id = c.id
WHERE r.run_id = 4 AND r.error_type != ''
ORDER BY c.book_id, c.id;
"