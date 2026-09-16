// All opponents are present and vulnerable from the start. No hidden reserves
// or timed spawns can postpone the existing kill-all victory condition.
const pockets=[
  [[.2,.26],[.77,.25],[.67,.72]],
  [[.22,.2],[.78,.25],[.22,.74]],
  [[.18,.3],[.76,.17],[.79,.73]],
  [[.22,.22],[.8,.42],[.23,.76]]
];
export function encounter(room,types,width,height){
  const centers=pockets[(room-5)%pockets.length];
  const extras=Array.from({length:Math.min(8,room-3)},(_,i)=>i%3===0?'runner':'blob');
  return [...types,...extras].map((type,i)=>{
    const group=i%3,rank=Math.floor(i/3),[cx,cy]=centers[group];
    const angle=rank*2.4+room*.4,radius=rank?Math.min(66,24+rank*8):0;
    const x=Math.max(70,Math.min(width-70,cx*width+Math.cos(angle)*radius));
    const y=Math.max(70,Math.min(height-70,cy*height+Math.sin(angle)*radius));
    return {type,x,y,group,anchorX:x,anchorY:y,engaged:false,guarded:true};
  });
}

export function enemyIntent(e,p){
  const dx=p.x-e.x,dy=p.y-e.y,d=Math.hypot(dx,dy)||1;
  if(e.guarded&&!e.engaged){
    if(d<250||e.hp<e.maxHp||e.armor<e.maxArmor)e.engaged=true;
    else return {x:0,y:0,attack:false};
  }
  // A damaged ranged enemy commits to its shot instead of leading
  // the player around the last clean strip forever.
  const ranged=['spitter','lobber','mender','fan'].includes(e.type);
  const move=ranged?(d>210?1:d<115&&e.hp===e.maxHp&&!e.reload?-.45:0):1;
  return {x:dx/d*move,y:dy/d*move,attack:true};
}
