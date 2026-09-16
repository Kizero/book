// Visible authored rules; no player-performance-driven difficulty adjustment.
export const ROOM_FLAVORS=[
 {name:'薄荷晨光',sky:'morning',rule:'入口散叶，练习把吸来的垃圾喷出去。'},
 {name:'花瓣小路',sky:'petals',rule:'两片花圃，可以选一侧先收拾。'},
 {name:'备餐时间',sky:'warm',rule:'回收包可以持续吸开，也能一发打爆，补充弹药。',parcels:1},
 {name:'茶会前夕',sky:'warm',rule:'看清翻桶落点，绕到空隙继续清洁。'},
 {name:'暖房顺风',sky:'morning',rule:'风带会推动泡泡与弹球；借风把连携送远。',wind:1,parcels:2},
 {name:'午后阵雨',sky:'rain',rule:'阵雨只是天气；看橙色落点躲泥桶。回收包会爆出清洁泡沫。',parcels:2},
 {name:'顺风快递',sky:'petals',rule:'借风运泡泡；鼓风怪会预告风向，也能被泡泡打断。',wind:1,parcels:2},
 {name:'雨后回收',sky:'rain',rule:'落泥圈配合鼓风，先找空隙；吸开回收包可以补弹。',wind:-1,parcels:3},
 {name:'开工流水线',sky:'warm',rule:'站上传输带可以顺势移动，弹球和泡泡也会搭顺风车。',belt:1,parcels:3},
 {name:'滚桶大搬家',sky:'warm',rule:'看长条预告躲滚桶冲锋，趁首领喘气集中喷射。',belt:-1,parcels:3},
 {name:'暖房晚风',sky:'evening',rule:'风带与回收包串起三片战区；把泡泡送进远处怪群。',wind:-1,parcels:3},
 {name:'收工庆典',sky:'evening',rule:'双首领轮流滚桶、撒泥；喘气时伤害更高。杀光或清洁达标都算赢。',wind:1,parcels:3}
];
const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
export class RoomFeatures{
 constructor(g){this.g=g;this.flavor=ROOM_FLAVORS[g.room-1];this.parcels=[];this.time=0;
  // Move existing floor dirt into visible sacks. Count it until collected;
  // presentation never creates/destroys hidden dirt to prolong a run.
  for(let i=0;i<(this.flavor.parcels||0);i++){
   const [nx,ny]=[[.17,.24],[.83,.28],[.52,.81]][i],x=nx*g.width,y=ny*g.height;let cargo=0;
   const cells=Array.from(g.dirt.keys()).filter(idx=>{const col=idx%g.cols,row=Math.floor(idx/g.cols);return col>=2&&col<g.cols-2&&row>=2&&row<g.rows-2;}).sort((a,b)=>Math.hypot((a%g.cols)*20-x,Math.floor(a/g.cols)*20-y)-Math.hypot((b%g.cols)*20-x,Math.floor(b/g.cols)*20-y));
   for(const idx of cells){const take=Math.min(g.dirt[idx],Math.max(0,60-cargo));g.dirt[idx]-=take;cargo+=take;if(cargo>=60)break;}
   this.parcels.push({x,y,cargo,progress:0,opened:false,age:0});
  }
 }
 get pendingDirt(){return this.parcels.reduce((n,p)=>n+(p.opened?0:p.cargo),0);}
 get remaining(){return this.parcels.filter(p=>!p.opened).length;}
 open(p){
  if(p.opened)return;p.opened=true;p.age=0;const g=this.g;
  g.stats.cleaned+=p.cargo;g.stats.parcels=(g.stats.parcels||0)+1;
  g.player.ammo=Math.min(g.mods.capacity,g.player.ammo+Math.min(65,p.cargo));p.cargo=0;
  g.clearArea(p.x,p.y,95);g.addFoam(p.x,p.y);
  for(const e of g.enemies)if(e.alive&&Math.hypot(e.x-p.x,e.y-p.y)<110+e.r)g.hitEnemy(e,30,'parcel');
  g.emit('parcel-open',{x:p.x,y:p.y,r:95});g.log('parcel-open');
 }
 update(dt){
  this.time+=dt;const g=this.g,f=this.flavor;
  for(const p of this.parcels){p.age+=dt;if(p.opened)continue;
   if(g.inCone(p.x,p.y))p.progress=Math.min(1,p.progress+dt*g.mods.suction/.85);
   if(p.progress>=1||g.shots.some(s=>s.life>0&&Math.hypot(s.x-p.x,s.y-p.y)<s.r+24))this.open(p);
  }
  const flow=f.wind?{y:g.height*.48,half:48,speed:f.wind*55}:f.belt?{y:g.height*.7,half:40,speed:f.belt*75}:null;
  if(!flow)return;
  for(const e of [...g.shots,...g.gadgets.bubbles,...g.gadgets.discs])if(Math.abs(e.y-flow.y)<flow.half)e.x=clamp(e.x+flow.speed*dt,36,g.width-36);
  if(f.belt&&Math.abs(g.player.y-flow.y)<flow.half)g.player.x=clamp(g.player.x+flow.speed*dt,42,g.width-42);
 }
 finish(){for(const p of this.parcels){p.opened=true;p.cargo=0;} }
}
