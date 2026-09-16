// Scripted controls, not human playtesting. No forced kills, HP, dirt or upgrades.
import {Game} from '../src/engine.js';
import {writeFileSync} from 'node:fs';
const results=[];
for(const seed of [21,42,63])for(const preset of ['normal','wash','transport','pinball','recycle']){
 const g=new Game({seed,starterGadget:'bubble'});g.selectPreset(preset);g.start();
 for(let i=0;i<60*900&&!['won','lost'].includes(g.state);i++){
  if(g.state==='upgrade'){
   const id=['chain','power','wide','electric','mop','brush','duck','bubble','heart'].find(id=>g.offers.includes(id))||g.offers[0];g.chooseUpgrade(id);
  }
  const p=g.player,e=g.enemies.filter(e=>e.alive).sort((a,b)=>Math.hypot(a.x-p.x,a.y-p.y)-Math.hypot(b.x-p.x,b.y-p.y))[0];
  let x=0,y=0,angle=p.angle;
  if(e){const dx=e.x-p.x,dy=e.y-p.y,d=Math.hypot(dx,dy)||1;angle=Math.atan2(dy,dx);const move=d>150?1:d<105?-1:0;x=dx/d*move;y=dy/d*move;}
  for(const h of g.hazards){const dx=p.x-h.x,dy=p.y-h.y,d=Math.hypot(dx,dy);if(d<h.r+50){x+=(d?dx/d:1)*1.5;y+=d?dy/d:0;}}
  if(p.x<90)x=Math.max(x,.8);if(p.x>g.width-90)x=Math.min(x,-.8);if(p.y<90)y=Math.max(y,.8);if(p.y>g.height-90)y=Math.min(y,-.8);
  g.update(1/60,{x,y,angle,fire:p.ammo>=(g.roomTime>25?20:68)});g.drainEvents();
 }
 results.push({seed,preset,...g.summary()});
}
writeFileSync(new URL('../artifacts/campaign-v10.json',import.meta.url),JSON.stringify(results,null,2));
console.log(JSON.stringify(results.map(r=>({seed:r.seed,preset:r.preset,state:r.state,room:r.room,seconds:r.seconds,hits:r.stats.hits,foamShots:r.stats.foamShots||0})),null,2));
if(results.some(r=>!['won','lost'].includes(r.state)))throw Error('Campaign did not reach a terminal state');
