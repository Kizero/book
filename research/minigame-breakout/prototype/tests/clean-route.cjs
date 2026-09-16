const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{})});
 const page=await browser.newPage({viewport:{width:1440,height:1040}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 // Replay the previously recorded clean-route map instead of picking a new
 // Date.now seed: this test checks the clean victory path, not bot strategy.
 await page.clock.install();await page.clock.setFixedTime(new Date(1789313868471));await page.goto('http://127.0.0.1:4177');await page.waitForFunction(()=>window.cleaningGame);
 await page.locator('[data-weapon="foam"]').click();await page.locator('#start').click();
 for(let i=0;i<900;i++){
  const {s,f}=await page.evaluate(()=>({s:window.cleaningGame.state(),f:window.cleaningGame.floor()}));
  if(s.state!=='playing')break;
  const p=s.player;let best=null,score=-Infinity;
  for(let row=3;row<f.rows-3;row+=3)for(let col=3;col<f.cols-3;col+=3){
   const x=col*20+10,y=row*20+10,amount=f.dirt[row*f.cols+col],d=Math.hypot(x-p.x,y-p.y);if(amount<.15)continue;
   const value=amount/(d+120);if(value>score){score=value;best={x,y,d};}
  }
  if(!best)break;let mx=(best.x-p.x)/Math.max(1,best.d),my=(best.y-p.y)/Math.max(1,best.d);
  for(const e of s.enemies)if(e.alive){const dx=p.x-e.x,dy=p.y-e.y,d=Math.hypot(dx,dy);if(d<140){mx+=dx/Math.max(d,1)*(140-d)/35;my+=dy/Math.max(d,1)*(140-d)/35;}}
  if(p.x<80)mx+=1;if(p.x>880)mx-=1;if(p.y<80)my+=1;if(p.y>520)my-=1;
  const box=await page.locator('#game').boundingBox();await page.mouse.move(box.x+best.x/960*box.width,box.y+best.y/600*box.height);
  for(const [key,on]of [['a',mx<-.2],['d',mx>.2],['w',my<-.2],['s',my>.2]]){if(on)await page.keyboard.down(key);else await page.keyboard.up(key);}
  if(p.ammo>=40)await page.mouse.click(box.x+best.x/960*box.width,box.y+best.y/600*box.height);
  await page.clock.runFor(100);
 }
 for(const k of ['a','d','w','s'])await page.keyboard.up(k);
 const summary=await page.evaluate(()=>window.cleaningGame.snapshot());
 assert.equal(summary.roomResults[0]?.reason,'clean');assert.ok(summary.roomResults[0].remaining>0);assert.equal(errors.length,0);
 await page.clock.runFor(1900);await page.screenshot({path:'artifacts/v2-clean-victory.png',animations:'disabled'});
 assert.ok(await page.getByText('清洁达标 · 怪物撤退',{exact:false}).count());
 fs.writeFileSync('artifacts/v2-clean-route.json',JSON.stringify({summary,errors},null,2));console.log('CLEAN ROUTE',JSON.stringify(summary.roomResults[0]));
 // Check a different starter really reaches the projectile path through UI input.
 await page.reload();await page.waitForFunction(()=>window.cleaningGame);await page.locator('[data-weapon="scatter"]').click();await page.locator('#start').click();
 let fired=false;for(let i=0;i<35;i++){await page.clock.runFor(150);const s=await page.evaluate(()=>window.cleaningGame.state());if(s.player.ammo>=20){await page.keyboard.press('Space');await page.clock.runFor(50);if((await page.evaluate(()=>window.cleaningGame.snapshot())).stats.shots>0){fired=true;break;}}}
 assert.ok(fired);assert.equal((await page.evaluate(()=>window.cleaningGame.snapshot())).weapon,'scatter');assert.equal(errors.length,0);console.log('SCATTER UI FIRE passed');
 await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1;setTimeout(()=>process.exit(1),1000);});
