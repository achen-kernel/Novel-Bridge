#!/usr/bin/env bash
# Index Book 7 on remote
BASE="http://127.0.0.1:18081"
echo "=== Indexing Book 7 ==="
curl -s -X POST "${BASE}/api/books/7/index" \
  -H "Content-Type: application/json" \
  -d '{"reindex": true}'
echo ""
echo "=== Done ==="
