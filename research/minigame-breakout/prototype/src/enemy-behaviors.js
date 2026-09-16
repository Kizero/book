import {updateBoss} from './boss-choreography.js?v=11';
export const SPECIAL_ENEMIES = {
 fan:{hp:48,armor:12,speed:32,r:25},
 charger:{hp:64,armor:18,speed:48,r:23},
 lobber:{hp:52,armor:20,speed:35,r:24},
 mender:{hp:58,armor:30,speed:38,r:24}
};
export function updateSpecial(g,e,dt){
 const p=g.player;
 if(e.type==='boss'&&g.room>=10){updateBoss(g,e,dt);return;}
 if(e.type==='fan'){
  if(e.gust>0){e.gust=Math.max(0,e.gust-dt);const a=e.gustAngle;
   for(const b of [...g.gadgets.bubbles,...g.shots]){const dx=b.x-e.x,dy=b.y-e.y,d=Math.hypot(dx,dy);if(d<235&&d>0&&(dx*Math.cos(a)+dy*Math.sin(a))/d>.65){b.x=Math.max(36,Math.min(g.width-36,b.x+Math.cos(a)*100*dt));b.y=Math.max(36,Math.min(g.height-36,b.y+Math.sin(a)*100*dt));}}
  }else if(e.windup>0){e.windup-=dt;if(e.windup<=0){e.gust=1.2;g.emit('gust',{x:e.x,y:e.y});}}
  else if((e.attack-=dt)<=0){e.gustAngle=Math.atan2(p.y-e.y,p.x-e.x);e.windup=.9;e.attack=3.8;}
 }
 if(e.type==='boss'){
  e.bucketTimer=(e.bucketTimer??2.2)-dt;
  if(e.bucketTimer<=0){
   // Six fixed, readable landing spots leave escape gaps; no invulnerability phase.
   const a=Math.atan2(p.y-e.y,p.x-e.x);
   for(let i=0;i<6&&g.hazards.length<12;i++){
    const angle=a+i*Math.PI/3,x=Math.max(75,Math.min(g.width-75,e.x+Math.cos(angle)*145)),y=Math.max(75,Math.min(g.height-75,e.y+Math.sin(angle)*145));
    g.hazards.push({x,y,r:32,life:1.25,duration:1.25});
   }
   e.bucketTimer=4.5;e.toss=.6;g.emit('bucket-toss',{x:e.x,y:e.y});
  }
  e.toss=Math.max(0,(e.toss||0)-dt);
 }

 if(e.type==='charger'){
  if(e.dash>0){e.dash=Math.max(0,e.dash-dt);return;}
  if(e.windup>0){
   e.windup-=dt;
   if(e.windup<=0){e.dash=.6;g.emit('spit',{x:e.x,y:e.y});}
  }else if((e.attack-=dt)<=0){
   e.chargeAngle=Math.atan2(p.y-e.y,p.x-e.x);e.windup=.85;e.attack=3.4;
  }
 }
 if(e.type==='lobber'&&(e.attack-=dt)<=0){
  // Snapshot the target, never chase the player after showing the warning.
  if(g.hazards.length<12)g.hazards.push({x:p.x,y:p.y,r:48,life:1.15,duration:1.15});
  e.attack=3.8;g.emit('spit',{x:e.x,y:e.y});
 }
 if(e.type==='mender'&&(e.attack-=dt)<=0){
  e.attack=3.6;e.repairFlash=.45;
  for(const friend of g.enemies)if(friend!==e&&friend.alive&&Math.hypot(friend.x-e.x,friend.y-e.y)<145){
   friend.armor=Math.min(friend.maxArmor,friend.armor+12);
  }
 }
 e.repairFlash=Math.max(0,(e.repairFlash||0)-dt);
}
export function updateHazards(g,dt){
 for(const h of g.hazards){
  h.life-=dt;if(h.life>0)continue;
  g.paint(h.x,h.y,h.r,.95);
  if(Math.hypot(g.player.x-h.x,g.player.y-h.y)<h.r+g.player.r)g.hurtPlayer('没躲开落泥');
  g.emit('mud-land',{x:h.x,y:h.y,r:h.r});
 }
 g.hazards=g.hazards.filter(h=>h.life>0);
}
