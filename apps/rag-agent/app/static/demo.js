var NB_PROJ_ID = 1;
var NB_SESS_ID = null;

(function(){window.onerror=function(m,f,l,c,e){var d=document.body||document.documentElement;if(d){var x=document.createElement('div');x.style.cssText='position:fixed;bottom:0;left:0;right:0;z-index:99999;background:#a33;color:#fff;font:12px monospace;padding:6px 10px';x.textContent='JS ERR: '+(e&&e.message?e.message:m||'?');d.appendChild(x)}};
var sid=Math.floor(Math.random()*900000)+100000;
var bid=6,msgs=[],sending=false;
var $=function(id){return document.getElementById(id)};
var esc=function(s){return String(s||'').replace(/[&<>]/g,function(m){return {'&':'&amp;','<':'&lt;','>':'&gt;'}[m]})};

function renderSide(){
  var el=$('bklist');el.innerHTML='';
  NB_B.forEach(function(b){
    var btn=document.createElement('button');
    btn.className='bk'+(b[0]===bid?' sel':'');btn.textContent=b[1];
    btn.onclick=function(){bid=b[0];renderSide()};el.appendChild(btn);
  });
  var ql=$('qlist');ql.innerHTML='';
  (NB_Q[bid]||[]).forEach(function(q){
    var btn=document.createElement('button');btn.className='q';btn.textContent=q;
    btn.onclick=function(){$('qi').value=q;$('qi').focus()};ql.appendChild(btn);
  });
}

function addMsg(r,c,m,d){msgs.push({role:r,content:c,mode:m,detail:d});renderChat()}
function renderAnchors(){
  var el=$('anchors');if(!el)return;
  var h='',i;
  for(i=0;i<msgs.length;i++){
    if(msgs[i].role==='a'){
      var active=i===msgs.length-1?' active':'';
      h+='<button class="anchor-dot'+active+'" title="跳到回答 '+(i+1)+'" onclick="scrollToMsg('+i+')"></button>';
    }
  }
  el.innerHTML=h;
}
window.scrollToMsg=function(idx){
  var el=$('msgs');
  var items=el.querySelectorAll('.msg');
  var target=items[idx];
  if(target)target.scrollIntoView({behavior:'smooth',block:'center'});
}

function renderChat(){
  var el=$('msgs'),h='',i;
  for(i=0;i<msgs.length;i++){
    var m=msgs[i];
    if(m.role==='u'){h+='<div class="msg u"><div class="b">'+esc(m.content)+'</div></div>';continue;}
    var mc=m.mode?'<div class="mc">'+esc(m.mode)+'</div>':'';
    var dt=m.detail?' <button class="dt" onclick="window._dtl('+i+')">详情</button>':'';
    h+='<div class="msg a"><div class="b">'+mc+esc(m.content).replace(/\\n/g,'<br>').replace(/\(基于模型知识\)/g,'<strong>(基于模型知识)</strong>')+dt+'</div></div>';
  }
  el.innerHTML=h||'<div style="text-align:center;color:var(--muted);padding:60px 0;font-size:14px">选择书籍并输入问题开始问答</div>';
  el.scrollTop=el.scrollHeight;
  // Render right-side anchor dots
  renderAnchors();
}

async function plan(q){
  var r=await fetch('/api/reader-agent/plan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({book_id:bid,question:q,preferred_mode:'auto',provider:$('prov').value,session_id:sid,model_mode:'deterministic'})});
  return r.ok?r.json():null;
}
async function run(p){
  var r=await fetch('/api/reader-agent/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});
  if(!r.ok)throw new Error((await r.text()).slice(0,200));return r.json();
}

window.show_more_ev=function(btn,total){var p=btn.parentNode;for(var i=0;i<total;i++){var el=p.children[i+1];if(el&&el.style.display==='none')el.style.display='block'}btn.style.display='none'};
window._dtl=function(idx){
  var m=msgs[idx];if(!m||!m.detail)return;
  var d=m.detail,el=$('dtl'),c=$('dtlc');
  var h='<div class="dr"><span class="l">模式</span><span class="v">'+esc(d.mode||'')+'</span></div>';
  if(d.tn)h+='<div class="dr"><span class="l">目标</span><span class="v">'+esc(d.tn)+'</span></div>';
  if(d.cf)h+='<div class="dr"><span class="l">置信度</span><span class="v">'+Math.round(d.cf*100)+'%</span></div>';
  if(d.rid)h+='<div class="dr"><span class="l">Run</span><span class="v"><a href="/agent-runs/'+d.rid+'" target="_blank">#'+d.rid+'</a></span></div>';
  if(d.ev&&d.ev.length){
    h+='<h3 class="s">证据</h3>';
    d.ev.slice(0,3).forEach(function(e,i){h+='<div class="de"><b>E'+(i+1)+'</b> '+esc((e.excerpt||'').slice(0,120))+'</div>'});
    if(d.ev.length>3){var ei=d.ev.length;h+='<button class="show-all-btn" onclick="show_more_ev(this,'+ei+')">展开全部 '+(ei-3)+' 条证据</button>'}
  }
  c.innerHTML=h;el.classList.add('o');
};
$('dtl').onclick=function(e){if(e.target===this)this.classList.remove('o')};

$('fm').onsubmit=async function(e){
  e.preventDefault();
  var q=$('qi').value.trim();if(!q||sending)return;
  sending=true;$('sb').disabled=true;
  addMsg('u',q);$('qi').value='';
  var li=document.createElement('div');li.className='msg a l';li.innerHTML='<div class="b">正在思考...</div>';
  $('msgs').appendChild(li);$('msgs').scrollTop=$('msgs').scrollHeight;
  try{
    var p=await plan(q);
    if(!p)p={mode:'answer',optimized_question:q,confidence:.5,target_name:'',target_type:'',tool_sequence:null,request_patch:{}};
    var pp=p.request_patch||{},tid=p.tool_sequence?JSON.parse(JSON.stringify(p.tool_sequence)):null;
    var body={mode:pp.mode||p.mode||'answer',book_id:bid,question:pp.question||p.optimized_question||q,
      target_name:pp.target_name||p.target_name||'',target_type:pp.target_type||p.target_type||'',
      analysis_type:pp.analysis_type||p.analysis_type||null,
      trace_target_type:pp.trace_target_type||p.trace_target_type||null,
      session_id:sid,options:{provider:$('prov').value,require_citations:true},tool_sequence:tid};
    var data=await run(body);
    li.remove();
    var detail={mode:data.mode||p.mode,cf:p.confidence,tn:p.target_name,rid:data.run_id,ev:data.citations||data.evidence||[]};
    addMsg('a',data.answer||'(无回答)',data.mode||p.mode,data.answer?detail:null);
  }catch(e){li.innerHTML='<div class="b"><span style="color:var(--danger)">'+esc(e.message||e)+'</span></div>'}
  sending=false;$('sb').disabled=false;
};

$('clrbtn').onclick=function(){msgs=[];renderChat();$('dtl').classList.remove('o')};
$('newbtn').onclick=function(){sid=Math.floor(Math.random()*900000)+100000;msgs=[];renderChat();$('dtl').classList.remove('o')};

var hnames=[['mysql','mysql'],['qdrant','qdrant'],['neo4j','neo4j'],['llm','llm'],['emb','embedding']];
async function refreshHealth(){
  for(var i=0;i<hnames.length;i++){
    var el=$('h-'+hnames[i][0]),d=el?el.querySelector('.d'):null;if(!d)continue;
    d.className='d';
    try{var r=await fetch('/health/'+hnames[i][1]);var j=await r.json();d.className='d '+(j.status==='ok'?'g':'r')}
    catch(e){d.className='d r'}
  }
}
$('hbtn').onclick=refreshHealth;

// New project button
$('newProjBtn').onclick=async function(){
  try{
    var r=await fetch('/api/reader-agent/projects',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:'新项目'})});
    var d=await r.json();
    NB_PROJ_ID=d.project.id;NB_SESS_ID=d.session.id;renderProjects();
  }catch(e){}
};

// ==============================
// Project + Session management
// ==============================
async function loadProjects(){
  if(NB_SESS_ID===null){
    // First load: create default session
    try{
      var r=await fetch('/api/reader-agent/projects');var data=await r.json();
      if(data.length&&data[0].sessions.length){NB_PROJ_ID=data[0].id;NB_SESS_ID=data[0].sessions[0].id}
      else{
        var r2=await fetch('/api/reader-agent/projects/1/sessions',{method:'POST'});
        var s=await r2.json();NB_PROJ_ID=1;NB_SESS_ID=s.id;
      }
    }catch(e){}
  }
  renderProjects();
}
async function renderProjects(){
  try{
    var r=await fetch('/api/reader-agent/projects');var data=await r.json();
    var el=$('projlist');el.innerHTML='';
    data.forEach(function(p){
      var pdiv=document.createElement('div');pdiv.className='proj';
      var ph=document.createElement('div');ph.className='proj-h'+(p.id===NB_PROJ_ID?' sel':'');
      ph.innerHTML='<span>'+esc(p.name)+'</span><span style="font-size:10px;color:var(--muted)">'+p.sessions.length+'</span>';
      ph.onclick=function(){NB_PROJ_ID=p.id;renderProjects()};
      var pdel=document.createElement('span');pdel.textContent='×';pdel.className='sess-del';
      pdel.onclick=function(ev){ev.stopPropagation();if(confirm('删除项目「'+p.name+'」及所有会话？')){fetch('/api/reader-agent/projects/'+p.id,{method:'DELETE'}).then(function(r){return r.json()}).then(function(){if(NB_PROJ_ID===p.id){NB_PROJ_ID=null;NB_SESS_ID=null};renderProjects()})}};
      ph.appendChild(pdel);
      pdiv.appendChild(ph);
      p.sessions.forEach(function(s){
        var si=document.createElement('div');si.className='sess'+(s.id===NB_SESS_ID?' sel':'');
        var sp=document.createElement('span');sp.textContent=s.name;
        var del=document.createElement('span');del.textContent='×';del.className='sess-del';
        del.onclick=function(ev){ev.stopPropagation();if(confirm('删除会话「'+s.name+'」？')){fetch('/api/reader-agent/sessions/'+s.id,{method:'DELETE'}).then(function(r){return r.json()}).then(function(){if(NB_SESS_ID===s.id){NB_SESS_ID=null};renderProjects()})}};
        si.appendChild(sp);si.appendChild(del);
        si.onclick=function(){NB_SESS_ID=s.id;NB_PROJ_ID=p.id;renderProjects();renderChat()};
        si.ondblclick=function(){var n=prompt('重命名:',s.name);if(n&&n.length){fetch('/api/reader-agent/sessions/'+s.id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n})}).then(function(){renderProjects()})}};
        pdiv.appendChild(si);
      });
      var addBtn=document.createElement('div');addBtn.className='add-sess';addBtn.textContent='+ 新会话';
      addBtn.onclick=function(){fetch('/api/reader-agent/projects/'+p.id+'/sessions',{method:'POST'}).then(function(r){return r.json()}).then(function(s){NB_SESS_ID=s.id;renderProjects()})};
      pdiv.appendChild(addBtn);
      el.appendChild(pdiv);
    });
  }catch(e){}
}

// Intent check: casual chat / greeting → answer directly
async function checkIntent(q){
  try{
    var resp=await fetch('/api/reader-agent/plan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({book_id:NB.selectedBookId||6,question:q,preferred_mode:'auto',provider:'local',session_id:NB_SESS_ID||0,model_mode:'deterministic'})});
    if(!resp.ok)return null;
    return resp.json();
  }catch(e){return null}
}

// Intent check: let backend model decide (no hardcoded patterns)
// The original submit handler is preserved and always called.
// Backend intent_detector will intercept non-book-qa queries.

renderSide();renderChat();refreshHealth();loadProjects();
})();
