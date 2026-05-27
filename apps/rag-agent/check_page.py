"""Check rendered page for issues."""
import urllib.request
html = urllib.request.urlopen('http://127.0.0.1:18079/demo', timeout=5).read().decode('utf-8')

checks = ['<body>', '<script>', 'id="app"', 'id="chat"', 'id="side"', 'id="anchors"', 'renderAnchors', 'scrollToMsg', 'show_more_ev']
for c in checks:
    print(f'[{"OK" if c in html else "MISS"}] {c}')

# Check for common JS-breaking patterns
issues = []
if '\\\\' in html:
    issues.append('Double backslashes in output')
if '\\"' in html:
    # Check if they're in the right context
    pass
print(f'Page size: {len(html)} bytes')
print(f'First 200 chars of HTML body: {html[html.find("<body>"):html.find("<body>")+200]}')
