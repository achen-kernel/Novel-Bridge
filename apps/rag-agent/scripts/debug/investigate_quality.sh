# 1. 事件空 summary 统计
docker exec -i novelbridge-mysql mysql -u"${MYSQL_USER:-novel_bridge}" -p"${MYSQL_PASSWORD}" novel_bridge --default-character-set=utf8mb4 -e "
SELECT book_id, COUNT(*) as total,
       SUM(CASE WHEN summary IS NULL OR summary = '' THEN 1 ELSE 0 END) as empty_summary
FROM novel_event_fact GROUP BY book_id ORDER BY book_id;
"

echo "---"

# 2. 关系重复统计（双向重复：A→B + B→A 同类型）
docker exec -i novelbridge-mysql mysql -u"${MYSQL_USER:-novel_bridge}" -p"${MYSQL_PASSWORD}" novel_bridge --default-character-set=utf8mb4 -e "
SELECT r1.book_id, r1.relation_type,
       r1.source_entity_name as A, r1.target_entity_name as B,
       r2.source_entity_name as B_dup, r2.target_entity_name as A_dup,
       r1.id as id1, r2.id as id2
FROM novel_relation_fact r1
JOIN novel_relation_fact r2 ON r1.book_id = r2.book_id
    AND r1.relation_type = r2.relation_type
    AND r1.source_entity_name = r2.target_entity_name
    AND r1.target_entity_name = r2.source_entity_name
    AND r1.id < r2.id
WHERE r1.status = 'ACTIVE' AND r2.status = 'ACTIVE'
ORDER BY r1.book_id, r1.relation_type;
"

echo "---"

# 3. 实体名不一致统计（relation_fact 中的实体名不在 entity_profile 中）
docker exec -i novelbridge-mysql mysql -u"${MYSQL_USER:-novel_bridge}" -p"${MYSQL_PASSWORD}" novel_bridge --default-character-set=utf8mb4 -e "
SELECT book_id, COUNT(DISTINCT entity_name) as mismatched_names
FROM (
    SELECT book_id, source_entity_name as entity_name FROM novel_relation_fact WHERE status = 'ACTIVE'
    UNION
    SELECT book_id, target_entity_name FROM novel_relation_fact WHERE status = 'ACTIVE'
) names
WHERE NOT EXISTS (
    SELECT 1 FROM novel_entity_profile p
    WHERE p.book_id = names.book_id AND p.canonical_name = names.entity_name AND p.status = 'ACTIVE'
)
AND entity_name NOT IN ('未知', '无', '')
GROUP BY book_id;
"
