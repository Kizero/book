export const RULES=['compressor','doublemouth','returner','backpack'];
export const EVOLUTIONS=[
 {id:'stormduck',name:'雷泡运输队',needs:{bubble:2,duck:2,electric:1},description:'喷射会指挥小鸭身边的泡泡向瞄准方向冲出；带电爆泡追加范围电击。'},
 {id:'washstorm',name:'电动洗地风暴',needs:{brush:2,electric:2},description:'刷盘持续铺泡沫；朝泡沫落点喷射可主动放电，沿相连泡沫传导。'},
 {id:'pinball',name:'双盘清扫阵',needs:{brush:2,mop:2},description:'双刷盘接力；非泡沫弹装填 60 以上会回旋，接回后下一发增伤 35%。'}
];
export const PRESETS=[
 {id:'normal',name:'从一件装备成长',weapon:null,levels:{}},
 {id:'transport',name:'雷泡运输队',weapon:'pressure',levels:{bubble:2,duck:2,electric:1,backpack:1}},
 {id:'wash',name:'电动洗地风暴',weapon:'foam',levels:{brush:2,electric:2,bucket:1}},
 {id:'pinball',name:'弹球清扫阵',weapon:'pressure',levels:{brush:2,mop:2,returner:1,compressor:1}},
 {id:'recycle',name:'双向回收站',weapon:'scatter',levels:{bucket:2,bubble:2,duck:1,doublemouth:1,backpack:1}}
];
export function evolved(g,id){const e=EVOLUTIONS.find(e=>e.id===id);return !!e&&Object.entries(e.needs).every(([k,n])=>g.mods[k]>=n);}
export function availableEvolutions(g){return EVOLUTIONS.filter(e=>evolved(g,e.id));}
const dist=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y);
export function updateExtras(fx,dt){
 const g=fx.g,p=g.player;
 if(g.mods.brush&&fx.timer.brush<=0){
  fx.timer.brush=3.3-g.mods.brush*.3;const count=evolved(g,'pinball')?2:1;
  for(let i=0;i<count&&fx.discs.length<8;i++){const a=p.angle+i*Math.PI;fx.discs.push({x:p.x,y:p.y,vx:Math.cos(a)*240,vy:Math.sin(a)*240,life:6,wet:0,trail:0,hitTimer:0});}
 }
 for(const d of fx.discs){
  d.life-=dt;d.wet=Math.max(0,d.wet-dt);d.trail-=dt;d.hitTimer-=dt;
  d.x+=d.vx*dt;d.y+=d.vy*dt;
  if(d.x<44||d.x>g.width-44){d.vx*=-1;d.x=Math.max(44,Math.min(g.width-44,d.x));}
  if(d.y<44||d.y>g.height-44){d.vy*=-1;d.y=Math.max(44,Math.min(g.height-44,d.y));}
  if(g.foam.some(f=>dist(f,d)<f.r))d.wet=2;
  if((d.wet>0||evolved(g,'washstorm'))&&d.trail<=0){d.trail=.4;g.addFoam(d.x,d.y);g.stats.foamTrails=(g.stats.foamTrails||0)+1;}
  g.clearArea(d.x,d.y,23+g.mods.brush*4);
  if(d.hitTimer<=0){d.hitTimer=.3;for(const e of g.enemies)if(e.alive&&dist(e,d)<e.r+23)g.hitEnemy(e,8+g.mods.brush*4,'brush');}
  if(evolved(g,'pinball')&&fx.mop&&!d.relayed&&dist(d,fx.mop)<40){d.relayed=true;d.vx*=1.5;d.vy*=1.5;g.stats.discRelays=(g.stats.discRelays||0)+1;}
 }
 fx.discs=fx.discs.filter(d=>d.life>0);
 if(g.mods.bucket&&fx.timer.bucket<=0){
  fx.timer.bucket=6; if(fx.buckets.length<2)fx.buckets.push({x:Math.max(55,Math.min(g.width-55,p.x+Math.cos(p.angle)*100)),y:Math.max(55,Math.min(g.height-55,p.y+Math.sin(p.angle)*100)),stored:0,life:8,pulse:0});
 }
 for(const bucket of fx.buckets){
  bucket.life-=dt;bucket.pulse-=dt;
  if(bucket.pulse<=0){bucket.pulse=.3;const r=75+g.mods.bucket*12;bucket.stored+=g.clearArea(bucket.x,bucket.y,r,false);}
  const bubble=fx.bubbles.find(b=>!b.popped&&dist(b,bucket)<48);
  if(bubble&&bucket.stored>0){bubble.cargo=(bubble.cargo||0)+bucket.stored;bucket.stored=0;g.stats.packed=(g.stats.packed||0)+1;}
  if(bucket.stored>0&&(g.shots.some(s=>s.life>0&&dist(s,bucket)<s.r+25)||bucket.life<=0||g.inCone(bucket.x,bucket.y)&&dist(p,bucket)<85)){
   g.stats.cleaned+=bucket.stored;p.ammo=Math.min(g.mods.capacity,p.ammo+bucket.stored*1.5);g.stats.bucketRecovered=(g.stats.bucketRecovered||0)+bucket.stored;bucket.stored=0;fx.pops.push({x:bucket.x,y:bucket.y,r:90,life:.45});
  }
 }
 fx.buckets=fx.buckets.filter(b=>b.life>0);
}
