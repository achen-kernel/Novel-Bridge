"""Fix anchor navigation and evidence expand."""
with open('app/api/demo.py', encoding='utf-8') as f:
    c = f.read()

# Fix 1: Add onclick to anchor dots
old = '''title="\u8df3\u5230\u56de\u7b54 '+(i+1)+'" onclick="scrollToMsg('''
new = '''title="\u8df3\u5230\u56de\u7b54 '+(i+1)+'" onclick="scrollToMsg('''
# Actually the issue is the anchor already has onclick but it might not be working
# Let me check the current state
idx = c.find('anchor-dot')
if idx > 0:
    # Show current anchor rendering
    snippet = c[idx:idx+300]
    print(f"Current anchor code: {snippet[:200]}")

# Fix 2: Evidence expand in detail panel
old_dtl = "if(d.ev.length>3)h+="
idx_dtl = c.find(old_dtl)
if idx_dtl > 0:
    snippet = c[idx_dtl:idx_dtl+150]
    print(f"Current evidence code: {snippet}")

# Check scrollToMsg function
idx_scroll = c.find('function scrollToMsg')
if idx_scroll > 0:
    snippet = c[idx_scroll:idx_scroll+200]
    print(f"scrollToMsg: {snippet}")
