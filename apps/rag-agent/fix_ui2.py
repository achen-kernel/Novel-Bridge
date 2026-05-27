"""Fix broken JavaScript in demo.py."""
with open('app/api/demo.py', encoding='utf-8') as f:
    c = f.read()

# Find the broken evidence expand section
# The current broken code uses \'.de.hidden\' with backslash escapes
# Fix: remove all backslash escaping before single quotes in onclick
old = """if(d.ev.length>3){var ei=d.ev.length;h+='<button class=\\"show-all-btn\\" onclick=\\"var p=this.parentNode;p.querySelectorAll(\\'.de.hidden\\').forEach(function(e){e.style.display=\\'block\\'});this.style.display=\\'none\\'\\">展开全部 '+(ei-3)+' 条证据</button>';d.ev.slice(3).forEach(function(e,i){h+='<div class=\\"de hidden\\" style=\\"display:none\\"><b>E'+(i+4)+'</b> '+esc((e.excerpt||'').slice(0,120))+'</div>'})}"""
new = """if(d.ev.length>3){var ei=d.ev.length;h+='<button class=\\"show-all-btn\\" onclick=\\"show_more_ev(this,'+ei+')\\">展开全部 '+(ei-3)+' 条证据</button>'}"""
c = c.replace(old, new)

# Add the show_more_ev function before _dtl
old2 = "window._dtl=function(idx)"
new2 = """window.show_more_ev=function(btn,total){var p=btn.parentNode;var shown=p.querySelectorAll('.de:not([style*=\\"display:none\\"])').length;for(var i=shown;i<total;i++){var el=p.querySelector('.de.hidden-'+i);if(el)el.style.display='block'}btn.style.display='none'};
window._dtl=function(idx)"""
c = c.replace(old2, new2)

# Also fix the hidden class in evidence items
old3 = """d.ev.slice(3).forEach(function(e,i){h+='<div class="de hidden" style="display:none"><b>E'+(i+4)+'</b> '+esc((e.excerpt||'').slice(0,120))+'</div>'})"""
new3 = """d.ev.slice(3).forEach(function(e,i){h+='<div class="de hidden-'+i+'" style="display:none"><b>E'+(i+4)+'</b> '+esc((e.excerpt||'').slice(0,120))+'</div>'})"""
c = c.replace(old3, new3)

with open('app/api/demo.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('OK')
