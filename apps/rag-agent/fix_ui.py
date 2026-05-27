"""Fix: anchor navigation + evidence expand."""
with open('app/api/demo.py', encoding='utf-8') as f:
    c = f.read()

# Fix 1: Export scrollToMsg to window so onclick handlers can find it
old1 = "function scrollToMsg(idx){"
new1 = "window.scrollToMsg=function(idx){"
c = c.replace(old1, new1)

# Fix 2: Evidence "还有 n 条" → expandable button
old2 = "if(d.ev.length>3)h+='<div style=\"color:var(--muted);font-size:11px\">还有 '+(d.ev.length-3)+' 条</div>';"
new2 = "if(d.ev.length>3){var ei=d.ev.length;h+='<button class=\"show-all-btn\" onclick=\"var p=this.parentNode;p.querySelectorAll(\\'.de.hidden\\').forEach(function(e){e.style.display=\\'block\\'});this.style.display=\\'none\\'\">展开全部 '+(ei-3)+' 条证据</button>';d.ev.slice(3).forEach(function(e,i){h+='<div class=\"de hidden\" style=\"display:none\"><b>E'+(i+4)+'</b> '+esc((e.excerpt||'').slice(0,120))+'</div>'})}"
c = c.replace(old2, new2)

with open('app/api/demo.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('OK')
