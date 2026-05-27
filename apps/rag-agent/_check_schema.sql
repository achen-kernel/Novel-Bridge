docker exec -i novelbridge-mysql mysql -u"${MYSQL_USER:-novel_bridge}" -p"${MYSQL_PASSWORD}" -e "DESCRIBE novel_entity;" 2>&1
echo "---"
docker exec -i novelbridge-mysql mysql -u"${MYSQL_USER:-novel_bridge}" -p"${MYSQL_PASSWORD}" -e "DESCRIBE novel_entity_alias;" 2>&1