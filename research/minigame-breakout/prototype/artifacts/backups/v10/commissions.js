// Authored encounter positions are normalized to work in both arena shapes.
export const COMMISSIONS = {
 1:{title:'花园茶会 · 扫开入口',note:'把门口的碎屑卷成一发大弹，给客人留条干净路。',layout:[[.27,.3],[.33,.28],[.3,.38],[.38,.35],[.78,.26]],dirt:[[.3,.34,.22],[.66,.3,.15],[.55,.67,.12]],thanks:'入口干净了，茶会的小路露出来了。'},
 2:{title:'花园茶会 · 两边都热闹',note:'两拨捣蛋鬼守着花圃，先收拾哪一边由你决定。',layout:[[.23,.3],[.3,.37],[.2,.2],[.75,.28],[.8,.42],[.7,.36],[.25,.68]],dirt:[[.25,.35,.2],[.75,.35,.2],[.5,.7,.11]],thanks:'花圃重新亮起来了，蝴蝶也回来了。'},
 3:{title:'花园茶会 · 收拾备餐台',note:'远处的吐泥怪守着两角，分裂怪在中间捣乱。',layout:[[.18,.19],[.27,.35],[.8,.6],[.73,.34],[.5,.27],[.5,.45],[.82,.19],[.2,.62]],dirt:[[.22,.3,.17],[.78,.3,.17],[.5,.4,.18]],thanks:'备餐的地方收拾好了，只剩最后那个大麻烦。'},
 4:{title:'花园茶会 · 赶走翻桶大王',note:'大王会把泥桶甩成一圈！看清落点，空隙里继续吸喷。',layout:[[.5,.23],[.2,.42],[.28,.25],[.76,.3],[.82,.2],[.72,.63],[.18,.65],[.5,.43]],thanks:'茶会可以开场了。这枚叶子徽章，送给今天的清洁员。'}
};
export function loadJournal(storage){
 try{const raw=JSON.parse(storage.getItem('dust-dash-journal')||'{}');return {completed:Array.isArray(raw.completed)?[...new Set(raw.completed.filter(n=>Number.isInteger(n)&&n>=1&&n<=12))]:[],teaParty:raw.teaParty===true};}catch{return {completed:[],teaParty:false};}
}
export function rememberRoom(storage,journal,room){
 const next={completed:[...new Set([...journal.completed,room])],teaParty:journal.teaParty||room===4};
 try{storage.setItem('dust-dash-journal',JSON.stringify(next));}catch{/* Storage may be unavailable; the current session still works. */}
 return next;
}
