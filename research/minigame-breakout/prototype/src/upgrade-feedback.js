export function upgradeFeedback(g,id){
 const level=g.mods[id]||0;
 const pairs={duck:g.mods.bubble?'与泡泡机配合：搬运泡泡，送到怪物身边。':'小鸭会主动找污渍，回收的垃圾补入弹舱。',bubble:g.mods.duck?'与小鸭配合：打包怪物，再把泡泡送出去。':'用垃圾弹击中泡泡，触发爆泡清洁。',electric:g.weapon==='foam'||g.mods.brush?'沿相连泡沫传导，让电弧扫过更远的区域。':'周期电弧清地；泡沫或小鸭能延长它的作用。',mop:'让弹球经过拖把，接力改变方向并增强伤害。',brush:g.weapon==='foam'?'刷盘沾上泡沫后，一路携泡洗地。':'刷盘撞墙折返，可与拖把和泡沫配合。',bucket:g.mods.bubble?'泡泡可以带走桶里的垃圾，再引爆结算。':'向回收桶喷一发，完成打包清理。'};
 return pairs[id]?`${level?'强化已有装备':'加入新装备'} · ${pairs[id]}`:'';
}
