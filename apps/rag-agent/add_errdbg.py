"""Add JS error handler and debug log."""
with open('app/api/demo.py', encoding='utf-8') as f:
    c = f.read()

# Add error handler at top of IIFE  
old = "(function(){"
new = "(function(){window.onerror=function(m,f,l,c,e){var d=document.body||document.documentElement;if(d){var x=document.createElement('div');x.style.cssText='position:fixed;bottom:0;left:0;right:0;z-index:99999;background:#a33;color:#fff;font:12px monospace;padding:6px 10px';x.textContent='JS ERR: '+(e&&e.message?e.message:m||'?');d.appendChild(x)}};"
c = c.replace(old, new)

with open('app/api/demo.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('OK')
