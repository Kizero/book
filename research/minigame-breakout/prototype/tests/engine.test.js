import test from 'node:test';
import assert from 'node:assert/strict';
import {Game,ROOMS} from '../src/engine.js';
const advance=(g,seconds,input={})=>{for(let i=0;i<seconds*60;i++){g.update(1/60,input);g.drainEvents();}};

test('suction removes dirt and shells and makes firing possible',()=>{
 const g=new Game({seed:4});g.start();g.player.x=400;g.player.y=300;g.player.angle=0;
 g.enemies=[];const e=g.spawnEnemy('blob',490,300);e.speed=0;g.paint(470,300,45);
 const armor=e.armor;advance(g,.6,{angle:0});
 assert.ok(e.armor<armor);assert.ok(g.player.ammo>=20);const ammo=g.player.ammo;
 assert.equal(g.fire(),true);assert.equal(g.player.ammo,0);assert.ok(g.shots[0].damage>24);assert.equal(g.stats.shots,1);
 assert.equal(g.fire(),false);assert.ok(ammo>0);
});
test('bare enemy is vulnerable to suction even with no floor ammo',()=>{
 const g=new Game({seed:1});g.start();g.dirt.fill(0);g.enemies=[];const p=g.player;
 const e=g.spawnEnemy('blob',p.x+75,p.y);e.speed=0;e.armor=0;
 advance(g,.5,{angle:0});assert.ok(e.hp<36);
});
test('hostile mud projectile can be caught for ammunition',()=>{
 const g=new Game({seed:2});g.start();g.dirt.fill(0);g.player.ammo=0;
 g.hostileShots=[{x:g.player.x+90,y:g.player.y,vx:-150,vy:0,r:9,life:2}];
 g.update(1/60,{angle:0});assert.equal(g.hostileShots.length,0);assert.ok(g.player.ammo>=12);
});
test('chain deaths are resolved once and clean their surrounding floor',()=>{
 const g=new Game({seed:2});g.start();g.enemies=[];g.mods.chainDamage=100;
 const a=g.spawnEnemy('blob',200,200),b=g.spawnEnemy('blob',250,200),c=g.spawnEnemy('blob',290,200);
 g.paint(200,200,70);g.hitEnemy(a,999);g.hitEnemy(a,999);g.resolveDeaths();
 assert.equal(g.stats.kills,3);assert.equal(g.stats.chains,2);assert.equal(g.aliveCount,0);assert.equal(g.deathQueue.length,0);
 assert.equal(g.dirt[10*g.cols+10],0);assert.equal(g.events.filter(e=>e.type==='burst').length,3);
});
test('all rooms, offered upgrades and final automatic cleanup complete a run',()=>{
 const g=new Game({seed:6});g.start();
 for(let room=1;room<=ROOMS.length;room++){
  assert.equal(g.room,room);g.player.hp=3;
  while(g.aliveCount){for(const e of g.enemies)g.hitEnemy(e,999);g.resolveDeaths();}advance(g,1.8);
  assert.equal(g.cleanPercent,100);assert.equal(g.stats.rooms,room);
  if(room<ROOMS.length){assert.equal(g.state,'upgrade');const id=g.offers[0];assert.equal(g.offers.length,3);assert.equal(new Set(g.offers).size,3);assert.equal(g.chooseUpgrade(id),true);assert.equal(g.player.hp,id==='heart'?5:4);assert.equal(g.chooseUpgrade(id),false);}
 }
 assert.equal(g.state,'won');assert.equal(g.loadout.length,ROOMS.length-1);assert.ok(g.stats.kills>=ROOMS.reduce((n,r)=>n+r.types.length,0));
});
test('pause freezes simulation; death prevents firing; restart owns fresh state',()=>{
 const g=new Game({seed:11});g.start();g.player.ammo=80;g.togglePause();const before=JSON.stringify(g.summary()),x=g.player.x;
 advance(g,2,{x:1,fire:true});assert.equal(JSON.stringify(g.summary()),before);assert.equal(g.player.x,x);
 g.togglePause();g.player.hp=1;g.player.invincible=0;g.hurtPlayer();assert.equal(g.state,'lost');assert.equal(g.fire(),false);
 g.reset(14);assert.equal(g.state,'ready');assert.equal(g.stats.hits,0);assert.equal(g.stats.shots,0);assert.equal(g.journal.length,0);assert.equal(g.hostileShots.length,0);assert.equal(g.loadout.length,0);assert.equal(g.player.hp,5);
});
test('large update gaps are capped and player stays inside room',()=>{
 const g=new Game({seed:5,width:600,height:800});g.start();const x=g.player.x;g.update(200,{x:1});assert.ok(g.player.x-x<10);
 advance(g,4,{x:-1,y:-1});assert.ok(g.player.x>=42&&g.player.y>=42);
});

test('wide and power upgrades modify distinct mechanics and persist to next room',()=>{
 for(const id of ['wide','power']){
  const g=new Game({seed:8});g.start();while(g.aliveCount){for(const e of g.enemies)g.hitEnemy(e,999);g.resolveDeaths();}advance(g,1.8);
  g.offers=[id];const before={...g.mods};assert.equal(g.chooseUpgrade('unknown'),false);assert.equal(g.chooseUpgrade(id),true);
  if(id==='wide'){assert.ok(g.mods.range>before.range);assert.ok(g.mods.suction>before.suction);assert.equal(g.mods.power,before.power);}
  else{assert.ok(g.mods.power>before.power);assert.equal(g.mods.range,before.range);}
  assert.equal(g.room,2);assert.deepEqual(g.loadout,[id]);
 }
});

test('90 percent cleanliness wins with enemies alive and does not count them as kills',()=>{
 const g=new Game({seed:31});g.start();g.player.x=42;g.player.y=42;g.dirt.fill(.1001);
 g.update(.000001,{angle:Math.PI});assert.equal(g.state,'playing');assert.equal(g.cleanPercent,89);
 const remaining=g.aliveCount;g.dirt.fill(.1);g.update(.000001,{angle:Math.PI});
 assert.equal(g.state,'clearing');assert.equal(g.clearReason,'clean');assert.equal(g.stats.kills,0);
 assert.equal(g.roomResults[0].remaining,remaining);assert.equal(g.roomResults[0].reason,'clean');
 advance(g,1.8);assert.equal(g.state,'upgrade');assert.equal(g.cleanPercent,100);assert.equal(g.roomResults.length,1);
});
test('generated rooms never start near the cleanliness victory threshold',()=>{
 for(let seed=0;seed<20;seed++)for(let room=1;room<=ROOMS.length;room++){
  const g=new Game({seed});g.room=room;g.setupRoom();assert.ok(g.cleanExact<=75);assert.ok(g.aliveCount>0);
 }
});
test('three starter weapons have different ammo and projectile behavior',()=>{
 for(const [weapon,bullets,remaining]of [['pressure',1,0],['scatter',3,0],['foam',1,80]]){
  const g=new Game({seed:9,weapon});g.start();g.player.ammo=100;assert.equal(g.fire(),true);
  assert.equal(g.shots.length,bullets);assert.equal(g.player.ammo,remaining);assert.equal(g.shots[0].weapon,weapon);
  if(weapon==='scatter')assert.notEqual(g.shots[0].vy,g.shots[1].vy);
 }
});
test('splitter produces two children and each enemy has a unique id',()=>{
 const g=new Game({seed:7});g.start();g.enemies=[];const e=g.spawnEnemy('splitter',200,200);
 g.hitEnemy(e,999);g.resolveDeaths();assert.equal(g.stats.kills,1);assert.equal(g.aliveCount,2);
 assert.equal(new Set(g.enemies.map(e=>e.id)).size,3);
});
test('foam cleans ground, pierce does not hit the same target twice, and bounce survives a wall',()=>{
 const g=new Game({seed:4,weapon:'foam'});g.start();g.paint(700,200,45);g.addFoam(700,200);
 g.update(1/60);assert.equal(g.dirt[10*g.cols+35],0);
 g.enemies=[];g.dirt.fill(.5);g.player.x=100;g.player.y=300;const e=g.spawnEnemy('boss',185,300);e.speed=0;
 g.mods.pierce=2;g.player.ammo=100;g.player.angle=0;g.fire();advance(g,.12,{angle:Math.PI});
 const total=e.hp+e.armor;advance(g,.03,{angle:Math.PI});assert.equal(e.hp+e.armor,total);
 const h=new Game({seed:2});h.start();h.player.x=h.width-60;h.player.angle=0;h.mods.bounces=1;h.player.ammo=40;h.fire();
 h.update(1/60,{angle:0});assert.ok(h.shots[0].vx<0);assert.equal(h.shots[0].bounces,0);
});
test('capacity and refund upgrades apply without negative or overflowing ammo',()=>{
 const g=new Game({seed:12});g.state='upgrade';g.offers=['battery'];g.chooseUpgrade('battery');assert.equal(g.mods.capacity,140);
 g.state='upgrade';g.offers=['recycle'];g.chooseUpgrade('recycle');g.player.ammo=140;g.fire();assert.equal(g.player.ammo,35);
});

test('bubble chain pops once per bubble, frees captives and cleans the impact area',()=>{
 const g=new Game({seed:7,starterGadget:'bubble'});g.start();g.enemies=[];g.mods.bubble=2;
 const e=g.spawnEnemy('blob',300,300);e.hp=e.maxHp=500;e.armor=0;
 g.paint(300,300,100);const b={x:300,y:300,r:23,life:6,popped:false,enemy:e},b2={x:345,y:300,r:23,life:6,popped:false,enemy:null};
 g.gadgets.bubbles=[b,b2];g.gadgets.pop(b);g.gadgets.pop(b);
 assert.equal(g.stats.bubblePops,2);assert.equal(e.hp,436);assert.equal(g.dirt[15*g.cols+15],0);
 g.gadgets.update(1/60);assert.equal(e.trapped,false);assert.equal(g.gadgets.bubbles.length,0);
});
test('electricity traverses connected foam, hits each enemy once and does not jump a gap',()=>{
 const g=new Game({seed:8});g.start();g.enemies=[];g.player.x=100;g.player.y=200;g.mods.electric=1;
 for(const x of [200,300,400,750])g.addFoam(x,200);
 const near=g.spawnEnemy('blob',400,200),far=g.spawnEnemy('blob',750,200);near.armor=far.armor=0;near.hp=far.hp=100;
 g.gadgets.discharge();assert.equal(near.hp,78);assert.equal(far.hp,100);assert.equal(g.stats.conducted,3);
});
test('mop redirects a shot once; repeated contact cannot multiply its damage again',()=>{
 const g=new Game({seed:8});g.start();g.enemies=[];g.mods.mop=1;const p=g.player;
 const shot={x:p.x+60,y:p.y,life:2,r:12,damage:40,vx:100,vy:0,bounces:0};g.shots=[shot];
 g.gadgets.update(.001);assert.equal(shot.relayed,true);assert.equal(shot.damage,54);assert.equal(shot.bounces,1);
 g.gadgets.update(.001);assert.equal(shot.damage,54);assert.equal(g.stats.relays,1);
});
test('duck collects dirt into bounded ammo and transports bubbles toward enemies',()=>{
 const g=new Game({seed:10});g.start();g.enemies=[];g.mods.duck=1;g.player.ammo=0;g.gadgets.timer.duck=0;
 const d=g.gadgets.duck;g.paint(d.x,d.y,40);g.gadgets.update(.01);assert.ok(g.player.ammo>0);assert.ok(g.stats.duckCleaned>0);
 const b={x:d.x+10,y:d.y,r:23,life:5,popped:false,enemy:null,vx:0,vy:0};g.gadgets.bubbles=[b];g.spawnEnemy('blob',b.x+180,b.y);const x=b.x;
 g.gadgets.update(.02);assert.ok(b.x>x);assert.ok(g.player.ammo<=g.mods.capacity);
});
test('new equipment caps, partner offers, pause and restart preserve ownership',()=>{
 const g=new Game({seed:11,starterGadget:'bubble'});g.start();g.state='upgrade';g.rollOffers();assert.ok(g.offers.includes('duck'));
 assert.ok(g.chooseUpgrade('duck'));assert.equal(g.mods.duck,1);assert.equal(g.mods.bubble,1);
 g.mods.duck=3;for(let i=0;i<10;i++){g.rollOffers();assert.ok(!g.offers.includes('duck'));}
 g.state='playing';g.gadgets.bubbles.push({x:200,y:200,r:23,life:4});g.togglePause();const before=JSON.stringify(g.gadgets.bubbles);g.update(.02);assert.equal(JSON.stringify(g.gadgets.bubbles),before);
 g.reset();assert.equal(g.gadgets.bubbles.length,0);assert.equal(g.mods.duck,0);assert.equal(g.mods.bubble,1);
});

test('double mouth trades reach for rear suction; compressor changes fire cadence and projectile',()=>{
 const g=new Game({seed:9});g.start();const p=g.player;p.angle=0;
 assert.equal(g.inCone(p.x-80,p.y),false);g.mods.doublemouth=1;assert.equal(g.inCone(p.x-80,p.y),true);assert.equal(g.inCone(p.x+160,p.y),false);
 p.ammo=80;g.mods.compressor=1;g.fire();assert.equal(g.shots[0].pierce,2);assert.ok(g.shots[0].r>25);assert.ok(Math.abs(g.shotCooldown-.72)<1e-9);
});
test('returning projectile refunds only once and never overflows the ammo cap',()=>{
 const g=new Game({seed:10});g.start();g.mods.returner=1;g.player.ammo=80;g.fire();const s=g.shots[0];assert.equal(s.returnValue,20);
 s.life=1;s.x=g.player.x;s.y=g.player.y;g.update(1/60);assert.equal(g.stats.returns,1);assert.equal(g.shots.length,0);
 g.update(1/60);assert.equal(g.stats.returns,1);assert.ok(g.player.ammo<=g.mods.capacity);
});
test('bucket relocation conserves outstanding dirt, then a shot completes collection',()=>{
 const g=new Game({seed:11});g.start();g.enemies=[];g.mods.bucket=1;g.player.x=100;g.player.y=100;g.player.angle=Math.PI;
 g.dirt.fill(0);g.paint(350,300,50);g.gadgets.timer.bucket=100;
 const b={x:350,y:300,life:8,pulse:0,stored:0};g.gadgets.buckets=[b];const before=g.cleanExact;g.gadgets.update(.01);
 assert.ok(b.stored>0);assert.ok(Math.abs(g.cleanExact-before)<.0001);assert.equal(g.stats.cleaned,0);
 g.shots=[{x:350,y:300,r:10,life:1}];g.gadgets.update(.01);assert.equal(b.stored,0);assert.equal(g.cleanExact,100);assert.ok(g.stats.bucketRecovered>0);
});
test('bucket cargo stays dirty while packed and is accounted once when its bubble pops',()=>{
 const g=new Game({seed:11});g.start();g.enemies=[];g.mods.bucket=1;g.mods.bubble=1;g.gadgets.timer.bucket=100;g.gadgets.timer.bubble=100;
 g.dirt.fill(0);g.gadgets.buckets=[{x:350,y:300,life:8,pulse:10,stored:12}];g.gadgets.makeBubble(350,300,0);const before=g.cleanExact;
 g.gadgets.update(.01);const b=g.gadgets.bubbles[0];assert.equal(b.cargo,12);assert.equal(g.cleanExact,before);
 g.gadgets.pop(b);g.gadgets.pop(b);assert.equal(g.cleanExact,100);assert.equal(g.stats.cleaned,12);
});
test('brush carries foam; evolved washing creates trails without preexisting foam',()=>{
 const g=new Game({seed:12});g.start();g.enemies=[];g.mods.brush=1;g.gadgets.timer.brush=100;
 const d={x:400,y:300,vx:0,vy:0,life:6,wet:0,trail:0,hitTimer:0};g.gadgets.discs=[d];g.addFoam(400,300);g.gadgets.update(.01);assert.ok(d.wet>0);assert.ok(g.stats.foamTrails>0);
 g.foam=[];d.wet=0;d.trail=0;g.mods.brush=2;g.mods.electric=2;g.gadgets.update(.01);assert.ok(g.foam.length>0);
});
test('preview kits persist on restart and leave no effects when returning to normal',()=>{
 const g=new Game({seed:12,starterGadget:'bubble'});assert.ok(g.selectPreset('transport'));assert.equal(g.mods.duck,2);assert.equal(g.mods.backpack,1);
 g.reset();assert.equal(g.mods.duck,2);g.selectPreset('normal');assert.equal(g.mods.duck,0);assert.equal(g.mods.bubble,1);assert.equal(g.gadgets.discs.length,0);
});
test('backpack converts some suction yield to bubbles without starving all ammo',()=>{
 const g=new Game({seed:13});g.start();g.mods.backpack=1;g.player.x=400;g.player.y=300;g.player.angle=0;g.player.ammo=0;g.paint(475,300,70);
 for(let i=0;i<25;i++)g.update(1/60,{angle:0});assert.ok(g.gadgets.bubbles.length>0);assert.ok(g.player.ammo>0);
});

test('charged duck delivery evolves only at required levels and combo effects reset',()=>{
 const g=new Game({seed:14});g.selectPreset('transport');g.start();g.enemies=[];g.gadgets.timer.bubble=100;g.gadgets.timer.electric=100;
 const d=g.gadgets.duck;g.gadgets.makeBubble(d.x,d.y,0);g.gadgets.update(.01);const b=g.gadgets.bubbles[0];assert.ok(b.charged);g.gadgets.pop(b);assert.equal(g.stats.chargedPops,1);
 g.mods.duck=1;g.gadgets.bubbles=[];g.gadgets.makeBubble(d.x,d.y,0);g.gadgets.update(.01);assert.equal(g.gadgets.bubbles[0].charged,undefined);
 g.reset();assert.equal(g.gadgets.bubbles.length,0);assert.equal(g.gadgets.buckets.length,0);
});
test('rule modification cards are unique and never appear again once owned',()=>{
 const g=new Game({seed:15});g.state='upgrade';g.offers=['compressor'];assert.ok(g.chooseUpgrade('compressor'));assert.equal(g.mods.compressor,1);
 for(let i=0;i<20;i++){g.rollOffers();assert.ok(!g.offers.includes('compressor'));assert.equal(new Set(g.offers).size,g.offers.length);}
});

test('charger locks its warning direction, dashes across it and is interrupted by bubbles',()=>{
 const g=new Game({seed:81});g.start();g.enemies=[];g.dirt.fill(1);g.player.x=700;g.player.y=300;
 const e=g.spawnEnemy('charger',300,300);e.attack=0;g.update(1/60,{angle:0});assert.ok(e.windup>0);assert.equal(e.chargeAngle,0);
 g.player.y=450;advance(g,.9,{angle:0});assert.ok(e.dash>0);assert.equal(e.chargeAngle,0);const x=e.x;advance(g,.1,{angle:0});assert.ok(e.x>x+25);
 g.gadgets.makeBubble(e.x,e.y,0);g.update(1/60);assert.equal(e.dash,0);assert.equal(e.windup,0);
});
test('lobber snapshots a delayed landing; moving away avoids damage, standing still takes one hit',()=>{
 for(const dodge of [false,true]){
  const g=new Game({seed:82});g.start();g.enemies=[];g.dirt.fill(1);g.player.invincible=0;
  const e=g.spawnEnemy('lobber',100,100);e.attack=0;g.update(1/60,{angle:0});const h=g.hazards[0];assert.ok(h);assert.equal(g.player.hp,5);
  const target={x:h.x,y:h.y};if(dodge)g.player.x+=180;
  advance(g,1.2,{angle:0});assert.equal(g.hazards.length,0);assert.equal(g.player.hp,dodge?5:4);
  assert.ok(g.dirt[Math.floor(target.y/20)*g.cols+Math.floor(target.x/20)]>0);
 }
});
test('mender repairs living nearby shells, cannot exceed cap or resurrect enemies',()=>{
 const g=new Game({seed:83});g.start();g.enemies=[];g.dirt.fill(1);g.player.x=800;
 const healer=g.spawnEnemy('mender',200,200),near=g.spawnEnemy('blob',250,200),far=g.spawnEnemy('blob',600,200),dead=g.spawnEnemy('blob',260,200);
 near.armor=20;far.armor=2;dead.alive=false;dead.armor=0;healer.attack=0;g.update(1/60,{angle:0});
 assert.equal(near.armor,24);assert.equal(far.armor,2);assert.equal(dead.armor,0);assert.equal(dead.alive,false);
});
test('foam charges a manual garbage shot once and impact carries foam onward',()=>{
 const g=new Game({seed:84});g.start();g.enemies=[];g.dirt.fill(1);g.player.x=400;g.player.y=300;g.player.angle=0;g.player.ammo=100;
 const e=g.spawnEnemy('boss',580,300);e.speed=0;g.addFoam(455,300);g.fire();const shot=g.shots[0],damage=shot.damage;
 advance(g,.1,{angle:0});assert.ok(shot.foamBoosted);assert.equal(shot.damage,damage*1.25);assert.equal(g.stats.foamShots,1);
 advance(g,.15,{angle:0});assert.equal(g.stats.foamShots,1);assert.ok(g.foam.some(f=>f.x>500));
});
test('both victory routes cancel pending landings and restart leaves no hazards',()=>{
 for(const reason of ['combat','clean']){const g=new Game({seed:85});g.start();g.hazards.push({x:400,y:300,r:48,life:.1});g.finishRoom(reason);assert.equal(g.hazards.length,0);advance(g,2);assert.equal(g.state,'upgrade');g.reset();assert.equal(g.hazards.length,0);}
});

test('commission layouts differ and fit landscape and portrait arenas',()=>{
 for(const [width,height]of [[960,600],[600,800]]){const g=new Game({width,height,seed:90});let previous='';for(let room=1;room<=4;room++){g.room=room;g.setupRoom();assert.ok(g.cleanExact<75);const layout=g.enemies.map(e=>[e.x,e.y]);assert.notEqual(JSON.stringify(layout),previous);previous=JSON.stringify(layout);assert.ok(g.enemies.every(e=>e.x>40&&e.x<width-40&&e.y>40&&e.y<height-40));}}
});
test('tea-party boss telegraphs bounded mud landings and remains defeatable',()=>{
 const g=new Game({seed:91});g.room=4;g.setupRoom();g.start();g.enemies=[];g.dirt.fill(1);const boss=g.spawnEnemy('boss',300,180);boss.bucketTimer=0;g.update(1/60,{angle:0});assert.equal(g.hazards.length,6);assert.ok(g.hazards.every(h=>h.life>1));g.hitEnemy(boss,999);g.resolveDeaths();g.update(1/60);assert.equal(g.clearReason,'combat');assert.equal(g.hazards.length,0);
});
