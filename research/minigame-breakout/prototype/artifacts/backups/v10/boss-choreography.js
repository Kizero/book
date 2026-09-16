// Attack phases, not health gates: the boss is always vulnerable and can die
// before finishing a performance. Targets lock before the warning is shown.
const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
export function updateBoss(g,e,dt){
 if(!e.act){e.act='warning';e.actTime=1.1+(e.duet||0)*.8;e.target={x:g.player.x,y:g.player.y};e.chargeAngle=Math.atan2(e.target.y-e.y,e.target.x-e.x);g.log('boss-pattern',{id:e.id,act:e.act});}
 e.actTime-=dt;e.vulnerable=e.act==='rest';
 if(e.act==='roll'){
  const speed=290*(e.slow>0?.65:1);e.x=clamp(e.x+Math.cos(e.chargeAngle)*speed*dt,35+e.r,g.width-35-e.r);e.y=clamp(e.y+Math.sin(e.chargeAngle)*speed*dt,35+e.r,g.height-35-e.r);
  e.toss=.25;
 }
 if(e.actTime>0)return;
 if(e.act==='warning'){e.act='roll';e.actTime=.85;g.emit('boss-roll',{x:e.x,y:e.y});}
 else if(e.act==='roll'){e.act='rest';e.actTime=3;e.nextAct='volley';g.emit('boss-rest',{x:e.x,y:e.y});}
 else if(e.act==='rest'&&e.nextAct==='volley'){
  e.act='volley';e.actTime=1.1;
  const a=Math.atan2(g.player.y-e.y,g.player.x-e.x);
  for(let i=-2;i<=2;i++)g.hostileShots.push({x:e.x,y:e.y,vx:Math.cos(a+i*.32)*175,vy:Math.sin(a+i*.32)*175,r:9,life:3.3});
  const count=e.hp<e.maxHp*.5?4:2;
  for(let i=0;i<count&&g.hazards.length<12;i++){const angle=a+(i-(count-1)/2)*.65;g.hazards.push({x:clamp(e.x+Math.cos(angle)*175,65,g.width-65),y:clamp(e.y+Math.sin(angle)*175,65,g.height-65),r:32,life:1.2,duration:1.2});}
  g.emit('bucket-toss',{x:e.x,y:e.y});
 }else if(e.act==='volley'){e.act='rest';e.actTime=2.6;e.nextAct='warning';g.emit('boss-rest',{x:e.x,y:e.y});}
 else {e.act='warning';e.actTime=1.1;e.target={x:g.player.x,y:g.player.y};e.chargeAngle=Math.atan2(e.target.y-e.y,e.target.x-e.x);}
 g.log('boss-pattern',{id:e.id,act:e.act});
}
export const BOSS_ACT_NAMES={warning:'预告 · 滚桶路线',roll:'滚桶冲锋',rest:'喘气 · 连携伤害提升',volley:'扇形撒泥'};
