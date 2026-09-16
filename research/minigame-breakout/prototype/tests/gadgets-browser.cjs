const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH});const errors=[],results=[];
 try{
 for(const [gadget,weapon]of [['bubble','pressure'],['electric','foam'],['mop','pressure'],['duck','pressure']]){
  const page=await browser.newPage({viewport:{width:1440,height:1040}});page.on('pageerror',e=>errors.push(e.message));await page.clock.install();await page.goto('http://127.0.0.1:4177');await page.waitForFunction(()=>window.cleaningGame);
  await page.locator(`[data-gadget="${gadget}"]`).click();await page.locator(`[data-weapon="${weapon}"]`).click();await page.locator('#start').click();
  assert.equal((await page.evaluate(()=>window.cleaningGame.state())).mods[gadget],1);
  await page.keyboard.down('Space');await page.clock.runFor(2200);await page.keyboard.up('Space');await page.screenshot({path:`artifacts/gadget-${gadget}.png`,animations:'disabled'});
  results.push({gadget,weapon,summary:await page.evaluate(()=>window.cleaningGame.snapshot())});await page.close();
 }
 const p=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true});p.on('pageerror',e=>errors.push(e.message));await p.goto('http://127.0.0.1:4177');await p.waitForFunction(()=>window.cleaningGame);
 await p.screenshot({path:'artifacts/gadgets-mobile-start.png',animations:'disabled'});await p.locator('[data-gadget="duck"]').click();await p.locator('#start').click();assert.equal((await p.evaluate(()=>window.cleaningGame.state())).mods.duck,1);
 assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await p.screenshot({path:'artifacts/gadgets-mobile-play.png',animations:'disabled'});
 assert.equal(errors.length,0);fs.writeFileSync('artifacts/gadgets-ui.json',JSON.stringify({results,errors,mobileStart:true},null,2));console.log('Four starter gadgets, weapon switching, mobile start and no overflow passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
