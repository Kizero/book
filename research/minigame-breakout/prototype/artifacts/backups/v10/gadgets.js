import {updateExtras,evolved,availableEvolutions} from './combinations.js?v=10';
// Bounded, run-owned companion systems. Secondary effects never recursively
// trigger themselves; bubble chains use a queue and electric hits are deduped.
export const GADGETS=['bubble','electric','mop','duck','brush','bucket'];
export const SYNERGIES=[
 {name:'携泡刷盘',needs:['brush','foam'],description:'刷盘穿过泡沫后沿路铺开泡沫。'},
 {name:'垃圾打包站',needs:['bucket','bubble'],description:'回收桶收拢垃圾，泡泡打包后被弹球引爆。'},
 {name:'泡泡搬运队',needs:['bubble','duck'],description:'小鸭把泡泡送向怪群，弹球引发连环清洁。'},
 {name:'电动洗地',needs:['electric','foam'],description:'电弧沿相连泡沫传开，每次放电同一只怪只受击一次。'},
 {name:'旋转接球',needs:['mop'],description:'拖把接住弹球再击出；每颗弹球最多接力一次。'},
 {name:'雷电小鸭',needs:['electric','duck'],description:'小鸭成为远处的放电中继点。'}
];
const dist=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y);
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
export function activeSynergies(g){return SYNERGIES.filter(s=>s.needs.every(id=>id==='foam'?g.weapon==='foam':g.mods[id]>0)).concat(availableEvolutions(g));}
export class Gadgets {
 constructor(g){this.g=g;this.reset();}
 reset(){this.bubbles=[];this.arcs=[];this.pops=[];this.discs=[];this.buckets=[];this.timer={brush:.6,bucket:.3,bubble:.4,electric:.8,duck:.5};this.phase=0;this.duck={x:this.g.player.x-38,y:this.g.player.y+28};this.serial=0;}
 get pendingDirt(){return this.buckets.reduce((n,b)=>n+b.stored,0)+this.bubbles.reduce((n,b)=>n+(b.popped?0:b.cargo||0),0);}
 makeBubble(x,y,angle,cargo=0){if(this.bubbles.length>=12)return false;this.bubbles.push({id:++this.serial,x,y,vx:Math.cos(angle)*65,vy:Math.sin(angle)*65,r:23,life:6,popped:false,enemy:null,cargo});return true;}
 pop(first){
  const g=this.g,queue=[first];while(queue.length){const b=queue.shift();if(b.popped)continue;b.popped=true;g.stats.cleaned+=b.cargo||0;b.cargo=0;
   const r=62+g.mods.bubble*10;g.clearArea(b.x,b.y,r);this.pops.push({x:b.x,y:b.y,r,life:.45});
   for(const e of g.enemies)if(e.alive&&dist(b,e)<r+e.r)g.hitEnemy(e,16+8*g.mods.bubble,'bubble');
   for(const other of this.bubbles)if(!other.popped&&dist(b,other)<r)queue.push(other);
   if(b.charged){for(const e of g.enemies)if(e.alive&&dist(b,e)<r*1.6){g.hitEnemy(e,22,'charged-bubble');e.slow=1;this.arcs.push({a:{x:b.x,y:b.y},b:{x:e.x,y:e.y},life:.3});}g.stats.chargedPops=(g.stats.chargedPops||0)+1;}
   g.emit('bubble-pop',{x:b.x,y:b.y});g.stats.bubblePops=(g.stats.bubblePops||0)+1;
  }
  if(this.pops.length>24)this.pops.splice(0,this.pops.length-24);
 }
 discharge(){
  this.pops.push({x:this.g.player.x,y:this.g.player.y,r:115,life:.4});
  const g=this.g,origins=[g.player],visited=new Set(),targets=new Set();if(g.mods.duck)origins.push(this.duck);
  for(let i=0;i<origins.length;i++){
   const origin=origins[i],range=i<(g.mods.duck?2:1)?115:origin.r+12;
   g.clearArea(origin.x,origin.y,range*.55);
   for(const f of g.foam)if(!visited.has(f)&&dist(origin,f)<range+f.r){visited.add(f);origins.push(f);this.arcs.push({a:{x:origin.x,y:origin.y},b:{x:f.x,y:f.y},life:.3});}
   for(const e of g.enemies)if(e.alive&&!targets.has(e)&&dist(origin,e)<range+e.r){targets.add(e);g.hitEnemy(e,14+8*g.mods.electric,'electric');e.slow=Math.max(e.slow,.7);this.arcs.push({a:{x:origin.x,y:origin.y},b:{x:e.x,y:e.y},life:.3});}
  }
  this.arcs=this.arcs.slice(-60);g.stats.conducted=(g.stats.conducted||0)+visited.size;g.stats.electricHits=(g.stats.electricHits||0)+targets.size;g.emit('electric',{x:g.player.x,y:g.player.y,nodes:visited.size,targets:targets.size});
 }
 update(dt){
  const g=this.g,p=g.player;this.phase+=dt*3.5;
  this.arcs=this.arcs.filter(a=>(a.life-=dt)>0);this.pops=this.pops.filter(a=>(a.life-=dt)>0);
  for(const key of Object.keys(this.timer))this.timer[key]-=dt;
  if(g.mods.bubble&&this.timer.bubble<=0){
   this.timer.bubble=2.7-g.mods.bubble*.35;
   const a=p.angle;this.makeBubble(p.x+Math.cos(a)*55,p.y+Math.sin(a)*55,a);
  }
  updateExtras(this,dt);
  for(const e of g.enemies)e.trapped=false;
  for(const b of this.bubbles){
   b.life-=dt;if(b.popped)continue;
   if(b.enemy&&!b.enemy.alive)b.enemy=null;
   if(!b.enemy){const e=g.enemies.find(e=>e.alive&&!e.trapped&&e.type!=='boss'&&dist(e,b)<e.r+b.r);if(e)b.enemy=e;}
   if(b.enemy)b.enemy.trapped=true;
   let vx=b.vx,vy=b.vy;
   if(g.mods.duck&&dist(this.duck,b)<100){if(evolved(g,'stormduck'))b.charged=true;const target=g.enemies.find(e=>e.alive&&!e.trapped);if(target){const d=dist(target,b)||1;vx=(target.x-b.x)/d*80;vy=(target.y-b.y)/d*80;}}
   else if(g.inCone(b.x,b.y)){const d=dist(p,b)||1;vx=(p.x-b.x)/d*45;vy=(p.y-b.y)/d*45;}
   b.x=clamp(b.x+vx*dt,42,g.width-42);b.y=clamp(b.y+vy*dt,42,g.height-42);
   if(b.enemy){b.enemy.x=b.x;b.enemy.y=b.y;}
   g.clearArea(b.x,b.y,14);
   if(g.shots.some(s=>s.life>0&&dist(s,b)<s.r+b.r))this.pop(b);
   if(b.life<=0&&!b.popped&&(b.cargo>0||b.charged))this.pop(b);
   if(b.life<=0&&!b.popped){if(b.enemy)b.enemy.trapped=false;b.popped=true;}
  }
  this.bubbles=this.bubbles.filter(b=>!b.popped);
  // Release popped captives in the same frame.
  for(const e of g.enemies)e.trapped=this.bubbles.some(b=>b.enemy===e);
  if(g.mods.mop){
   const m={x:p.x+Math.cos(this.phase)*60,y:p.y+Math.sin(this.phase)*60};this.mop=m;g.clearArea(m.x,m.y,25+g.mods.mop*4);
   for(const e of g.enemies)if(e.alive&&dist(e,m)<e.r+22){g.hitEnemy(e,(12+g.mods.mop*5)*dt,'mop');e.knockX+=(e.x-p.x)*dt*4;e.knockY+=(e.y-p.y)*dt*4;}
   for(const s of g.shots)if(s.life>0&&!s.relayed&&dist(s,m)<s.r+28){
    s.relayed=true;const a=this.phase+Math.PI/2;s.vx=Math.cos(a)*700;s.vy=Math.sin(a)*700;s.life=Math.max(s.life,1.5);s.damage*=1.35;s.bounces=Math.max(s.bounces,1);
    g.stats.relays=(g.stats.relays||0)+1;g.emit('relay',{x:m.x,y:m.y});this.pops.push({x:m.x,y:m.y,r:30,life:.25});
   }
  }
  if(g.mods.duck){
   let target=this.bubbles.find(b=>dist(b,p)<220)||p,best=0;
   if(target===p)for(let row=3;row<g.rows-3;row+=2)for(let col=3;col<g.cols-3;col+=2){const q={x:col*20+10,y:row*20+10},value=g.dirt[row*g.cols+col]/(dist(this.duck,q)+40);if(dist(q,p)<190&&value>best){best=value;target=q;}}
   const d=dist(this.duck,target)||1,step=Math.min(d,dt*160);this.duck.x+=(target.x-this.duck.x)/d*step;this.duck.y+=(target.y-this.duck.y)/d*step;
   if(this.timer.duck<=0){this.timer.duck=.7;const collected=g.clearArea(this.duck.x,this.duck.y,20+g.mods.duck*5);p.ammo=Math.min(g.mods.capacity,p.ammo+collected*2);g.stats.duckCleaned=(g.stats.duckCleaned||0)+collected;}
  }
  if(g.mods.electric&&this.timer.electric<=0){this.timer.electric=2.3-g.mods.electric*.25;this.discharge();}
 }
}
