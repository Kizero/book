import {renderBuildPlanner,upgradeOutcome} from './build-plan.js?v=11';
import {renderRunRecap} from './recap.js?v=11';
import {createGameKeyboard} from './keyboard.js?v=11';
import {COMMISSIONS,loadJournal,rememberRoom} from './commissions.js?v=11';
import {CleaningSound} from './sound.js?v=11';
import {PRESETS,EVOLUTIONS} from './combinations.js?v=11';
import {GADGETS,activeSynergies} from './gadgets.js?v=11';
import {Game,UPGRADES,ROOM_NAMES,ROOMS,WEAPONS,CLEAN_TARGET} from './engine.js?v=11';
import {Renderer} from './render.js?v=11';
import {loadAssets} from './assets.js?v=11';
const $=id=>document.getElementById(id);
const mobile=matchMedia('(max-width:560px)').matches;
const game=new Game({starterGadget:'bubble',width:mobile?600:960,height:mobile?800:600});
let assets;try{assets=await loadAssets();}catch(error){$('start').textContent='素材加载失败，请刷新重试';throw error;}
let journal=loadJournal({getItem:k=>localStorage.getItem(k)});
const motorSound=new CleaningSound();
const renderer=new Renderer($('game'),game,assets);
const keys=new Set();let pointer=null,touch=false,stick={x:0,y:0},fireHeld=false,lastState='ready',toastUntil=0,prev=performance.now(),accumulator=0,hudTimer=0;
let audioCtx=null,sound=false;
function tone(freq,duration=.1,type='sine',volume=.025){
  if(!sound)return;try{audioCtx??=new (window.AudioContext||window.webkitAudioContext)();if(audioCtx.state==='suspended')audioCtx.resume();const o=audioCtx.createOscillator(),gain=audioCtx.createGain();o.type=type;o.frequency.setValueAtTime(freq,audioCtx.currentTime);o.frequency.exponentialRampToValueAtTime(Math.max(30,freq*.6),audioCtx.currentTime+duration);gain.gain.setValueAtTime(volume,audioCtx.currentTime);gain.gain.exponentialRampToValueAtTime(.001,audioCtx.currentTime+duration);o.connect(gain);gain.connect(audioCtx.destination);o.start();o.stop(audioCtx.currentTime+duration);}catch{/* sound is optional */}}
function toast(text){$('toast').textContent=text;$('toast').classList.add('visible');toastUntil=performance.now()+2200;}
function clearInput(){keys.clear();fireHeld=false;stick={x:0,y:0};$('stick').style.transform='';}
function begin(){clearInput();game.start();$('overlay').hidden=true;$('game').focus({preventScroll:true});lastState=game.state;tone(530,.15);}
function restart(){clearInput();game.reset(Date.now());renderer.reset();game.start();$('overlay').hidden=true;$('game').focus({preventScroll:true});lastState=game.state;hud();toast('新一轮清洁行动，开工！');}
function weaponChoices(){
  $('weapon-choices').innerHTML=WEAPONS.map(w=>`<button class="weapon-card ${game.weapon===w.id?'selected':''}" data-weapon="${w.id}" aria-pressed="${game.weapon===w.id}"><img class="selected-mark" src="assets/kenney/ui_icon_checkmark.png" alt="已选"/><img class="weapon-image" src="${w.id==='pressure'?'assets/illustrated/vacuum.webp':`assets/illustrated/${w.id}-v1.webp`}" alt="${w.name}"/><span class="weapon-tag">${w.tag}</span><strong>${w.name}</strong><small>${w.description}</small></button>`).join('');
  document.querySelectorAll('[data-weapon]').forEach(b=>b.onclick=()=>{game.selectWeapon(b.dataset.weapon);renderer.reset();weaponChoices();hud();});
}
function gadgetChoices(){
 $('gadget-choices').innerHTML=GADGETS.map(id=>{const u=UPGRADES.find(u=>u.id===id);return `<button class="gadget-choice ${game.starterGadget===id?'selected':''}" data-gadget="${id}" aria-pressed="${game.starterGadget===id}"><img src="assets/original/${id}.svg" alt=""/><strong>${u.name}</strong></button>`;}).join('');
 document.querySelectorAll('[data-gadget]').forEach(b=>b.onclick=()=>{game.selectGadget(b.dataset.gadget);renderer.reset();gadgetChoices();hud();});
}
$('preset-select').innerHTML=PRESETS.map(k=>`<option value="${k.id}">${k.id==='normal'?'正常成长：':'组合试玩：'}${k.name}</option>`).join('');
$('preset-select').onchange=()=>{game.selectPreset($('preset-select').value);renderer.reset();weaponChoices();gadgetChoices();hud();};
$('evolution-list').innerHTML=EVOLUTIONS.map(e=>`<div><strong>${e.name}</strong><small>${Object.entries(e.needs).map(([id,n])=>UPGRADES.find(u=>u.id===id).name+' '+['','I','II','III'][n]).join(' + ')} → ${e.description}</small></div>`).join('');
weaponChoices();gadgetChoices();$('start').disabled=false;$('start').innerHTML='带上装备，开工！ <span>↗</span>';
$('start').addEventListener('click',begin);
$('restart').addEventListener('click',restart);
$('pause').addEventListener('click',()=>{game.togglePause();clearInput();syncOverlay();});
$('sound').addEventListener('click',()=>{sound=!sound;try{motorSound.setEnabled(sound);}catch{sound=false;}$('sound').textContent=`声音 ${sound?'开':'关'}`;$('sound').setAttribute('aria-label',sound?'关闭声音':'打开声音');tone(520,.15);});
const keyboard=createGameKeyboard({state:()=>game.state,keys,fire:()=>game.fire(),pause:()=>{game.togglePause();clearInput();syncOverlay();}});
window.addEventListener('keydown',keyboard.down);
window.addEventListener('keyup',keyboard.up);
window.addEventListener('blur',()=>{clearInput();if(game.state==='playing'){game.togglePause();syncOverlay();}});
document.addEventListener('visibilitychange',()=>{if(document.hidden){clearInput();if(game.state==='playing'){game.togglePause();syncOverlay();}}});
$('game').addEventListener('pointermove',e=>{if(e.pointerType==='mouse'){pointer=renderer.point(e.clientX,e.clientY);touch=false;}});
$('game').addEventListener('pointerleave',()=>{pointer=null;});
$('game').addEventListener('pointerdown',e=>{if(e.pointerType==='mouse'&&e.button===0){pointer=renderer.point(e.clientX,e.clientY);game.player.angle=Math.atan2(pointer.y-game.player.y,pointer.x-game.player.x);game.fire();$('game').focus({preventScroll:true});}});
$('game').addEventListener('contextmenu',e=>e.preventDefault());
let joystickPointer=null;
function moveStick(e){const r=$('joystick').getBoundingClientRect(),dx=e.clientX-r.left-r.width/2,dy=e.clientY-r.top-r.height/2,d=Math.hypot(dx,dy),scale=d>34?34/d:1;stick={x:dx*scale/34,y:dy*scale/34};$('stick').style.transform=`translate(${dx*scale}px,${dy*scale}px)`;}
$('joystick').addEventListener('pointerdown',e=>{if(joystickPointer!==null)return;e.preventDefault();touch=true;pointer=null;joystickPointer=e.pointerId;e.currentTarget.setPointerCapture(e.pointerId);moveStick(e);});
$('joystick').addEventListener('pointermove',e=>{if(e.pointerId===joystickPointer)moveStick(e);});
for(const name of ['pointerup','pointercancel','lostpointercapture'])$('joystick').addEventListener(name,e=>{if(e.pointerId===joystickPointer){joystickPointer=null;stick={x:0,y:0};$('stick').style.transform='';}});
$('touch-fire').addEventListener('pointerdown',e=>{e.preventDefault();touch=true;pointer=null;fireHeld=true;game.fire();e.currentTarget.setPointerCapture(e.pointerId);});
for(const name of ['pointerup','pointercancel','lostpointercapture'])$('touch-fire').addEventListener(name,()=>fireHeld=false);

function showUpgradeChoices(focusId=null){
 const overlay=$('overlay');overlay.classList.remove('showcase-overlay');
 overlay.innerHTML=`<div class="modal upgrade-modal plan-modal"><div class="upgrade-heading"><div><span class="modal-eyebrow">第 ${game.room} 关 · 收拾妥当</span><h2>选好下一步，继续变强。</h2></div><button class="reroll" id="reroll" ${game.rerolls?'':'disabled'}>换一批 <b>${game.rerolls} / 3</b><small>整局共用</small></button></div>${renderBuildPlanner(game)}<div class="upgrades">${game.offers.map(id=>UPGRADES.find(u=>u.id===id)).map(u=>`<button class="upgrade" data-upgrade="${u.id}"><img class="upgrade-icon" src="assets/original/${u.icon}.svg" alt=""/><span class="category">${u.category}</span><strong>${u.name}${GADGETS.includes(u.id)?` · ${['I','II','III'][game.mods[u.id]]}`:''}</strong><small>${u.description}</small><span class="outcome">${upgradeOutcome(game,u.id)}</span></button>`).join('')}</div><div class="menu-keys">选择后恢复一格体力 · Tab 切换，Enter 确认</div></div>`;
 overlay.querySelectorAll('[data-upgrade]').forEach(b=>b.onclick=()=>{game.chooseUpgrade(b.dataset.upgrade);tone(640,.16);syncOverlay();hud();});
 overlay.querySelectorAll('[data-build]').forEach(b=>b.onclick=()=>{game.markBuild(b.dataset.build);showUpgradeChoices(b.dataset.build);});
 $('reroll').onclick=()=>{if(game.rerollOffers()){tone(460,.08);showUpgradeChoices('reroll');}};
 const focus=focusId==='reroll'?$('reroll'):focusId?overlay.querySelector(`[data-build="${focusId}"]`):overlay.querySelector('[data-upgrade]');
 (focus?.disabled?overlay.querySelector('[data-upgrade]'):focus)?.focus({preventScroll:true});
}
function syncOverlay(){
  if(game.state===lastState)return;lastState=game.state;clearInput();const overlay=$('overlay');overlay.classList.remove('showcase-overlay');
  if(game.state==='playing'||game.state==='clearing'){overlay.hidden=true;if(game.state==='playing')$('game').focus({preventScroll:true});return;}
  if(game.state==='upgrade'){
    overlay.hidden=false;overlay.classList.add('showcase-overlay');
    overlay.innerHTML=`<div class="clear-reward">${game.room===4?'<span class="leaf-medal" aria-label="叶子徽章">✿</span>':''}<div><span class="modal-eyebrow">${game.clearReason==='clean'?'清洁达标 · 怪物撤退':'捣蛋鬼已清空'}</span><strong>第 ${game.room} 关，收拾妥当。</strong><small>${COMMISSIONS[game.room]?.thanks||'下一站 · '+ROOM_NAMES[game.room]}</small></div><button class="primary" id="show-upgrades">挑选升级 ↗</button></div>`;
    $('show-upgrades').onclick=()=>showUpgradeChoices();$('show-upgrades').focus({preventScroll:true});
  }else if(game.state==='paused'){
    overlay.hidden=false;overlay.innerHTML='<div class="modal"><span class="modal-eyebrow">TAKE A LITTLE BREAK</span><h2>吸尘器休息一下。</h2><p>后院的麻烦也会乖乖等着。</p><button class="primary" id="resume">继续开工 <span>↗</span></button><button class="secondary" id="retry">重新开始</button></div>';
    $('resume').onclick=()=>{game.togglePause();syncOverlay();};$('retry').onclick=restart;$('resume').focus({preventScroll:true});
  }else if(game.state==='won'||game.state==='lost'){
    const won=game.state==='won',secs=Math.round(game.time);
    overlay.hidden=false;overlay.innerHTML=renderRunRecap(game);
    $('again').onclick=restart;$('new-kit').onclick=()=>location.reload();$('export').onclick=()=>{const blob=new Blob([JSON.stringify(game.summary(),null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='dust-and-dash-run.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};$('again').focus({preventScroll:true});
  }
}
function hud(){
  $('synergy-status').textContent=(game.preset&&game.preset!=='normal'?'组合试玩 · ':'')+(activeSynergies(game).map(s=>s.name).join(' · ')||'带上新装备，组合出你的清洁方式');
  $('room-label').textContent=`ROOM ${String(game.room).padStart(2,'0')} / ${String(ROOMS.length).padStart(2,'0')}`;$('room-name').textContent=ROOM_NAMES[game.room-1];$('room-badge').textContent=game.stage.flavor.name+(game.stage.remaining?` · 回收包 ${game.stage.remaining} 个`:'');
  $('enemy-count').innerHTML=`${game.aliveCount} <small>只</small>`;$('clean-percent').innerHTML=`${game.cleanPercent}<small>%</small>`;
  $('hearts').innerHTML=Array.from({length:5},(_,i)=>`<span class="${i>=game.player.hp?'heart-empty':''}">♥</span>`).join(' ');$('hearts').setAttribute('aria-label',`体力 ${game.player.hp} / 5`);
  const ammo=Math.floor(game.player.ammo),capacity=game.mods.capacity;$('ammo-fill').style.width=`${ammo/capacity*100}%`;$('ammo-text').textContent=`${ammo} / ${capacity}`;document.querySelector('.ammo-track>i').style.left=`${20/capacity*100}%`;$('clean-fill').style.width=`${game.cleanPercent}%`;
  const weapon=WEAPONS.find(w=>w.id===game.weapon);$('equipped-name').textContent=weapon.name+' · '+weapon.tag;$('equipped-icon').src=weapon.id==='pressure'?'assets/illustrated/vacuum.webp':`assets/illustrated/${weapon.id}-v1.webp`;
  $('shot-state').textContent=game.weapon==='foam'&&ammo>=20?'泡沫就绪 · 每发 20 点':ammo>=capacity*.8?'大弹球就绪，来一发！':ammo>=20?'可以发射 · 多攒更强':'吸一吸，装点弹药';$('shot-state').classList.toggle('ready',ammo>=20);
  $('pause').disabled=!['playing','paused'].includes(game.state);$('pause').innerHTML=game.state==='paused'?'继续 <kbd>ESC</kbd>':'暂停 <kbd>ESC</kbd>';
  for(const el of document.querySelectorAll('[data-room]')){el.classList.toggle('active',+el.dataset.room===game.room);el.classList.toggle('done',+el.dataset.room<game.room||game.state==='won');}
  $('kit-items').innerHTML=`<span class="kit-tag">${weapon.name}</span>`+[...new Set(game.loadout)].map(id=>`<span class="kit-tag"><img src="assets/original/${id}.svg" alt=""/>${UPGRADES.find(u=>u.id===id).name}${GADGETS.includes(id)?' '+['','I','II','III'][game.mods[id]]:''}</span>`).join('');
  $('tip').textContent=game.stage?.flavor.rule||COMMISSIONS[game.room]?.note||ROOMS[game.room-1].tip||(game.room===1?'吸入会剥掉泥壳。攒得越多，垃圾弹打得越痛。':game.cleanPercent>=80?'快打扫好了！达到 90% 就能直接过关。':game.room===2?'面朝飞来的泥弹，把它吸进弹舱。':'绿色绒球会分裂。也可以绕开它，把地面清到 90%。');
}
function frame(now){
  const elapsed=Math.min((now-prev)/1000,.05);prev=now;accumulator+=elapsed;
  const input={x:(keys.has('KeyD')||keys.has('ArrowRight')?1:0)-(keys.has('KeyA')||keys.has('ArrowLeft')?1:0)+stick.x,
    y:(keys.has('KeyS')||keys.has('ArrowDown')?1:0)-(keys.has('KeyW')||keys.has('ArrowUp')?1:0)+stick.y,
    autoAim:touch||!pointer,fire:keys.has('Space')||fireHeld};
  if(pointer&&!touch)input.angle=Math.atan2(pointer.y-game.player.y,pointer.x-game.player.x);
  while(accumulator>=1/60){game.update(1/60,input);accumulator-=1/60;}
  for(const e of game.drainEvents()){
    renderer.event(e);if(['fire','shell','clear','foam-boost','bucket-toss'].includes(e.type))motorSound.cue(e.type);
    if(e.type==='clear'){journal=rememberRoom({setItem:(k,v)=>localStorage.setItem(k,v)},journal,game.room);updateJournal();}
    
    if(e.type==='burst')tone(370,.16,'sine');
    
    if(e.type==='bubble-pop')tone(480,.12,'sine',.02);
    if(e.type==='electric')tone(820,.09,'triangle',.018);
    
    if(e.type==='delivery')tone(700,.16,'sine',.025);if(e.type==='wash-trigger')tone(950,.15,'triangle',.025);if(e.type==='return-catch')tone(570,.19,'sine',.03);
    if(e.type==='relay')tone(360,.08,'triangle',.02);
    if(e.type==='catch')tone(780,.055,'sine',.012);
    if(e.type==='hurt')tone(100,.18,'sawtooth',.02);
    if(e.type==='empty')toast('再吸一点垃圾，20 点就能发射');
    if(e.type==='clear'){toast(e.reason==='clean'?'清洁达标！捣蛋鬼撤退啦。':'漂亮！捣蛋鬼全部清空。');}
    if(e.type==='evolution'){toast('连携成型：'+e.name);tone(660,.28,'triangle',.04);tone(990,.3,'sine',.025);}
    if(e.type==='room')toast(`${ROOM_NAMES[e.room-1]} · 开工！`);
  }
  motorSound.update(game);renderer.draw(elapsed);syncOverlay();hudTimer+=elapsed;if(hudTimer>.1){hud();hudTimer=0;}
  if(now>toastUntil)$('toast').classList.remove('visible');requestAnimationFrame(frame);
}
$('route').innerHTML=ROOMS.map((r,i)=>`<div class="route-item ${i===0?'active':''}" data-room="${i+1}"><span>${String(i+1).padStart(2,'0')}</span><div>${r.name}<small>${({garden:'花园',workshop:'工坊',greenhouse:'温室'})[r.theme]}</small></div><i></i></div>`).join('');
function updateJournal(){
 const el=$('commission-record');if(!el)return;el.textContent=journal.teaParty?'✿ 花园茶会已完成 · 叶子徽章已收藏':`花园茶会委托 · 已完成 ${journal.completed.filter(n=>n<=4).length} / 4 处`;
}
updateJournal();hud();requestAnimationFrame(frame);
// Read-only snapshot for repeatable local verification; no network telemetry.
window.cleaningGame={snapshot:()=>game.summary(),floor:()=>({cols:game.cols,rows:game.rows,dirt:Array.from(game.dirt)}),state:()=>({room:game.room,state:game.state,player:{...game.player},enemies:game.enemies.map(e=>({...e})),clean:game.cleanPercent,clearReason:game.clearReason,weapon:game.weapon,offers:[...game.offers],mods:{...game.mods}})};
