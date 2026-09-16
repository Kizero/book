// Optional browser verification. Provide PLAYWRIGHT_MODULE and CHROME_PATH
// when using a bundled runtime; no changes are made to simulation state.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{})});
 const errors=[];const page=await browser.newPage({viewport:{width:1440,height:1024}});
 page.on('pageerror',e=>errors.push(e.message));
 await page.clock.install();await page.goto('http://127.0.0.1:4177');await page.waitForFunction(()=>window.cleaningGame);
 await page.locator('#start').click();await page.clock.runFor(100);
 const before=await page.evaluate(()=>window.cleaningGame.state());
 await page.keyboard.down('a');await page.clock.runFor(250);await page.keyboard.up('a');
 assert.ok((await page.evaluate(()=>window.cleaningGame.state())).player.x<before.player.x);
 await page.keyboard.press('Escape');
 const paused=await page.evaluate(()=>window.cleaningGame.snapshot());await page.clock.runFor(500);
 assert.equal((await page.evaluate(()=>window.cleaningGame.snapshot())).seconds,paused.seconds);
 assert.equal((await page.evaluate(()=>window.cleaningGame.state())).state,'paused');
 await page.locator('#resume').click();
 let terminal='',upgrades=0;
 for(let i=0;i<2000;i++){
  const s=await page.evaluate(()=>window.cleaningGame.state());
  if(s.state==='upgrade'){
   await page.locator('#show-upgrades').click();await page.clock.runFor(350);await page.screenshot({path:'artifacts/v2-desktop-upgrade.png',animations:'disabled'});
   const id=(process.env.UPGRADE_PRIORITY||'chain,power,wide,drone,skates').split(',').find(id=>s.offers.includes(id))||s.offers[0];await page.locator(`[data-upgrade="${id}"]`).click();upgrades++;continue;
  }
  if(['won','lost'].includes(s.state)){terminal=s.state;break;}
  if(s.state==='clearing'){await page.clock.runFor(300);continue;}
  const e=s.enemies.filter(e=>e.alive).sort((a,b)=>Math.hypot(a.x-s.player.x,a.y-s.player.y)-Math.hypot(b.x-s.player.x,b.y-s.player.y))[0];
  if(!e){await page.clock.runFor(200);continue;}
  const box=await page.locator('#game').boundingBox();
  await page.mouse.move(box.x+e.x/960*box.width,box.y+e.y/600*box.height);
  const dx=e.x-s.player.x,dy=e.y-s.player.y,d=Math.hypot(dx,dy);
  // Approach at range, step back before contact, keep within the playable yard.
  let mx=0,my=0;
  if(d>150){mx=dx/d;my=dy/d;}
  if(d<105){mx=-dx/d;my=-dy/d;}
  if(s.player.x<90)mx=Math.max(mx,.8);if(s.player.x>870)mx=Math.min(mx,-.8);
  if(s.player.y<90)my=Math.max(my,.8);if(s.player.y>510)my=Math.min(my,-.8);
  for(const [key,on]of [['a',mx<-.25],['d',mx>.25],['w',my<-.25],['s',my>.25]]){if(on)await page.keyboard.down(key);else await page.keyboard.up(key);}
  if(s.player.ammo>=68)await page.mouse.click(box.x+e.x/960*box.width,box.y+e.y/600*box.height);
  await page.clock.runFor(200);
 }
 for(const key of ['a','d','w','s'])await page.keyboard.up(key);
 const summary=await page.evaluate(()=>window.cleaningGame.snapshot());
 await page.clock.runFor(350);await page.screenshot({path:'artifacts/v2-desktop-result.png',animations:'disabled'});
 console.log('DESKTOP',JSON.stringify(summary));assert.equal(terminal,'won');assert.equal(upgrades,summary.roomResults.length-1);assert.equal(errors.length,0);
 await page.locator('#again').click();assert.equal((await page.evaluate(()=>window.cleaningGame.snapshot())).stats.kills,0);
 const mobile=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:1});
 mobile.on('pageerror',e=>errors.push(e.message));await mobile.clock.install();await mobile.goto('http://127.0.0.1:4177');
 await mobile.waitForFunction(()=>window.cleaningGame);await mobile.locator('[data-weapon="foam"]').tap();await mobile.clock.runFor(350);await mobile.screenshot({path:'artifacts/v2-mobile-start.png',animations:'disabled'});await mobile.locator('#start').tap();
 const joystick=mobile.locator('#joystick'),r=await joystick.boundingBox();
 const touchSession=await mobile.context().newCDPSession(mobile);
 await touchSession.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:r.x+r.width/2+25,y:r.y+r.height/2}]});
 await mobile.clock.runFor(300);
 await touchSession.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
 const ms=await mobile.evaluate(()=>window.cleaningGame.state());assert.ok(ms.player.x>300);assert.equal(ms.weapon,'foam');
 const stoppedX=ms.player.x;await mobile.clock.runFor(100);assert.equal((await mobile.evaluate(()=>window.cleaningGame.state())).player.x,stoppedX);
 await mobile.screenshot({path:'artifacts/v2-mobile-play.png'});
 assert.equal(await mobile.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 assert.equal(errors.length,0);console.log('MOBILE',JSON.stringify({movement:true,releaseStops:true,noOverflow:true,errors}));
 fs.writeFileSync('artifacts/v2-browser-verification.json',JSON.stringify({desktop:{terminal,upgrades,summary},mobile:{movement:true,releaseStops:true,noOverflow:true},errors},null,2));
 await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1;setTimeout(()=>process.exit(1),1000);});
