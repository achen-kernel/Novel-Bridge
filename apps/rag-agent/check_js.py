"""Check JS syntax."""
import urllib.request
html = urllib.request.urlopen('http://127.0.0.1:18079/demo', timeout=5).read().decode('utf-8')

# Extract the IIFE
start = html.find('(function(){')
end = html.find('})();', start) + 5
js = html[start:end]

# Check brace balance
opens = js.count('{')
closes = js.count('}')
print(f'Braces: {opens} open, {closes} close, diff={opens-closes}')

# Check paren balance
ropens = js.count('(')
rcloses = js.count(')')
print(f'Parens: {ropens} open, {rcloses} close, diff={ropens-rcloses}')

# Check for unescaped quotes in wrong places
# Find lines with potential issues
lines = js.split('\n')
for i, line in enumerate(lines):
    # Check for backslash-quote issues
    if "\\'" in line and 'onclick' in line:
        print(f'Line {i}: BACKSLASH QUOTE in onclick: {line[:120]}')
    # Check for lines that look like they have encoding issues
    if '\\\\' in line:
        print(f'Line {i}: DOUBLE BACKSLASH: {line[:100]}')
