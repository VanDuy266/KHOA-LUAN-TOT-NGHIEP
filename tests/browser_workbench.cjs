// Optional full workflow browser validation against a running web app.
const {chromium, expect}=require('playwright/test');
const {existsSync}=require('node:fs');
const fs=require('node:fs/promises');
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||(existsSync('/usr/bin/chromium')?'/usr/bin/chromium':chromium.executablePath()),args:['--no-sandbox']});
  try{
    const base=process.env.ASSESSMENT_BASE_URL||'http://127.0.0.1:8506',context=await browser.newContext({viewport:{width:1365,height:900},locale:'vi-VN'}),page=await context.newPage(),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto(base+'/');await expect(page.locator('#dashboard-file')).toBeVisible();await expect(page.locator('h1')).toHaveText('Đánh giá pin từ lần đo thực tế');
    const trainingCSV=await (await page.request.get(base+'/api/download/training-template')).text();
    await page.goto(base+'/#training');await page.locator('#training-file').setInputFiles({name:'my_labeled_data.csv',mimeType:'text/csv',buffer:Buffer.from(trainingCSV)});
    await page.locator('#training-label-source').fill('Browser test fixture: reference capacity labels');
    await page.getByText('Dùng mô hình vừa học để dự đoán dữ liệu mới',{exact:true}).click();await page.locator('#training-portable-enabled').check();
    await page.locator('#training-domain-chemistry').selectOption('NMC');await page.locator('#training-domain-level').selectOption('cell');await page.locator('#training-domain-mode').selectOption('discharge');await page.locator('#training-domain-nominal').fill('2.4');await page.locator('#training-domain-protocol').fill('V/A/°C, thống kê 120 giây đầu theo cùng quy trình đo');
    await page.locator('#training-form button[type=submit]').click();await expect(page.locator('#training-use-custom')).toBeEnabled({timeout:30000});
    const portableDownload=page.waitForEvent('download');await page.locator('#training-portable').click();const portable=JSON.parse(await fs.readFile(await (await portableDownload).path(),'utf8'));if(!portable.domain||!portable.coefficients)throw new Error('Portable model is incomplete');
    await page.locator('#training-use-custom').click();await expect(page.locator('#custom-model-preview')).toContainText('Đã đọc mô hình');
    const lines=trainingCSV.trim().split(/\r?\n/),cols=lines[0].split(','),target=cols.indexOf('soh_pct'),newCSV=lines.slice(0,4).map(line=>line.split(',').filter((_,i)=>i!==target).join(',')).join('\n');
    await page.locator('#custom-data-file').setInputFiles({name:'new_unlabeled.csv',mimeType:'text/csv',buffer:Buffer.from(newCSV)});await page.locator('#custom-confirm').check();await page.locator('#custom-form button[type=submit]').click();
    await expect(page.locator('#custom-result')).toContainText('Tính trực tiếp từ CSV mới');await expect(page.locator('#custom-result tbody tr')).toHaveCount(4);
    // Actual user-style files can produce feature tables and feed the training form.
    const raw=['battery,cycle,phase_code,time,terminal_voltage,terminal_current,temperature,soh_pct'];
    for(let cycle=1;cycle<=2;cycle++)for(let t=0;t<=120;t+=10)raw.push(['USER-PIN',cycle,0,t,4.1-t*.001,-2,25+t*.01,95-cycle].join(','));
    await page.locator('#custom-signals-file').setInputFiles({name:'my_raw_signals.csv',mimeType:'text/csv',buffer:Buffer.from(raw.join('\n'))});await page.locator('#custom-features-form button').click();await expect(page.locator('#custom-train-features')).toBeEnabled();await page.locator('#custom-train-features').click();await expect(page.locator('#training-file')).toHaveValue(/dac_trung_co_nhan/);
    // Build five independent API records from submitted measurements, then use UI restore and trend.
    const records=[];
    for(let i=0;i<5;i++){
      const profile={battery_id:'OWN-TRACK',measured_at:`2026-11-0${i+1}`,conditions:'25°C, cùng thiết bị',chemistry:'LFP',level:'pack',mode:'discharge',origin:'other',nominal_ah:100};
      const r=await page.request.post(base+'/api/assessment',{form:{task:'capacity',profile:JSON.stringify(profile),reference_ah:'100',measured_ah:String(99-4*i),comparable:'1'}});if(!r.ok())throw new Error(await r.text());records.push((await r.json()).record);
    }
    await page.goto(base+'/#history');await page.locator('#assessment-import-persist').check();await page.locator('#assessment-import').setInputFiles({name:'backup.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({format:'vincent-assessments',version:1,records}))});await expect(page.locator('[data-open-assessment]')).toHaveCount(5);
    for(const box of await page.locator('[data-compare]').all())await box.check();await page.locator('#assessment-trend').click();await expect(page.locator('#assessment-comparison')).toContainText('OWN-TRACK');await expect(page.locator('#assessment-history-trend svg')).toBeVisible();
    const backupEvent=page.waitForEvent('download');await page.locator('#assessment-backup').click();const backup=await fs.readFile(await (await backupEvent).path());
    const otherContext=await browser.newContext(),otherPage=await otherContext.newPage();await otherPage.goto(base+'/#history');await expect(otherPage.locator('#content')).toContainText('Chưa có hồ sơ');await otherPage.locator('#assessment-import').setInputFiles({name:'restore.json',mimeType:'application/json',buffer:backup});await expect(otherPage.locator('[data-open-assessment]')).toHaveCount(5);await otherContext.close();
    await page.goto(base+'/');await expect(page.locator('.dashboard-record')).toHaveCount(3);await page.screenshot({path:'/tmp/vincent-dashboard-final.png',fullPage:true});
    await page.locator('#theme').click();await page.screenshot({path:'/tmp/vincent-dashboard-final-dark.png',fullPage:true});
    await page.setViewportSize({width:390,height:844});await page.reload();await expect(page.locator('#dashboard-file')).toBeVisible();await page.evaluate(()=>{document.activeElement?.blur();window.scrollTo(0,0);});if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw new Error('Dashboard mobile overflow');await page.screenshot({path:'/tmp/vincent-dashboard-final-mobile.png',fullPage:true});
    await page.goto(base+'/#guide');await expect(page.locator('#content')).toContainText('Mô hình của tôi');
    // Changing inputs must clear results in the older analysis forms too.
    await page.goto(base+'/#health');await expect(page.locator('#health-file')).toBeVisible();
    await page.locator('#health-file').setInputFiles({name:'history.csv',mimeType:'text/csv',buffer:Buffer.from('position,soh_pct\n0,99\n1,95\n2,91\n3,87\n4,83\n')});await page.locator('#health-form button[type=submit]').click();await expect(page.locator('#health-result .assessment-card')).toBeVisible();await page.locator('#health-threshold').fill('75');await expect(page.locator('#health-result')).toBeEmpty();
    await page.goto(base+'/#fault');await expect(page.locator('#fault-upload')).toBeVisible();await page.locator('#fault-sample').selectOption({index:1});await page.locator('#fault-form button[type=submit]').click();await expect(page.locator('#fault-result .assessment-card')).toBeVisible();await page.locator('#fault-sample').selectOption({index:2});await expect(page.locator('#fault-result')).toBeEmpty();
    await page.goto(base+'/#forecast');await page.locator('#use-sample').check();await page.locator('#upload-form button[type=submit]').click();await expect(page.locator('#form-result .kpis')).toBeVisible();await page.locator('.model-settings summary').click();await page.locator('#predict-model').selectOption('Ridge');await expect(page.locator('#form-result')).toBeEmpty();
    if(errors.length)throw new Error(errors.join('; '));
    console.log('PASS: real file training, portable Ridge inference on unlabeled CSV, raw feature extraction, browser backup/restore across contexts, calendar trend, dashboard and guide.');await context.close();
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
