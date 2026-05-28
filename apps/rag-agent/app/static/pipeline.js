var AUTO_REFRESH = true;
var USE_MODEL = false;
var PHASE_NAMES = {'P1':'分章','P2':'梗概','P3':'提取','P4':'治理','P5':'叙事','P6':'索引','P7':'图谱','P8':'导出'};
var PHASE_ORDER = ['P1','P2','P3','P4','P5','P6','P7','P8'];
var BOOKS_DATA = [];
var _cancelFullPipeline = false;

async function loadPipeline(){
  try{
    var r=await fetch('/api/v2/pipeline/books');
    var data=await r.json();
    BOOKS_DATA = data.books || [];
    renderPipeline();
  }catch(e){
    document.getElementById('pipeline-container').innerHTML='<div class="loading">加载失败: '+e.message+'</div>';
  }
}

async function refreshStatus(){
  try{
    var r=await fetch('/api/v2/pipeline/books');
    var data=await r.json();
    var books=data.books||[];
    for(var b=0;b<books.length;b++){
      var book=books[b];
      for(var p=0;p<PHASE_ORDER.length;p++){
        var phase=PHASE_ORDER[p];
        var info=book.phases[phase]||{latest_status:'PENDING',latest_progress:0};
        var st=info.latest_status.toLowerCase();
        var pct=info.latest_progress||0;
        var btn=document.getElementById('btn-'+book.id+'-'+phase);
        var msg=document.getElementById('msg-'+book.id+'-'+phase);
        var cbtn=document.getElementById('cancel-'+book.id+'-'+phase);
        if(btn){
          if(btn.className.indexOf('running')===-1||st!=='running'){
            btn.className='phase-btn '+st;
          }
        }
        if(msg){
          // Preserve elapsed time if already shown
          if(msg.textContent.indexOf('（')===-1||st!=='running'){
            msg.textContent=st;
          }
        }
        if(cbtn){
          cbtn.style.display=(st==='running'?'':'none');
        }
        var pbar=btn?btn.parentElement.querySelector('.pfill'):null;
        if(pbar)pbar.style.width=pct+'%';
      }
    }
  }catch(e){}
}

function renderPipeline(){
  var el=document.getElementById('pipeline-container');
  var books = BOOKS_DATA;
  if(!books||books.length===0){
    el.innerHTML='<div class="loading">暂无书籍，请先上传</div>';return;
  }
  var h='';
  for(var b=0;b<books.length;b++){
    var book=books[b];
    var badge='<span class="badge '+book.status+'">'+book.status+'</span>';
    h+='<div class="card">';
      h+='<div class="card-h"><div class="card-t">';
      h+='<input type="checkbox" class="bk-cb" value="'+book.id+'" onchange="updateBatchBtn()">';
      h+=esc(book.title)+'</div> <span class="card-m">'+badge+' '+book.chapter_count+'章 '+book.chunk_count+'块';
      h+=' <label style="font-size:11px;cursor:pointer"><input type="checkbox" class="model-cb" value="'+book.id+'" checked onchange="toggleModel('+book.id+')"> 模型</label>';
      h+=' <select class="provider-sel" data-book="'+book.id+'" onchange="setProvider()" style="font-size:10px;padding:1px 2px;border:1px solid #d8ded7;border-radius:3px">';
      h+='<option value="local">9B</option><option value="deepseek">DeepSeek</option>';
      h+='</select>';
      h+='</span></div>';
    // Phase buttons
    h+='<div class="phase-grid">';
    for(var p=0;p<PHASE_ORDER.length;p++){
      var phase=PHASE_ORDER[p];
      var info=book.phases[phase]||{latest_status:'PENDING',latest_progress:0,latest_task_id:''};
      var st=info.latest_status.toLowerCase();
      var pct=info.latest_progress||0;
      h+='<div class="phase-item">';
      h+='<div style="display:flex;gap:2px">';
      h+='<button class="phase-btn '+st+'" onclick="triggerPhase('+book.id+',\''+phase+'\')" id="btn-'+book.id+'-'+phase+'" style="flex:1">'+PHASE_NAMES[phase]+'</button>';
      h+='<button class="phase-btn '+st+'" onclick="cancelTask('+book.id+',\''+phase+'\')" id="cancel-'+book.id+'-'+phase+'" title="取消" style="flex:0;padding:7px 6px;font-size:11px;display:'+(st==='running'?'':'none')+'">✕</button>';
      h+='</div>';
      h+='<div class="pbar"><div class="pfill '+(st==='failed'?'failed':'')+'" style="width:'+pct+'%"></div></div>';
      h+='<div class="pmsg" id="msg-'+book.id+'-'+phase+'">'+st+'</div>';
      h+='</div>';
    }
    h+='</div><div class="action-bar">';
    // Full pipeline button
    h+='<button class="bar-btn full" onclick="fullPipeline('+book.id+')" id="full-'+book.id+'">全流程</button>';
    // Cleanup buttons
    h+='<button class="btn-cln" onclick="cleanupBook('+book.id+',\'data\')">清数据库</button>';
    h+='<button class="btn-cln" onclick="cleanupBook('+book.id+',\'qdrant\')">清向量</button>';
    h+='<button class="btn-cln" onclick="cleanupBook('+book.id+',\'neo4j\')">清图谱</button>';
    h+='<button class="btn-cln danger" onclick="cleanupBook('+book.id+',\'all\')">清全部</button>';
    h+='</div></div>';
  }
  el.innerHTML=h;
  updateBatchBtn();
}
function toggleModel(bookId){}
function setProvider(bookId){}
function updateBatchBtn(){
  var cbs=document.querySelectorAll('.bk-cb:checked');
  document.getElementById('batchBtn').textContent='批量运行 '+(cbs.length>0?'('+cbs.length+'本)':'');
}

function cancelFullPipeline(){
  _cancelFullPipeline = true;
  var btn = document.getElementById('cancelFullBtn');
  if(btn)btn.textContent='正在取消...';
  // Also notify the backend to cancel current phase task
  var currentPhaseTask = btn ? btn.getAttribute('data-current-task') : null;
  if(currentPhaseTask){
    fetch('/api/v2/tasks/'+currentPhaseTask+'/cancel',{method:'POST'}).catch(function(){});
  }
}

async function fullPipeline(bookId){
  if(!confirm('将清空本书所有旧数据（数据库+向量+图谱），然后重新执行 P1-P8 全流程。\n原始书籍文本不受影响。确认继续？'))return;
  _cancelFullPipeline = false;
  var fullBtn=document.getElementById('full-'+bookId);
  var cancelBtn=document.getElementById('cancelFullBtn');
  fullBtn.disabled=true;fullBtn.textContent='清理中...';
  if(cancelBtn)cancelBtn.style.display='inline-block';
  // Auto-clean first — check responses
  var clean1=await fetch('/api/v2/books/'+bookId+'/cleanup',{method:'POST'});
  var clean2=await fetch('/api/v2/books/'+bookId+'/cleanup/qdrant',{method:'POST'});
  var clean3=await fetch('/api/v2/books/'+bookId+'/cleanup/neo4j',{method:'POST'});
  var r1=await clean1.json(),r2=await clean2.json(),r3=await clean3.json();
  if(r1.status!=='success'||r2.status!=='success'||r3.status!=='success'){
    alert('清理失败: '+(r1.message||r2.message||r3.message));
    fullBtn.textContent='全流程';fullBtn.disabled=false;
    if(cancelBtn)cancelBtn.style.display='none';
    _cancelFullPipeline=false;return;
  }
  fullBtn.textContent='全流程运行中...';
  // 重置所有阶段为 PENDING，避免旧状态干扰
  for(var p=0;p<PHASE_ORDER.length;p++){
    var rpBtn=document.getElementById('btn-'+bookId+'-'+PHASE_ORDER[p]);
    var rpMsg=document.getElementById('msg-'+bookId+'-'+PHASE_ORDER[p]);
    var rpCancel=document.getElementById('cancel-'+bookId+'-'+PHASE_ORDER[p]);
    if(rpBtn)rpBtn.className='phase-btn pending';
    if(rpMsg)rpMsg.textContent='排队中...';
    if(rpCancel)rpCancel.style.display='none';
  }
  // 清理后端该书的 pipeline 任务记录
  fetch('/api/v2/books/'+bookId+'/tasks',{method:'DELETE'}).catch(function(){});
  var useM = document.querySelector('.model-cb[value="'+bookId+'"]');
  var prov = document.querySelector('.provider-sel[data-book="'+bookId+'"]');
  for(var p=0;p<PHASE_ORDER.length;p++){
    // Check if user cancelled
    if(_cancelFullPipeline){
      for(var x=0;x<PHASE_ORDER.length;x++){
        var xbtn=document.getElementById('btn-'+bookId+'-'+PHASE_ORDER[x]);
        if(xbtn&&xbtn.className.indexOf('running')>=0)xbtn.className='phase-btn pending';
      }
      break;
    }
    var phase=PHASE_ORDER[p];
    var phaseBtn=document.getElementById('btn-'+bookId+'-'+phase);
    var msg=document.getElementById('msg-'+bookId+'-'+phase);
    var t0=Date.now();
    phaseBtn.className='phase-btn running';msg.textContent='排队中...';
    try{
      var r=await fetch('/api/v2/books/'+bookId+'/phase/'+phase,{method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          use_model:!!(useM&&useM.checked),
          provider:prov?prov.value:'local'
        })});
      var data=await r.json();
      if(data.status==='started'){
        msg.textContent='已排队';
        // Store current task on cancel button for cancellation
        if(cancelBtn)cancelBtn.setAttribute('data-current-task',data.task_id);
        await waitTask(data.task_id,bookId,phase);
      }
    }catch(e){msg.textContent='失败';phaseBtn.className='phase-btn failed';break;}
    var elapsed=Math.round((Date.now()-t0)/1000);
    var curMsg=msg.textContent;
    if(curMsg.indexOf('（')===-1)msg.textContent=curMsg+'（'+elapsed+'s）';
  }
  fullBtn.textContent='全流程';fullBtn.disabled=false;
  if(cancelBtn){cancelBtn.style.display='none';cancelBtn.textContent='✕ 取消全流程';cancelBtn.removeAttribute('data-current-task');}
  _cancelFullPipeline=false;
  loadPipeline();
}
async function waitTask(taskId,bookId,phase){
  var btn=document.getElementById('btn-'+bookId+'-'+phase);
  var msg=document.getElementById('msg-'+bookId+'-'+phase);
  var cancelBtn=document.getElementById('cancel-'+bookId+'-'+phase);
  if(cancelBtn)cancelBtn.setAttribute('data-task-id',taskId);
  var t0=Date.now();
  for(var i=0;i<600;i++){
    await new Promise(function(r){setTimeout(r,2000)});
    // Check if full pipeline was cancelled
    if(_cancelFullPipeline){
      // Cancel this phase task
      fetch('/api/v2/tasks/'+taskId+'/cancel',{method:'POST'}).catch(function(){});
      if(cancelBtn)cancelBtn.style.display='none';
      msg.textContent='已取消（全流程终止）';
      btn.className='phase-btn pending';
      return 'CANCELLED';
    }
    try{
      var rx=await fetch('/api/v2/tasks/'+taskId);
      var t=await rx.json();
      var st=t.status.toLowerCase();
      btn.className='phase-btn '+st;
      var elapsed=Math.round((Date.now()-t0)/1000);
      msg.textContent=(t.message||st)+'（'+elapsed+'s）';
      var pf=btn.parentElement.querySelector('.pfill');
      if(pf)pf.style.width=t.progress+'%';
      if(t.status==='SUCCESS'||t.status==='FAILED'){
        if(t.error)msg.textContent='失败: '+t.error.slice(0,60)+'（'+elapsed+'s）';
        return t.status;
      }
    }catch(e){msg.textContent='异常';return 'FAILED';}
  }
  return 'FAILED';
}
async function batchRun(){
  var cbs=document.querySelectorAll('.bk-cb:checked');
  if(cbs.length===0){alert('请先勾选要处理的书籍');return;}
  if(!confirm('批量运行 '+cbs.length+' 本书的全流程？将按顺序依次处理每本书的 P1-P8。'))return;
  document.getElementById('batchBtn').disabled=true;
  for(var i=0;i<cbs.length;i++){
    var bid=parseInt(cbs[i].value);
    document.getElementById('batchBtn').textContent='正在处理第 '+(i+1)+'/'+cbs.length+' 本...';
    await fullPipeline(bid);
  }
  document.getElementById('batchBtn').textContent='批量运行完成';document.getElementById('batchBtn').disabled=false;
  setTimeout(function(){document.getElementById('batchBtn').textContent='批量运行选中'},3000);
  loadPipeline();
}

async function triggerPhase(bookId,phase){
  var btn=document.getElementById('btn-'+bookId+'-'+phase);
  var msg=document.getElementById('msg-'+bookId+'-'+phase);
  btn.className='phase-btn running';btn.disabled=true;msg.textContent='启动中...';
  var useM = document.querySelector('.model-cb[value="'+bookId+'"]');
  var prov = document.querySelector('.provider-sel[data-book="'+bookId+'"]');
  try{
    var r=await fetch('/api/v2/books/'+bookId+'/phase/'+phase,{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        use_model:!!(useM&&useM.checked),
        provider:prov?prov.value:'local'
      })});
    var data=await r.json();
    if(data.status==='started'){
      msg.textContent='已排队';
      var cancelBtn=document.getElementById('cancel-'+bookId+'-'+phase);
      if(cancelBtn)cancelBtn.setAttribute('data-task-id',data.task_id);
      pollTask(data.task_id,bookId,phase);
    }
    else{msg.textContent='启动失败';btn.className='phase-btn failed';}
  }catch(e){msg.textContent=e.message;btn.className='phase-btn failed';}
  btn.disabled=false;
}

function pollTask(taskId,bookId,phase){
  var btn=document.getElementById('btn-'+bookId+'-'+phase);
  var msg=document.getElementById('msg-'+bookId+'-'+phase);
  // Store task_id on DOM so cancel button can find it
  var cancelBtn=document.getElementById('cancel-'+bookId+'-'+phase);
  if(cancelBtn)cancelBtn.setAttribute('data-task-id',taskId);
  var t0=Date.now();
  var i=0,timer=setInterval(async function(){
    i++;
    try{
      var r=await fetch('/api/v2/tasks/'+taskId);
      var t=await r.json();
      var st=t.status.toLowerCase();
      btn.className='phase-btn '+st;
      var elapsed=Math.round((Date.now()-t0)/1000);
      msg.textContent=(t.message||st)+'（'+elapsed+'s）';
      var pf=btn.parentElement.querySelector('.pfill');
      if(pf)pf.style.width=t.progress+'%';
      if(t.status==='SUCCESS'||t.status==='FAILED'||i>600){
        clearInterval(timer);
        if(t.error)msg.textContent='失败: '+t.error.slice(0,80)+'（'+elapsed+'s）';
      }
    }catch(e){clearInterval(timer);msg.textContent='轮询异常';}
  },2000);
}

async function cleanupBook(bookId,target){
  var label={'data':'数据库','qdrant':'向量索引','neo4j':'图谱','all':'全部数据'};
  if(!confirm('确认清理书籍 '+bookId+' 的 '+label[target]+'？不可恢复！'))return;
  if(target==='all'){
    await fetch('/api/v2/books/'+bookId+'/cleanup',{method:'POST'});
    await fetch('/api/v2/books/'+bookId+'/cleanup/qdrant',{method:'POST'});
    await fetch('/api/v2/books/'+bookId+'/cleanup/neo4j',{method:'POST'});
  } else {
    await fetch('/api/v2/books/'+bookId+'/cleanup'+(target==='data'?'':'/'+target),{method:'POST'});
  }
  loadPipeline();
}
async function uploadBook(){
  var fi=document.getElementById('book-file');
  var title=document.getElementById('book-title').value||'未命名';
  var author=document.getElementById('book-author').value||'';
  var re=document.getElementById('upload-result');
  if(!fi.files.length){re.textContent='请选择文件';return;}
  var fd=new FormData();fd.append('title',title);fd.append('author',author);
  for(var f=0;f<fi.files.length;f++)fd.append('files',fi.files[f]);
  re.textContent='上传中...';
  try{
    var r=await fetch('/api/books/upload',{method:'POST',body:fd});
    var d=await r.json();
    re.textContent='上传成功: book_id='+d.book_id+' chapters='+d.chapters;
    loadPipeline();
  }catch(e){re.textContent='上传失败: '+e.message;}
}
async function cancelTask(bookId,phase){
  var btn=document.getElementById('btn-'+bookId+'-'+phase);
  var msg=document.getElementById('msg-'+bookId+'-'+phase);
  var cancelBtn=document.getElementById('cancel-'+bookId+'-'+phase);
  // Read task_id from DOM data attribute (set by pollTask/triggerPhase)
  var taskId = cancelBtn ? cancelBtn.getAttribute('data-task-id') : null;
  if(!taskId){msg.textContent='无运行中任务';return;}
  try{
    var r=await fetch('/api/v2/tasks/'+taskId+'/cancel',{method:'POST'});
    var d=await r.json();
    if(d.status==='cancelled'){
      msg.textContent='已取消';
      btn.className='phase-btn pending';
      var cbtn=document.getElementById('cancel-'+bookId+'-'+phase);
      if(cbtn)cbtn.style.display='none';
    }
  }catch(e){msg.textContent='取消失败';}
}

function esc(s){return String(s||'').replace(/[&<>"]/g,function(m){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]||m})}
loadPipeline();
setInterval(function(){if(AUTO_REFRESH)refreshStatus();},5000);
