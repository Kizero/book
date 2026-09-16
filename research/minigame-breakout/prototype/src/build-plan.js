import {EVOLUTIONS,RULES} from './combinations.js?v=11';
import {UPGRADES} from './content.js?v=11';
export const EQUIPMENT=['bubble','electric','mop','duck','brush','bucket'];
export function buildProgress(g,id){
 const e=EVOLUTIONS.find(e=>e.id===id);if(!e)return null;
 const parts=Object.entries(e.needs).map(([key,need])=>({id:key,name:UPGRADES.find(u=>u.id===key).name,have:Math.min(g.mods[key]||0,need),need}));
 return {...e,parts,missing:parts.reduce((sum,p)=>sum+p.need-p.have,0)};
}
export function upgradeOutcome(g,id){
 const advancing=EVOLUTIONS.map(e=>buildProgress(g,e.id)).filter(e=>e.parts.some(p=>p.id===id&&p.have<p.need));
 const goal=advancing.find(e=>e.id===g.buildGoal)||advancing[0];
 if(goal)return goal.missing===1?`选后成型：${goal.name} · ${goal.description}`:`${goal.name}：选后还差 ${goal.missing-1} 次组件升级`;
 const detail={power:`伤害倍率 ${g.mods.power.toFixed(2)} → ${(g.mods.power*1.35).toFixed(2)}`,battery:`弹舱 ${g.mods.capacity} → ${g.mods.capacity+40}`,wide:`吸入距离 ${g.mods.range} → ${g.mods.range+38}`,chain:`击破范围 ${g.mods.burst} → ${g.mods.burst+38}`,pierce:`穿透 ${g.mods.pierce} → ${g.mods.pierce+1}`,recycle:`弹药返还 ${Math.round(g.mods.refund*100)}% → ${Math.round(Math.min(.5,g.mods.refund+.25)*100)}%`};
 return detail[id]||(EQUIPMENT.includes(id)?`装备 ${g.mods[id]||0} → ${Math.min(3,(g.mods[id]||0)+1)} 级`:'立即改变这局的清洁方式');
}
export function eligibleUpgrades(g){return UPGRADES.filter(u=>!(RULES.includes(u.id)&&g.mods[u.id])&&!(EQUIPMENT.includes(u.id)&&g.mods[u.id]>=3)&&!(u.id==='bounce'&&g.mods.bounces>=2)&&!(u.id==='recycle'&&g.mods.refund>=.5)&&!(u.id==='drone'&&g.mods.drones>=3));}
export function chooseOffers(g,exclude=[]){
 let pool=eligibleUpgrades(g).filter(u=>!exclude.includes(u.id));
 if(pool.length<3)pool=eligibleUpgrades(g);
 for(let i=pool.length-1;i>0;i--){const j=Math.floor(g.random()*(i+1));[pool[i],pool[j]]=[pool[j],pool[i]];}
 const picked=[];
 const take=fn=>{const u=pool.find(u=>!picked.includes(u)&&fn(u));if(u)picked.push(u);};
 // The first reward introduces a partner; later choices mix investment,
 // exploration and utility. Marking a goal never changes RNG or the pool.
 const partner=g.room===1?(g.mods.bubble&&!g.mods.duck?'duck':g.mods.duck&&!g.mods.bubble?'bubble':g.weapon==='foam'&&!g.mods.electric?'electric':null):null;
 take(u=>u.id===partner);
 take(u=>EQUIPMENT.includes(u.id)&&g.mods[u.id]>0);
 if(picked.length<2)take(u=>EQUIPMENT.includes(u.id)&&!g.mods[u.id]&&EVOLUTIONS.some(e=>e.needs[u.id]&&Object.keys(e.needs).some(id=>g.mods[id]>0)));
 if(picked.length<2)take(u=>EQUIPMENT.includes(u.id)&&!g.mods[u.id]);
 if(picked.length<3)take(u=>!EQUIPMENT.includes(u.id));
 while(picked.length<3)take(()=>true);
 return picked.map(u=>u.id);
}
export function renderBuildPlanner(g){
 return `<section class="build-planner" aria-label="本局构筑计划"><div class="planner-heading"><strong>这局想凑什么？</strong><span>标记只作提醒，不改变出牌</span></div><div class="build-routes">${EVOLUTIONS.map(e=>{const p=buildProgress(g,e.id);return `<button data-build="${e.id}" aria-pressed="${g.buildGoal===e.id}" class="build-route ${g.buildGoal===e.id?'selected':''}"><b>${e.name}</b><span>${p.parts.map(x=>`${x.name} ${x.have}/${x.need}`).join(' · ')}</span><small>${p.missing?`还差 ${p.missing} 次组件升级`:'已成型 · 继续强化或尝试另一条路线'}</small></button>`;}).join('')}</div></section>`;
}
