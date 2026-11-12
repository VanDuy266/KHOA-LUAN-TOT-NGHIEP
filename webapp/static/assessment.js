/* A complete assessment is kept in the browser, never in shared server storage. */
"use strict";
const assessmentKey = 'vincent-assessments-v1';
const assessmentFields = [
  ['time', 'Thời gian', [{value:'s',label:'Giây'},{value:'ms',label:'Mili giây'},{value:'min',label:'Phút'}]],
  ['terminal_voltage', 'Điện áp', ['V','mV']],
  ['terminal_current', 'Dòng điện', ['A','mA']],
  ['temperature', 'Nhiệt độ', ['C','K']]
];
function assessmentStorage(persistent=false){try{return persistent?window.localStorage:window.sessionStorage;}catch(e){return null;}}
function assessmentRecords(storage=assessmentStorage()){
  try {const rows=JSON.parse(storage.getItem(assessmentKey)||'[]');return Array.isArray(rows)?rows.filter(x=>x?.record?.id&&x?.record?.profile).slice(0,100):[];} catch(e){return [];}
}
function assessmentDownload(content,type,filename){
  const url=URL.createObjectURL(new Blob([content],{type})),a=document.createElement('a');
  a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1500);
}
function assessmentSave(item,persistent){
  // Remove a former copy so moving a record to session-only storage is effective.
  const target=assessmentStorage(persistent),other=assessmentStorage(!persistent);
  if(!target)throw new Error('Trình duyệt không cho lưu lịch sử.');
  const saved=[item,...assessmentRecords(target).filter(x=>x.record.id!==item.record.id)].slice(0,100);
  target.setItem(assessmentKey,JSON.stringify(saved));
  if(other)other.setItem(assessmentKey,JSON.stringify(assessmentRecords(other).filter(x=>x.record.id!==item.record.id)));
}
function assessmentSteps(step){return `<ol class="assessment-steps" aria-label="Tiến trình đánh giá">${['Hồ sơ & bài toán','Dữ liệu & đơn vị','Kiểm tra phạm vi','Kết quả & báo cáo'].map((label,i)=>`<li class="${i+1===step?'current':i+1<step?'done':''}" ${i+1===step?'aria-current="step"':''}><span>${i+1}</span>${label}</li>`).join('')}</ol>`;}
function assessmentDrawSignals(item,root){
  const r=item.record;if(!r.signals?.length)return;
  const x=r.task==='bms'?'time_s':'time';
  const channels=r.task==='bms'?[['pack_voltage','Điện áp bộ pin (V)'],['charge_current','Dòng sạc (A)'],['max_temperature','Nhiệt độ cao nhất (°C)']]:[['terminal_voltage','Điện áp (V)'],['terminal_current','Dòng điện (A)'],['temperature','Nhiệt độ (°C)']];
  const target=$('[data-assessment-signals]',root);if(!target)return;
  target.innerHTML=channels.map(([key,label])=>`<h3>${esc(label)}</h3><div class="plot" id="assessment-plot-${key}"></div>`).join('');
  for(const [key,label] of channels)chart('assessment-plot-'+key,[series(label,r.signals,x,key)],'Thời gian (s)',label);
}
function assessmentResult(item){
  const r=item.record,v=r.results[0],isSignals=r.task==='signals';
  const metrics=isSignals?[
    {label:'Thời lượng đoạn đo',value:v.duration_seconds,unit:'s'},
    {label:'Điện áp thấp nhất',value:v.voltage_min,unit:'V'},
    {label:'Điện áp cao nhất',value:v.voltage_max,unit:'V'}
  ]:[
    {label:r.task==='bms'?'SOH vận hành ước tính':r.task==='capacity'?'SOH từ dung lượng đo':'SOH dự đoán',value:v.soh_pct,unit:'%',digits:2},
    {label:'Mức chai dung lượng',value:v.loss_pct,unit:'%',digits:2,detail:v.soh_pct>100?'Không tính mức chai âm':''},
    {label:r.task==='capacity'?'Dung lượng xả đo được':'Dung lượng còn lại ước tính',value:v.capacity_ah,unit:'Ah',digits:3}
  ];
  return `<div class="assessment-card"><span class="tag">${esc(r.sample?'MẪU MINH HỌA':'HỒ SƠ ĐÁNH GIÁ')}</span><h2>${esc(r.profile.battery_id)}</h2><p>${esc(r.title)} · ${esc(r.profile.measured_at||'Ngày đo mẫu không khai báo')}</p>${kpis(metrics)}<p><strong>${esc(r.label_source)}</strong></p></div>`+
    r.warnings.map(w=>notice(w,'warning')).join('')+
    (r.signals?.length?'<details class="panel"><summary>Biểu đồ tín hiệu của đoạn đã phân tích</summary><p>Hiển thị tối đa 200 điểm; kiểm tra dữ liệu dùng toàn bộ đoạn đã chọn.</p><div data-assessment-signals></div></details>':'')+
    panel('Kết quả này dùng để làm gì?','Đọc kết quả cùng chất lượng đầu vào và phạm vi mô hình.',`<p>${esc(isSignals?'Đoạn dữ liệu này chỉ được tổng hợp tín hiệu. Điện lượng của một đoạn sạc/xả không phải dung lượng đầy và không xác định SOH.':r.task==='capacity'?'Tỷ lệ dung lượng hiện tại so với mốc tham chiếu do bạn cung cấp; chất lượng phụ thuộc phép đo.':'Hỗ trợ đối chiếu dung lượng trong cấu hình đã khai báo. Kết quả từ mô hình chưa thay thế phép đo dung lượng độc lập.')}</p><p>${esc(r.scope.message)}</p><p>${esc(r.uncertainty)}</p><p>${esc(r.limitation)}</p><ol>${r.next_steps.map(x=>`<li>${esc(x)}</li>`).join('')}</ol>`)+
    panel('Chất lượng đầu vào','Đã kiểm tra lại trên máy chủ trước khi chạy mô hình.',table(r.checks,'kiem_tra_danh_gia'))+
    (r.explanation?`<details class="panel"><summary>Vì sao mô hình đưa ra kết quả này?</summary>${explanationEvidence(r.explanation.evidence,r.explanation.baseline)}<p>Giải thích đóng góp của mô hình, không chứng minh nguyên nhân hư hỏng vật lý.</p></details>`:'')+
    (r.validation?.length?`<details class="panel"><summary>Bằng chứng kiểm thử mô hình</summary>${table(r.validation,'kiem_thu_mo_hinh')}<p>MAE là sai số trung bình trên dữ liệu kiểm thử giữ riêng pin/xe; không phải độ chính xác của hồ sơ này.</p></details>`:'')+
    (isSignals?panel('Tín hiệu đo và điện lượng đoạn quan sát','Không suy ra SOH từ đoạn đo.',table([v],'tin_hieu_do')):'')+
    `<details class="panel"><summary>Truy xuất hồ sơ và bảo mật</summary>${table([{'Mã hồ sơ':r.id,'Ngày đo':r.profile.measured_at,'Điều kiện đo':r.profile.conditions,'File':r.source_name||'Giá trị nhập tay','SHA256 file':r.source_sha256,'Mô hình':r.model,'SHA256 mô hình':r.model_sha256||'Không dùng mô hình','Phiên bản ứng dụng':r.app_version}],'truy_xuat_ho_so')}<p>Ứng dụng không lưu file và hồ sơ trên máy chủ, không tự đưa file vào tập huấn luyện. Nhật ký vận hành chỉ phục vụ xử lý yêu cầu. Lịch sử mặc định ở tab này; chỉ lưu lâu dài trên thiết bị nếu bạn chọn.</p></details>`;
}
function assessmentBindExports(item,root){
  assessmentDrawSignals(item,root);
  $('[data-assessment-html]',root).onclick=()=>assessmentDownload(item.report_html,'text/html;charset=utf-8','bao_cao_pin_'+item.record.id+'.html');
  $('[data-assessment-json]',root).onclick=()=>assessmentDownload(JSON.stringify(item.record,null,2),'application/json','ho_so_pin_'+item.record.id+'.json');
  $('[data-assessment-csv]',root).onclick=()=>csvDownload(item.record.results.map(v=>({battery_id:item.record.profile.battery_id,measured_at:item.record.profile.measured_at,task:item.record.task,model:item.record.model,...v})) ,['battery_id','measured_at','task','model','soh_pct','loss_pct','capacity_ah','outside_count'],'ket_qua_danh_gia');
}
function assessmentExportButtons(){return '<div class="actions"><button class="button primary" type="button" data-assessment-html>Tải báo cáo · In / Lưu PDF</button><button class="button" type="button" data-assessment-csv>Tải kết quả CSV</button><button class="button" type="button" data-assessment-json>Tải hồ sơ JSON</button></div><p class="sub">Mở báo cáo HTML vừa tải, chọn “In / Lưu PDF”. Báo cáo có thể đọc độc lập khi không có mạng.</p>';}
async function assessment(token){
  const today=new Date(Date.now()-new Date().getTimezoneOffset()*60000).toISOString().slice(0,10);
  const taskOptions=[['signals','Tôi có tín hiệu đo','Phân tích dữ liệu pin khác hoặc chưa rõ cấu hình; chưa dự đoán SOH.'],['sdu','Tôi có dữ liệu SDU','Đầu xả cell NMC 2,4 Ah, dùng mô hình SOH đã học.'],['bms','Tôi có BMS BAIC EU500','Đầu sạc bộ pin NMC 145 Ah, nhãn SOH suy ra từ dòng/SOC.'],['capacity','Tôi có dung lượng đo đầy đủ','Tính tỷ lệ dung lượng hiện tại so với tham chiếu cùng điều kiện.']];
  if(!put(header('Đánh giá pin theo hồ sơ','Dành cho người có dữ liệu đo: chọn đúng bài toán, kiểm tra đầu vào rồi lập báo cáo.')+'<div id="assessment-progress">'+assessmentSteps(1)+'</div>'+`<form id="assessment-form" novalidate>${panel('1. Bạn muốn đánh giá điều gì?','Chọn theo dữ liệu đang có. Chưa rõ cấu hình: bắt đầu bằng phân tích tín hiệu.',`<div class="assessment-task-grid">${taskOptions.map(([value,title,desc],i)=>`<label class="assessment-task"><input type="radio" name="task" value="${value}" ${i===0?'checked':''}><strong>${title}</strong><span>${desc}</span></label>`).join('')}</div><div class="actions"><button class="button" type="button" data-assessment-sample="sdu">Thử mẫu SDU</button><button class="button" type="button" data-assessment-sample="bms">Thử mẫu BAIC</button><a class="button" href="#health">Theo dõi xu hướng</a><a class="button" href="#fault">Phân tích điện áp có nhãn lỗi</a></div><p id="assessment-sample-status" role="status"></p>`)}${panel('Hồ sơ pin và phép đo','Dùng mã pin nhất quán giữa các lần đo. Ghi điều kiện để biết lần nào có thể so sánh.',`<div class="controls"><div class="field"><label for="assessment-battery">Mã pin / xe</label><input id="assessment-battery" maxlength="100" placeholder="Ví dụ: PIN-001" required></div><div class="field"><label for="assessment-date">Ngày đo</label><input id="assessment-date" type="date" value="${today}" required></div></div><div class="controls">${select('assessment-origin','Nguồn / cấu hình',[{value:'other',label:'Khác / chưa rõ'},{value:'SDU',label:'Nguồn SDU'},{value:'BAIC EU500',label:'BAIC EU500'}],'other')}${select('assessment-chemistry','Hóa học pin',['unknown','NMC','LFP','LCO','NCA','LTO','other'].map(value=>({value,label:{unknown:'Chưa rõ',other:'Khác'}[value]||value})),'unknown')}${select('assessment-level','Cấp đo',[{value:'unknown',label:'Chưa rõ'},{value:'cell',label:'Một cell'},{value:'pack',label:'Cả bộ pin'}],'unknown')}${select('assessment-mode','Chế độ',[{value:'unknown',label:'Chưa rõ'},{value:'charge',label:'Sạc'},{value:'discharge',label:'Xả'},{value:'mixed',label:'Sạc và xả'}],'unknown')}<div class="field"><label for="assessment-nominal">Dung lượng định mức (Ah)</label><input id="assessment-nominal" type="number" min="0.000001" step="any"></div></div><div class="field"><label for="assessment-conditions">Điều kiện đo / thiết bị / quy trình</label><input id="assessment-conditions" maxlength="300" placeholder="Ví dụ: 25°C, dòng xả 2 A, thiết bị đo …"></div><label id="assessment-confirm-wrap" class="check" hidden><input id="assessment-confirm" type="checkbox">Tôi xác nhận đúng nguồn, cấu hình và cửa sổ 120 giây đầu sạc/xả của mô hình đã chọn.</label>`)}<div id="assessment-upload-panel">${panel('2. Chuẩn bị dữ liệu đo','CSV / CSV.GZ tối đa 512 MiB; JSON dạng bảng tối đa 20 MiB. Chọn một pin và một chu kỳ, tối đa 100.000 dòng.',`<div class="field"><label for="assessment-file">File dữ liệu</label><input id="assessment-file" type="file" accept=".csv,.csv.gz,.gz,.json"></div><div class="actions"><a class="button" id="assessment-sample-link" href="/api/download/sample?kind=sdu">Tải cấu trúc CSV mẫu</a><a class="button" href="#mapping">Bộ tiếp nhận dữ liệu riêng</a></div><details><summary>Lấy dữ liệu ở đâu?</summary><p>Xuất bảng đo từ máy thử pin hoặc phần mềm BMS. Với SDU cần thời gian (s), điện áp cell (V), dòng điện (A, xả âm), nhiệt độ (°C), chu kỳ và giai đoạn. Với BAIC cần time_s, soc, pack_voltage, charge_current (sạc âm), max/min_cell_voltage và max/min_temperature. Không thể suy SOH chỉ từ ảnh phần trăm pin hoặc SOC.</p><p>Chỉ đo bằng thiết bị và quy trình phù hợp; ứng dụng không điều khiển thiết bị đo. Không lấy điện lượng của một đoạn sạc làm dung lượng đầy.</p></details><div id="assessment-preview" aria-live="polite"></div><div id="assessment-mapping"></div>`)} </div><div id="assessment-capacity-panel" hidden>${panel('2. Hai phép đo dung lượng','Giá trị lấy từ phép xả dung lượng đầy đủ, không phải lượng điện nạp của một phiên sạc dở dang.',`<div class="controls"><div class="field"><label for="assessment-reference">Dung lượng tham chiếu (Ah)</label><input id="assessment-reference" type="number" step="any" min="0.000001"></div><div class="field"><label for="assessment-measured">Dung lượng hiện tại (Ah)</label><input id="assessment-measured" type="number" step="any" min="0.000001"></div></div><label class="check"><input id="assessment-comparable" type="checkbox">Cùng cell/bộ pin, cùng đơn vị, nhiệt độ, chế độ xả và giới hạn điện áp đối chiếu.</label>`)} </div><div id="assessment-model-panel">${panel('Mô hình và cửa sổ đo','Random Forest là mặc định ổn định của sản phẩm. Ridge–RF có MAE SDU gần tương đương; mô hình tốt nhất phụ thuộc nguồn và tiêu chí.',`<div class="controls">${select('assessment-model','Mô hình',['Random Forest','Ridge-RF residual','Ridge','LightGBM','CatBoost','XGBoost'],'Random Forest')}<div id="assessment-cycle-wrap" class="field"><label for="assessment-cycle">Chu kỳ nếu file chưa có</label><input id="assessment-cycle" type="number" value="1" min="1" step="1"></div><div id="assessment-phase-wrap">${select('assessment-phase','Giai đoạn nếu file chưa có',[{value:'0',label:'Sử dụng ban đầu'},{value:'1',label:'Tái sử dụng'}],'0')}</div></div><p>Sáu mô hình bảng hỗ trợ dự đoán SDU. GRU dùng chuỗi tín hiệu riêng và hiện chỉ phục vụ thực nghiệm, chưa mở dự đoán trực tiếp trên Render.</p>`)} </div><div class="actions"><button class="button primary" id="assessment-check" type="submit">3. Kiểm tra dữ liệu & phạm vi</button><button class="button" id="assessment-run" type="button" disabled>4. Phân tích & lập báo cáo</button></div></form><div id="assessment-preflight" aria-live="polite"></div><div id="assessment-result" aria-live="polite"></div>`,token))return;
  const form=$('#assessment-form');let sample=false,checked=null,revision=0,previewRevision=0;
  const currentTask=()=>$('input[name=task]:checked',form).value;
  const invalidate=()=>{revision++;checked=null;$('#assessment-run').disabled=true;$('#assessment-preflight').innerHTML='';$('#assessment-result').innerHTML='';$('#assessment-progress').innerHTML=assessmentSteps(1);};
  function taskUI(){
    const task=currentTask(),isModel=['sdu','bms'].includes(task),isBms=task==='bms';
    $('#assessment-upload-panel').hidden=task==='capacity';$('#assessment-capacity-panel').hidden=task!=='capacity';$('#assessment-model-panel').hidden=!isModel;$('#assessment-confirm-wrap').hidden=!isModel;
    $('#assessment-cycle-wrap').hidden=isBms;$('#assessment-phase-wrap').hidden=isBms;
    $('#assessment-model').innerHTML=(isBms?['Random Forest','Ridge-RF residual']:['Random Forest','Ridge-RF residual','Ridge','LightGBM','CatBoost','XGBoost']).map(v=>`<option>${esc(v)}</option>`).join('');
    $('#assessment-sample-link').href='/api/download/sample?kind='+(isBms?'bms':'sdu');
    $('#assessment-mapping').hidden=isBms;
  }
  function defaults(task){if(task==='sdu'||task==='bms'){
    const bms=task==='bms';$('#assessment-origin').value=bms?'BAIC EU500':'SDU';$('#assessment-chemistry').value='NMC';$('#assessment-level').value=bms?'pack':'cell';$('#assessment-mode').value=bms?'charge':'discharge';$('#assessment-nominal').value=bms?'145':'2.4';
  }}
  form.addEventListener('input',invalidate);
  form.addEventListener('change',e=>{invalidate();if(e.target.name==='task'){sample=false;$('#assessment-sample-status').textContent='';$('#assessment-confirm').checked=false;defaults(currentTask());taskUI();if($('#assessment-file').files.length)preview();}});
  async function preview(){
    const requestRevision=++previewRevision,file=$('#assessment-file').files[0],out=$('#assessment-preview');$('#assessment-mapping').innerHTML='';if(!file)return;
    sample=false;$('#assessment-sample-status').textContent='';out.innerHTML='<p class="loading" role="status">Đang đọc tên cột và 5 dòng đầu…</p>';
    try{const data=new FormData();data.set('file',file);const d=await api('/api/column-mapping/preview',{method:'POST',body:data});if(token!==version||requestRevision!==previewRevision)return;
      out.innerHTML=table(d.preview,'xem_truoc_danh_gia');
      const groupOptions=()=>[{value:'',label:'Không lọc'},...d.columns.map(value=>({value,label:value}))];
      $('#assessment-mapping').innerHTML=`<h3>Chọn cột và xác nhận đơn vị</h3>${assessmentFields.map(([key,label,units])=>`<div class="controls">${select('assessment-map-'+key,label,[{value:'',label:'Chọn cột'},...d.columns],d.suggestions[key])}${select('assessment-unit-'+key,'Đơn vị',units,typeof units[0]==='object'?units[0].value:units[0])}</div>`).join('')}<label class="check"><input id="assessment-positive" type="checkbox">Nguồn quy ước dòng xả dương: đổi dấu thành dòng xả âm.</label><h3>Lọc một pin và một chu kỳ (nếu file có nhiều nhóm)</h3>${['battery','cycle','phase'].map(key=>`<div class="controls">${select('assessment-filter-'+key,({battery:'Cột mã pin',cycle:'Cột chu kỳ',phase:'Cột giai đoạn'})[key],groupOptions(), '')}<div class="field"><label for="assessment-filter-value-${key}">Giá trị cần lấy</label><input id="assessment-filter-value-${key}" maxlength="100"></div></div>`).join('')}<p class="sub">Thời gian chuẩn hóa bắt đầu tại dòng đầu của đoạn đã chọn. Với SDU phải chọn đúng đầu xả; chỉ đổi tên cột chưa chứng minh mô hình phù hợp.</p>`;
      $('#assessment-progress').innerHTML=assessmentSteps(2);taskUI();
    }catch(e){if(token===version&&requestRevision===previewRevision&&e.name!=='AbortError')out.innerHTML=notice(e.message,'error');}
  }
  $('#assessment-file').onchange=preview;
  for(const button of form.querySelectorAll('[data-assessment-sample]'))button.onclick=()=>{
    invalidate();previewRevision++;sample=true;const task=button.dataset.assessmentSample;$(`input[name=task][value=${task}]`,form).checked=true;defaults(task);taskUI();$('#assessment-file').value='';$('#assessment-preview').innerHTML='';$('#assessment-mapping').innerHTML='';$('#assessment-battery').value=task==='sdu'?'SDU_01':'Mẫu BAIC 01';$('#assessment-conditions').value='Dữ liệu mẫu kèm sản phẩm; đã tham gia học mô hình';$('#assessment-sample-status').textContent='Đang dùng mẫu '+(task==='sdu'?'SDU':'BAIC')+' để minh họa thao tác; không phải kiểm chứng độc lập.';
  };
  function payload(){
    const body=new FormData(),task=currentTask();body.set('task',task);body.set('sample',sample?'1':'0');body.set('model',$('#assessment-model').value);body.set('phase_code',$('#assessment-phase').value);body.set('cycle',$('#assessment-cycle').value);
    body.set('confirmed',$('#assessment-confirm').checked?'1':'0');body.set('configuration',$('#assessment-confirm').checked?'BAIC EU500 145Ah':'');
    const profile={};for(const [key,id] of Object.entries({battery_id:'battery',measured_at:'date',conditions:'conditions',origin:'origin',chemistry:'chemistry',level:'level',mode:'mode',nominal_ah:'nominal'}))profile[key]=$('#assessment-'+id).value;
    body.set('profile',JSON.stringify(profile));
    if(task==='capacity'){body.set('reference_ah',$('#assessment-reference').value);body.set('measured_ah',$('#assessment-measured').value);body.set('comparable',$('#assessment-comparable').checked?'1':'0');}
    if(!sample&&task!=='capacity'){
      const file=$('#assessment-file').files[0];if(!file)throw new Error('Chọn file hoặc dùng dữ liệu mẫu.');body.set('file',file);
      const mapping={},units={};for(const [key] of assessmentFields){mapping[key]=$('#assessment-map-'+key)?.value||'';units[key]=$('#assessment-unit-'+key)?.value||'';}
      body.set('mapping',JSON.stringify(mapping));body.set('units',JSON.stringify(units));body.set('positive_discharge',$('#assessment-positive')?.checked?'1':'0');
      for(const key of ['battery','cycle','phase']){body.set('filter_'+key+'_column',$('#assessment-filter-'+key)?.value||'');body.set('filter_'+key+'_value',$('#assessment-filter-value-'+key)?.value||'');}
    }
    return body;
  }
  form.onsubmit=async event=>{event.preventDefault();const rev=revision,out=$('#assessment-preflight'),button=$('#assessment-check');checked=null;$('#assessment-run').disabled=true;$('#assessment-result').innerHTML='';button.disabled=true;
    try{const body=payload();out.innerHTML='<p class="loading" role="status">Đang kiểm tra file và phạm vi mô hình…</p>';const d=await api('/api/assessment/check',{method:'POST',body});if(token!==version||rev!==revision)return;
      checked=d.ready?body:null;$('#assessment-run').disabled=!d.ready;$('#assessment-progress').innerHTML=assessmentSteps(3);
      out.innerHTML=panel('3. Kết quả kiểm tra',d.ready?'Có thể chạy phân tích đã chọn.':'Chưa chạy mô hình; cần xử lý các mục sau.',notice(d.scope.message,d.ready?'':'error')+d.warnings.map(w=>notice(w,'warning')).join('')+table(d.checks,'kiem_tra_truoc_phan_tich')+(!d.ready?'<p>Kiểm tra lại hồ sơ và dữ liệu. Nếu khác cấu hình SDU/BAIC, chọn “Tôi có tín hiệu đo”.</p>':'<p>Bấm “Phân tích & lập báo cáo” để tiếp tục.</p>'));
    }catch(e){if(token===version&&rev===revision&&e.name!=='AbortError')out.innerHTML=notice(e.message,'error');}finally{button.disabled=false;}
  };
  $('#assessment-run').onclick=async()=>{if(!checked)return;const rev=revision,body=checked,button=$('#assessment-run'),out=$('#assessment-result');button.disabled=true;out.innerHTML='<p class="loading" role="status">Đang phân tích và lập hồ sơ…</p>';
    try{const item=await api('/api/assessment',{method:'POST',body});if(token!==version||rev!==revision)return;$('#assessment-progress').innerHTML=assessmentSteps(4);out.innerHTML=assessmentResult(item)+panel('Báo cáo và lịch sử','Tự tải báo cáo để lưu; lịch sử tab sẽ mất khi đóng tab.',assessmentExportButtons()+'<label class="check"><input id="assessment-persist" type="checkbox">Lưu hồ sơ lâu dài trên trình duyệt của thiết bị này (không đồng bộ tài khoản).</label><div class="actions"><button class="button" id="assessment-save" type="button">Lưu vào lịch sử</button><a class="button" href="#history">Xem & so sánh lịch sử</a></div><p id="assessment-saved" role="status"></p>');
      assessmentBindExports(item,out);$('#assessment-save').onclick=()=>{try{assessmentSave(item,$('#assessment-persist').checked);$('#assessment-saved').textContent=$('#assessment-persist').checked?'Đã lưu trên thiết bị này. Có thể xóa trong Lịch sử.':'Đã lưu trong tab hiện tại.';}catch(e){$('#assessment-saved').textContent='Trình duyệt không cho lưu hoặc đã hết dung lượng. Hãy tải báo cáo để giữ kết quả.';}};
      out.scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
    }catch(e){if(token===version&&rev===revision&&e.name!=='AbortError')out.innerHTML=notice(e.message,'error');}finally{if(token===version&&rev===revision)button.disabled=!checked;}
  };
  taskUI();
  receiveUpload('assessment','assessment-file');
  const sampleTask=state('check').sampleTask;if(sampleTask){delete state('check').sampleTask;form.querySelector('[data-assessment-sample="'+sampleTask+'"]')?.click();}
}
function assessmentAll(){
  return [...new Map([...assessmentRecords(),...assessmentRecords(assessmentStorage(true))].map(item=>[item.record.id,item])).values()].sort((a,b)=>b.record.created_at.localeCompare(a.record.created_at));
}
function assessmentComparable(a,b){
  const keys=['battery_id','origin','chemistry','level','mode','nominal_ah','conditions'];
  return a.task===b.task&&a.model===b.model&&a.model_sha256===b.model_sha256&&a.source_battery_id===b.source_battery_id&&a.sample===b.sample&&keys.every(k=>a.profile[k]===b.profile[k])&&a.profile.conditions&&a.profile.measured_at&&b.profile.measured_at&&a.profile.measured_at!==b.profile.measured_at&&a.results[0].phase_code===b.results[0].phase_code&&(a.task!=='capacity'||a.results[0].reference_ah===b.results[0].reference_ah);
}
async function assessmentHistory(token){
  const unique=assessmentAll();
  const backup=panel('Sao lưu và khôi phục','Tải gói JSON để chuyển thiết bị. Khi nhập, báo cáo được tạo lại từ dữ liệu; file HTML trong gói không được sử dụng.',`<div class="actions"><button class="button" id="assessment-backup" ${unique.length?'':'disabled'}>Tải toàn bộ hồ sơ JSON</button><a class="button" href="#check">Tạo hồ sơ mới</a></div><div class="field"><label for="assessment-import">Nhập một hồ sơ hoặc gói sao lưu JSON · tối đa 5 MiB</label><input id="assessment-import" type="file" accept=".json"></div><label class="check"><input id="assessment-import-persist" type="checkbox">Lưu hồ sơ nhập trên thiết bị này (mặc định chỉ trong tab).</label><p id="assessment-import-status" role="status"></p>`);
  const rows=unique.length?`<div class="field"><label for="assessment-history-filter">Lọc theo mã pin / xe</label><input id="assessment-history-filter" type="search" placeholder="Nhập mã pin"></div><div class="table-wrap"><table><thead><tr><th>Chọn</th><th>Mã pin / xe</th><th>Ngày đo</th><th>Bài toán / mô hình</th><th>SOH</th><th>Thao tác</th></tr></thead><tbody>${unique.map(({record:r})=>`<tr data-battery="${esc(r.profile.battery_id.toLowerCase())}"><td><input type="checkbox" data-compare="${esc(r.id)}" aria-label="Chọn ${esc(r.profile.battery_id)} ngày ${esc(r.profile.measured_at)}"></td><td>${esc(r.profile.battery_id)}${r.sample?'<br><small>Mẫu minh họa</small>':''}${r.restored?'<br><small>Hồ sơ nhập · chưa xác thực</small>':''}</td><td>${esc(r.profile.measured_at)}</td><td>${esc(r.title)}<br><small>${esc(r.model)}</small></td><td>${fmt(r.results[0].soh_pct,2)} %</td><td><button class="button small" data-open-assessment="${esc(r.id)}">Mở báo cáo</button> <button class="button small" data-delete-assessment="${esc(r.id)}">Xóa</button></td></tr>`).join('')}</tbody></table></div><div class="actions"><button class="button" id="assessment-compare">Đối chiếu hai lần đo</button><button class="button" id="assessment-trend">Phân tích xu hướng từ hồ sơ đã chọn</button></div><div class="field"><label for="assessment-trend-threshold">Mốc SOH cần đối chiếu (%)</label><input id="assessment-trend-threshold" type="number" min="1" max="99" value="80"></div><p>Chọn đúng 2 hồ sơ để đối chiếu hoặc từ 5 hồ sơ khác ngày để phân tích xu hướng. Cần cùng pin, bài toán, mô hình, giai đoạn và điều kiện đo.</p>`:'<p>Chưa có hồ sơ. Sau khi phân tích, chọn “Lưu vào lịch sử”, hoặc nhập gói sao lưu bên trên.</p>';
  if(!put(header('Hồ sơ và lịch sử đánh giá','Lưu riêng trong trình duyệt. Tải gói sao lưu để tránh mất khi xóa dữ liệu trình duyệt.')+backup+panel('Hồ sơ đã lưu',`${unique.length} hồ sơ · tối đa 100 hồ sơ mỗi nơi lưu`,rows)+'<div id="assessment-comparison" aria-live="polite"></div><div id="assessment-history-report"></div>',token))return;
  $('#assessment-backup').onclick=()=>assessmentDownload(JSON.stringify({format:'vincent-assessments',version:1,records:unique.map(x=>x.record)},null,2),'application/json','sao_luu_ho_so_pin.json');
  $('#assessment-import').onchange=async()=>{
    const file=$('#assessment-import').files[0],out=$('#assessment-import-status');if(!file)return;
    try{if(file.size>5*1024*1024)throw new Error('Gói JSON tối đa 5 MiB.');const raw=JSON.parse(await file.text());if(token!==version||$('#assessment-import').files[0]!==file)return;out.textContent='Đang kiểm tra hồ sơ và tạo lại báo cáo…';
      const d=await api('/api/assessment/restore',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(raw)});if(token!==version||$('#assessment-import').files[0]!==file)return;
      const existing=new Set(assessmentAll().map(x=>x.record.id)),incoming=d.items.filter(x=>!existing.has(x.record.id)),storage=assessmentStorage($('#assessment-import-persist').checked);
      if(!storage)throw new Error('Trình duyệt không cho lưu. Hãy giữ gói sao lưu bên ngoài.');
      const merged=[...incoming,...assessmentRecords(storage)];if(merged.length>100)throw new Error('Vượt 100 hồ sơ tại nơi lưu đã chọn. Hãy xóa hoặc đổi nơi lưu trước khi nhập.');
      storage.setItem(assessmentKey,JSON.stringify(merged));toast('Đã nhập '+incoming.length+' hồ sơ; bỏ qua '+(d.items.length-incoming.length)+' mã đã có. Hồ sơ nhập chưa được xác thực.');render();
    }catch(e){if(token===version&&e.name!=='AbortError')out.textContent='Không nhập hồ sơ: '+e.message;}
  };
  const legacy=readHistory();
  if(legacy.length){$('#content').insertAdjacentHTML('beforeend',panel('Dự đoán trong giao diện cũ','Kết quả cũ chưa đủ hồ sơ để đối chiếu điều kiện đo.',table(legacy,'lich_su_cu')+'<button class="button" id="assessment-clear-legacy">Xóa lịch sử dự đoán cũ</button>'));$('#assessment-clear-legacy').onclick=()=>{try{assessmentStorage()?.removeItem('vincent-history');render();}catch(e){toast('Không thể xóa lịch sử cũ.');}};}
  if(!unique.length)return;
  let historyRevision=0;document.querySelectorAll('[data-compare],#assessment-history-filter,#assessment-trend-threshold').forEach(node=>node.addEventListener('input',()=>{historyRevision++;$('#assessment-comparison').innerHTML='';}));
  const selected=()=>[...document.querySelectorAll('[data-compare]:checked')].map(x=>unique.find(item=>item.record.id===x.dataset.compare).record).sort((a,b)=>a.profile.measured_at.localeCompare(b.profile.measured_at));
  $('#assessment-history-filter').oninput=e=>{for(const tr of document.querySelectorAll('[data-battery]')){tr.hidden=!tr.dataset.battery.includes(e.target.value.toLowerCase());if(tr.hidden)$('[data-compare]',tr).checked=false;}};
  for(const b of document.querySelectorAll('[data-delete-assessment]'))b.onclick=()=>{try{for(const storage of [assessmentStorage(),assessmentStorage(true)].filter(Boolean))storage.setItem(assessmentKey,JSON.stringify(assessmentRecords(storage).filter(x=>x.record.id!==b.dataset.deleteAssessment)));render();}catch(e){toast('Không thể xóa trong trình duyệt này.');}};
  for(const b of document.querySelectorAll('[data-open-assessment]'))b.onclick=()=>{const item=unique.find(x=>x.record.id===b.dataset.openAssessment),out=$('#assessment-history-report');out.innerHTML=assessmentResult(item)+assessmentExportButtons();assessmentBindExports(item,out);out.scrollIntoView({block:'start'});};
  $('#assessment-compare').onclick=()=>{
    const records=selected(),out=$('#assessment-comparison');if(records.length!==2){out.innerHTML=notice('Chọn đúng hai hồ sơ để đối chiếu.');return;}
    const [a,b]=records,compatible=assessmentComparable(a,b),finite=records.every(r=>Number.isFinite(r.results[0].soh_pct));
    out.innerHTML=panel('Đối chiếu hai hồ sơ',compatible?'Điều kiện khai báo phù hợp; chưa xác nhận nguyên nhân thay đổi.':'Không đủ điều kiện tính mức thay đổi có ý nghĩa.',table(records.map(r=>({'Mã pin':r.profile.battery_id,'Ngày đo':r.profile.measured_at,'Bài toán':r.title,'Mô hình':r.model,'SOH (%)':r.results[0].soh_pct,'Điều kiện đo':r.profile.conditions})),'doi_chieu_ho_so')+(compatible&&finite?notice('Thay đổi giữa hai ngày đo: '+fmt(b.results[0].soh_pct-a.results[0].soh_pct,2)+' điểm % SOH. Chênh lệch có thể do sai số mô hình hoặc phép đo.'):notice('Chỉ hiển thị hai hồ sơ; chưa đủ điều kiện tính mức thay đổi.','warning'))+(records.some(r=>r.restored)?notice('Có hồ sơ nhập từ file, chưa xác thực. Hãy đối chiếu file đo nguồn.','warning'):''));
  };
  $('#assessment-trend').onclick=async()=>{
    const submittedRevision=historyRevision,records=selected(),out=$('#assessment-comparison'),button=$('#assessment-trend');button.disabled=true;
    try{if(records.length<5)throw new Error('Chọn ít nhất 5 hồ sơ khác ngày, cùng pin và điều kiện.');out.innerHTML='<p class="loading">Đang kiểm tra lịch sử và tính xu hướng…</p>';
      const d=await api('/api/assessment/trend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({records,threshold:Number($('#assessment-trend-threshold').value)})});if(token!==version||submittedRevision!==historyRevision)return;
      out.innerHTML=panel('Xu hướng của '+d.battery_id,d.result.message,kpis([{label:'Số mốc đo',value:d.result.samples},{label:'SOH mới nhất',value:d.result.soh_pct,unit:'%',digits:2},{label:'Ngày xuống mốc (thử nghiệm)',value:d.crossing_date||'Chưa ước tính'}])+'<div id="assessment-history-trend" class="plot"></div>'+notice(d.scope)+table(d.points,'lich_su_theo_ngay'));
      chart('assessment-history-trend',[series('SOH từ hồ sơ',d.result.points,'position','soh_pct'),series('Ngoại suy thử nghiệm',d.result.forecast,'position','soh_pct')],'Ngày kể từ '+d.first_date,'SOH (%)');
    }catch(e){if(token===version&&submittedRevision===historyRevision&&e.name!=='AbortError')out.innerHTML=notice(e.message,'error');}finally{button.disabled=false;}
  };
}
