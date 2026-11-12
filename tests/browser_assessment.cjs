// Run against a running app: ASSESSMENT_BASE_URL=http://127.0.0.1:8504 node tests/browser_assessment.cjs
const {chromium, expect} = require('playwright/test');
const fs = require('node:fs/promises');
(async () => {
  const browser = await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox']});
  try {
    const context = await browser.newContext({viewport:{width:1365,height:900},locale:'vi-VN'});
    const page = await context.newPage(), errors=[];
    page.on('pageerror', e=>errors.push(e.message));
    const base=process.env.ASSESSMENT_BASE_URL||'http://127.0.0.1:8504';
    const open=async()=>{await page.goto(base+'/#check');await expect(page.locator('#assessment-form')).toBeVisible();};
    const check=async()=>{await page.locator('#assessment-check').click();await expect(page.locator('#assessment-run')).toBeEnabled();};
    const run=async()=>{await page.locator('#assessment-run').click();await expect(page.locator('#assessment-save')).toBeVisible();};
    await open();
    await page.locator('[data-assessment-sample=sdu]').click();await check();await run();
    await expect(page.locator('#assessment-result')).toContainText('SOH trên 100%');
    const downloadEvent=page.waitForEvent('download');await page.locator('[data-assessment-html]').click();
    const download=await downloadEvent,html=await fs.readFile(await download.path(),'utf8');
    if(!html.includes('In / Lưu PDF')||!html.includes('<svg')||!html.includes('SHA256')&&!html.includes('source_sha256'))throw new Error('Incomplete portable report');
    const reportPage=await context.newPage();await reportPage.setContent(html);await reportPage.pdf({path:'/tmp/vincent-assessment-report.pdf',printBackground:true});await reportPage.close();
    await page.locator('#assessment-save').click();await page.goto(base+'/#history');
    await expect(page.locator('[data-open-assessment]')).toHaveCount(1);
    await page.reload();await expect(page.locator('[data-open-assessment]')).toHaveCount(1);
    await open();await page.locator('[data-assessment-sample=bms]').click();await check();await run();
    await expect(page.locator('#assessment-result')).toContainText('SOH suy ra từ dòng điện/SOC');
    for(const [date,value] of [['2026-11-10','90'],['2026-11-12','87']]){
      await open();await page.locator('input[name=task][value=capacity]').check();
      await page.locator('#assessment-battery').fill('XE-001');await page.locator('#assessment-date').fill(date);
      await page.locator('#assessment-conditions').fill('25°C · cùng thiết bị · cùng chế độ xả');
      await page.locator('#assessment-reference').fill('100');await page.locator('#assessment-measured').fill(value);await page.locator('#assessment-comparable').check();
      await check();
      await page.locator('#assessment-measured').fill(String(Number(value)+1));await expect(page.locator('#assessment-run')).toBeDisabled();
      await page.locator('#assessment-measured').fill(value);await check();await run();
      await page.locator('#assessment-persist').check();await page.locator('#assessment-save').click();
    }
    await page.goto(base+'/#history');await expect(page.locator('[data-open-assessment]')).toHaveCount(3);
    for(const row of await page.locator('tr[data-battery="xe-001"]').all())await row.locator('[data-compare]').check();
    await page.locator('#assessment-compare').click();await expect(page.locator('#assessment-comparison')).toContainText('-3');
    await page.locator('[data-open-assessment]').first().click();await expect(page.locator('#assessment-history-report')).toContainText('XE-001');
    // Unit conversion and unknown-domain signal analysis through the real file input.
    await open();await page.locator('#assessment-battery').fill('PIN-KHAC');
    const csv='Time,Voltage,Current,Temperature\n0,3300,-1000,298.15\n60000,3250,-1000,298.25\n120000,3200,-1000,298.35\n';
    await page.locator('#assessment-file').setInputFiles({name:'signals.csv',mimeType:'text/csv',buffer:Buffer.from(csv)});
    await expect(page.locator('#assessment-map-time')).toBeVisible();
    await page.locator('#assessment-unit-time').selectOption('ms');await page.locator('#assessment-unit-terminal_voltage').selectOption('mV');await page.locator('#assessment-unit-terminal_current').selectOption('mA');await page.locator('#assessment-unit-temperature').selectOption('K');
    await check();await run();await expect(page.locator('#assessment-result')).toContainText('chỉ được tổng hợp tín hiệu');
    // A changed profile cannot keep an earlier successful preflight or prediction.
    await page.locator('#assessment-nominal').fill('145');await expect(page.locator('#assessment-run')).toBeDisabled();await expect(page.locator('#assessment-result')).toBeEmpty();
    await page.screenshot({path:'/tmp/vincent-assessment-upload.png',fullPage:true});
    await page.goto(base+'/');await page.locator('#home-example').click();await expect(page.locator('#assessment-sample-status')).toContainText('BAIC');
    // A response from an obsolete preflight must never enable prediction.
    let release,entered;const gate=new Promise(resolve=>release=resolve),intercepted=new Promise(resolve=>entered=resolve);
    await page.route('**/api/assessment/check',async route=>{entered();await gate;await route.continue();});
    await page.locator('#assessment-check').click();await intercepted;
    await page.locator('#assessment-conditions').fill('Điều kiện đã đổi trong lúc chờ');
    const obsoleteResponse=page.waitForResponse(r=>r.url().endsWith('/api/assessment/check'));release();await obsoleteResponse;
    await expect(page.locator('#assessment-check')).toBeEnabled();await expect(page.locator('#assessment-run')).toBeDisabled();await expect(page.locator('#assessment-preflight')).toBeEmpty();await page.unroute('**/api/assessment/check');
    await page.setViewportSize({width:390,height:844});await page.reload();await expect(page.locator('#assessment-form')).toBeVisible();await page.evaluate(()=>{document.activeElement?.blur();window.scrollTo(0,0);});
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1);
    if(overflow)throw new Error('Mobile page overflows viewport');
    await page.screenshot({path:'/tmp/vincent-assessment-mobile.png',fullPage:true});
    const privateContext=await browser.newContext();await privateContext.addInitScript(()=>{for(const key of ['sessionStorage','localStorage'])Object.defineProperty(window,key,{get(){throw new DOMException('Blocked','SecurityError');}});});
    const privatePage=await privateContext.newPage();await privatePage.goto(base+'/#history');await expect(privatePage.locator('#content')).toContainText('Chưa có hồ sơ');await privateContext.close();
    if(errors.length)throw new Error('Browser errors: '+errors.join('; '));
    console.log('PASS: SDU + BMS prediction, unit-mapped upload, standalone report download, invalidation, session/persistent history, two-date comparison and mobile layout.');
    await context.close();
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
