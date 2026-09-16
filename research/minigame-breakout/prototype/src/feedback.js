import {BOSS_ACT_NAMES} from './boss-choreography.js?v=11';
const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
// Presentation owns its timing. No damage, upgrades or enemy state changes here.
export class Feedback {
 constructor(){this.reset();}
 reset(){this.time=0;this.lastKill=-9;this.streak=0;this.labels=[];this.flashes=[];this.clearAge=-1;this.full=false;this.chargePulse=0;this.cooldowns={};}
 say(key,text,x,y,color='#fff3cb'){
  if((this.cooldowns[key]||0)>this.time)return;this.cooldowns[key]=this.time+1.2;
  const nearby=this.labels.filter(l=>Math.abs(l.x-x)<150&&Math.abs(l.y-y)<70).length;y-=nearby*25;this.labels.push({text,x,y,life:1.15,color});if(this.labels.length>5)this.labels.shift();
 }
 event(e,g){
  if(e.type==='room'){this.reset();if(g.room===4)this.say('boss','翻桶大王来了',g.width/2,115,'#ffe1a0');}
  if(e.type==='hurt')this.say('hurt',e.source||'受伤了',e.x,e.y-48,'#ffd0c2');
  if(e.type==='electric'&&e.nodes>1&&e.targets>0)this.say('electric',`导电连携 · ${e.targets} 只`,e.x,e.y-44,'#d7ffff');
  if(e.type==='clear'){this.clearAge=0;this.labels=[];}
  if(e.type==='fire'){this.chargePulse=0;this.flashes.push({x:e.x+Math.cos(e.angle)*38,y:e.y+Math.sin(e.angle)*38,angle:e.angle,life:.14,large:e.amount>=80});}
  if(e.type==='burst'){
   this.streak=this.time-this.lastKill<.65?this.streak+1:1;this.lastKill=this.time;
   if(this.streak>=2){this.labels=this.labels.filter(l=>!l.streak);this.labels.push({text:`连续清除 ×${this.streak}`,x:e.x,y:e.y-35,life:1.15,color:'#fff1a8',streak:true});}
  }
  const names={'wash-trigger':['落点放电','#d7ffff'],'delivery':['泡泡出发','#fff0b8'],'return-catch':['接住了 · 下一发更强','#ffe1a0'],'catch-shot':['回收强化弹','#ffe1a0'],'parcel-open':['回收包打开 · 补弹！','#fff0b8'],'boss-rest':['喘气了，放开喷！','#ffeab4'],'gust':['风向锁定','#d0f4ff'],'foam-boost':['泡沫裹弹','#d7ffff'],'relay':['拖把接力','#e5f5b5'],'bubble-pop':['爆泡清洁','#c5f3ff'],'bucket-toss':['泥桶要翻啦！','#ffe1a0']};
  if(names[e.type])this.say(e.type,...[names[e.type][0],e.x??g.player.x,(e.y??g.player.y)-35,names[e.type][1]]);
 }
 update(dt,g){
  if(g.state==='paused')return;
  this.time+=dt;if(this.clearAge>=0)this.clearAge+=dt;
  const full=g.player.ammo>=(g.weapon==='foam'?20:g.mods.capacity*.8);
  if(full&&!this.full&&g.state==='playing'){this.chargePulse=1;this.say('loaded',g.weapon==='foam'?'泡沫就绪':'大弹就绪',g.player.x,g.player.y-62,'#fff0a6');}
  this.full=full;this.chargePulse=Math.max(0,this.chargePulse-dt*1.5);
  for(const l of this.labels)l.life-=dt;for(const f of this.flashes)f.life-=dt;
  this.labels=this.labels.filter(l=>l.life>0);this.flashes=this.flashes.filter(f=>f.life>0);
 }
 draw(c,g){
  c.save();
  const bosses=g.enemies.filter(e=>e.type==='boss'&&e.alive),boss=bosses.length?{hp:bosses.reduce((n,e)=>n+e.hp,0),maxHp:bosses.reduce((n,e)=>n+e.maxHp,0),armor:bosses.reduce((n,e)=>n+e.armor,0),maxArmor:bosses.reduce((n,e)=>n+e.maxArmor,0)}:null;
  if(boss){const x=g.width/2;c.fillStyle='#fff7e8ed';c.beginPath();c.roundRect(x-108,40,216,46,12);c.fill();c.font='bold 13px system-ui';c.textAlign='center';c.fillStyle='#674c36';c.fillText(BOSS_ACT_NAMES[['warning','roll','volley','rest'].find(act=>bosses.some(e=>e.act===act))]||(bosses.length>1?'双倍捣蛋 · 翻桶搭档':'翻桶大王'),x,57);c.fillStyle='#d9cbb5';c.fillRect(x-90,66,180,6);c.fillStyle='#c88755';c.fillRect(x-90,66,180*Math.max(0,boss.hp/boss.maxHp),6);if(boss.armor>0){c.fillStyle='#859b76';c.fillRect(x-90,75,180*boss.armor/boss.maxArmor,3);}}
  for(const f of this.flashes){c.save();c.translate(f.x,f.y);c.rotate(f.angle);c.globalAlpha=f.life/.14;c.fillStyle='#fff5c2';c.beginPath();c.moveTo(0,-8);c.lineTo(f.large?56:34,0);c.lineTo(0,8);c.fill();c.restore();}
  const placed=[];
  for(const l of this.labels){
   c.font='bold 17px system-ui';const width=c.measureText(l.text).width+12,x=clamp(l.x,width/2+6,g.width-width/2-6);let y=clamp(l.y-(1.15-l.life)*24,boss?110:45,g.height-60);
   for(let tries=0;tries<7&&placed.some(p=>Math.abs(p.x-x)<(p.width+width)/2&&Math.abs(p.y-y)<24);tries++)y-=25;
   if(y<(boss?100:28))continue;placed.push({x,y,width});c.globalAlpha=Math.min(1,l.life*4);c.textAlign='center';c.lineWidth=4;c.strokeStyle='#38564c';c.strokeText(l.text,x,y);c.fillStyle=l.color;c.fillText(l.text,x,y);
  }
  c.restore();
 }
}
