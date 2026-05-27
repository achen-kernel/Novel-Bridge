"""Check rendered JS for issues."""
with open('D:\\Novel-Bridge\\temp_page.html', encoding='utf-8') as f:
    html = f.read()

start = html.find('(function(){')
end = html.find('})();', start) + 5
js = html[start:end]

print('JS length:', len(js))
print('Has window.onerror:', 'window.onerror' in js)
print('First 150 chars:', js[:150])

# Check for template literals that Python f-strings might have corrupted
idx = js.find('${')
if idx >= 0:
    print(f'WARNING: template literal at char {idx}: {js[idx:idx+50]}')

# Check for Python f-string artifacts
idx2 = js.find('{deepseek_configured}')
if idx2 >= 0:
    print(f'Python template leftover: {js[idx2:idx2+50]}')
