// ASSESSMENT_BASE_URL=http://127.0.0.1:8509 node tests/browser_assessment.cjs
const {chromium,expect}=require('playwright/test');
const fs=require('node:fs/promises');
const {existsSync}=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||(existsSync('/usr/bin/chromium')?'/usr/bin/chromium':chromium.executablePath()),args:['--no-sandbox']});
 try{
  const base=process.env.ASSESSMENT_BASE_URL||'http://127.0.0.1:8504',context=await browser.newContext({viewport:{width:1365,height:900},locale:'vi-VN'}),page=await context.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const open=async()=>{await page.goto(base+'/?test='+Date.now()+'#check');await expect(page.locator('#assessment-form')).toBeVisible();};
  const sample=async task=>{await page.locator('#assessment-samples>summary').click();await page.locator('[data-assessment-sample='+task+']').click();};
  const run=async()=>{await page.locator('#assessment-check').click();await expect(page.locator('#assessment-save')).toBeVisible();await expect(page.locator('#assessment-form')).toBeHidden();};
  await open();await expect(page.locator('#research-navigation')).not.toHaveAttribute('open','');await expect(page.locator('.assessment-steps')).toHaveCount(0);
  await sample('sdu');await run();await expect(page.locator('#assessment-result')).toContainText('SOH trên 100%');
  const downloadEvent=page.waitForEvent('download');await page.locator('[data-assessment-html]').click();const download=await downloadEvent,html=await fs.readFile(await download.path(),'utf8');
  if(!html.includes('In / Lưu PDF')||!html.includes('<svg')||!html.includes('source_sha256'))throw new Error('Incomplete report');
  const report=await context.newPage();await report.setContent(html);await report.pdf({path:'/tmp/vincent-assessment-report.pdf',printBackground:true});await report.close();
  await page.locator('#assessment-save').click();await page.goto(base+'/#history');await expect(page.locator('[data-open-assessment]')).toHaveCount(1);await page.reload();await expect(page.locator('[data-open-assessment]')).toHaveCount(1);
  await open();await sample('bms');await run();await expect(page.locator('#assessment-result')).toContainText('SOH suy ra từ dòng điện/SOC');
  for(const [date,value] of [['2026-11-10','90'],['2026-11-12','87']]){
   await open();await page.locator('#assessment-task').selectOption('capacity');await page.locator('#assessment-battery').fill('XE-001');await page.locator('#assessment-date').fill(date);await page.locator('.analysis-settings>summary').click();await page.locator('#assessment-conditions').fill('25°C · cùng thiết bị · cùng chế độ xả');await page.locator('#assessment-reference').fill('100');await page.locator('#assessment-measured').fill(value);await page.locator('#assessment-comparable').check();await run();
   await page.locator('#assessment-edit').click();await expect(page.locator('#assessment-result')).toBeEmpty();await expect(page.locator('#assessment-form')).toBeVisible();await run();await page.locator('#assessment-persist').check();await page.locator('#assessment-save').click();
  }
  await page.goto(base+'/#history');await expect(page.locator('[data-open-assessment]')).toHaveCount(3);for(const row of await page.locator('tr[data-battery="xe-001"]').all())await row.locator('[data-compare]').check();await page.locator('#assessment-compare').click();await expect(page.locator('#assessment-comparison')).toContainText('-3');
  await page.locator('[data-open-assessment]').first().click();await expect(page.locator('#assessment-history-report')).toContainText('XE-001');
  await open();await page.locator('#assessment-battery').fill('PIN-KHAC');
  const csv='Time,Voltage,Current,Temperature\n0,3300,-1000,298.15\n60000,3250,-1000,298.25\n120000,3200,-1000,298.35\n';
  await page.locator('#assessment-file').setInputFiles({name:'signals.csv',mimeType:'text/csv',buffer:Buffer.from(csv)});await expect(page.locator('#assessment-map-time')).toBeVisible();for(const [key,value] of [['time','ms'],['terminal_voltage','mV'],['terminal_current','mA'],['temperature','K']])await page.locator('#assessment-unit-'+key).selectOption(value);await run();await expect(page.locator('#assessment-result')).toContainText('chỉ được tổng hợp tín hiệu');
  await page.locator('#assessment-edit').click();await expect(page.locator('#assessment-result')).toBeEmpty();
  // An obsolete prediction response must not reappear after the form changes.
  await open();await sample('sdu');let release,entered;const gate=new Promise(resolve=>release=resolve),intercepted=new Promise(resolve=>entered=resolve);
  await page.route('**/api/assessment',async route=>{entered();await gate;await route.continue();});await page.locator('#assessment-check').click();await intercepted;await page.locator('#assessment-battery').fill('CHANGED');const staleResponse=page.waitForResponse(r=>r.url().endsWith('/api/assessment'));release();await staleResponse;await expect(page.locator('#assessment-check')).toBeEnabled();await expect(page.locator('#assessment-result')).toBeEmpty();await expect(page.locator('#assessment-form')).toBeVisible();await page.unroute('**/api/assessment');
  await page.setViewportSize({width:390,height:844});await open();if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw new Error('Mobile form overflow');await page.screenshot({path:'/tmp/vincent-compact-mobile.png',fullPage:true});
  const other=await browser.newContext();await other.addInitScript(()=>{for(const key of ['sessionStorage','localStorage'])Object.defineProperty(window,key,{get(){throw new DOMException('Blocked','SecurityError');}});});const privatePage=await other.newPage();await privatePage.goto(base+'/#history');await expect(privatePage.locator('#content')).toContainText('Chưa có hồ sơ');await other.close();
  if(errors.length)throw new Error(errors.join('; '));console.log('PASS: compact single-submit analysis, samples, uploads/units, reports, edit/invalidation, history, stale-response protection and mobile.');await context.close();
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
