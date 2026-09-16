import {chooseOffers} from './build-plan.js?v=11';
import {RoomFeatures} from './room-features.js?v=11';
import {encounter,enemyIntent} from './encounters.js?v=11';
import {COMMISSIONS} from './commissions.js?v=11';
import {SPECIAL_ENEMIES,updateSpecial,updateHazards} from './enemy-behaviors.js?v=11';
import {RULES,PRESETS,EVOLUTIONS,evolved,availableEvolutions} from './combinations.js?v=11';
import {Gadgets,GADGETS} from './gadgets.js?v=11';
export const TILE = 20;
import {UPGRADES,WEAPONS,ROOMS,CLEAN_TARGET} from './content.js?v=11';
export {UPGRADES,WEAPONS,ROOMS,CLEAN_TARGET};
export const ROOM_NAMES=ROOMS.map(r=>r.name);
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const distance=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y);
export function seededRandom(seed){let s=seed>>>0;return()=>{s=(Math.imul(1664525,s)+1013904223)>>>0;return s/4294967296;};}

// Pure simulation: ownership of all run state stays here. Rendering consumes
// bounded transient events; restarting never retains entities or subscribers.
export class Game {
  constructor({seed=Date.now(),width=960,height=600,weapon='pressure',starterGadget=null}={}){
    this.width=width;this.height=height;this.cols=Math.ceil(width/TILE);this.rows=Math.ceil(height/TILE);
    this.starterGadget=GADGETS.includes(starterGadget)?starterGadget:null;this.seed=seed;this.weapon=WEAPONS.some(w=>w.id===weapon)?weapon:'pressure';this.reset();
  }
  reset(seed=this.seed){
    this.seed=seed;this.random=seededRandom(seed);this.state='ready';this.room=1;this.time=0;this.roomTime=0;
    this.player={x:this.width/2,y:this.height/2,r:17,angle:-Math.PI/2,hp:5,maxHp:5,ammo:0,invincible:0,speed:232};
    this.rerolls=3;this.buildGoal=null;this.evolutionHistory=[];this.catchBoost=0;
    this.stats={shots:0,kills:0,cleaned:0,hits:0,chains:0,rooms:0};this.loadout=[];this.offers=[];this.roomResults=[];this.clearReason=null;this.foam=[];this.dronePhase=0;
    this.mods={compressor:0,doublemouth:0,returner:0,backpack:0,brush:0,bucket:0,bubble:0,electric:0,mop:0,duck:0,range:185,cone:.57,power:1,burst:112,chainDamage:19,suction:1,capacity:100,pierce:0,bounces:0,refund:0,skates:0,drones:0,yield:1,frost:0};
    if(this.weapon==='scatter'){this.mods.cone=.8;this.mods.range=170;}
    if(this.weapon==='foam'){this.mods.range=195;this.mods.suction=1.1;}
    if(this.starterGadget){this.mods[this.starterGadget]=1;this.loadout.push(this.starterGadget);}
    if(this.preset&&this.preset!=='normal'){const kit=PRESETS.find(k=>k.id===this.preset);Object.assign(this.mods,kit.levels);this.loadout=[...new Set([...this.loadout,...Object.keys(kit.levels)])];}
    this.events=[];this.journal=[];this.shots=[];this.hostileShots=[];this.hazards=[];this.enemies=[];this.deathQueue=[];
    this.packCharge=0;this.shotCooldown=0;this.sweep=0;this.setupRoom();
  }
  log(type,data={}){this.journal.push({t:+this.time.toFixed(2),room:this.room,type,...data});if(this.journal.length>500)this.journal.shift();}
  emit(type,data={}){if(this.events.length<180)this.events.push({...data,type});}
  drainEvents(){return this.events.splice(0);}
  selectWeapon(id){if(this.state!=='ready'||!WEAPONS.some(w=>w.id===id))return false;this.weapon=id;this.reset(this.seed);return true;}
  selectPreset(id){if(this.state!=='ready'||!PRESETS.some(k=>k.id===id))return false;this.preset=id;const kit=PRESETS.find(k=>k.id===id);if(kit.weapon)this.weapon=kit.weapon;this.reset(this.seed);return true;}
  selectGadget(id){if(this.state!=='ready'||!GADGETS.includes(id))return false;this.starterGadget=id;this.reset(this.seed);return true;}
  start(){if(this.state!=='ready')return;this.state='playing';this.log('start');this.emit('room',{room:1});}
  togglePause(){if(this.state==='playing'){this.state='paused';this.log('pause');}else if(this.state==='paused'){this.state='playing';this.log('resume');}}
  setupRoom(){
    this.gadgets=null;this.stage=null;
    this.dirt=new Float32Array(this.cols*this.rows);this.shots=[];this.hostileShots=[];this.hazards=[];this.enemies=[];this.deathQueue=[];this.foam=[];this.clearReason=null;
    this.player.x=this.width/2;this.player.y=this.height*.63;this.player.angle=-Math.PI/2;this.player.invincible=1.4;
    this.roomTime=0;this.sweep=0;this.shotCooldown=0;this.gathering=0;this.catchBoost=0;
    for(let i=0;i<43+this.room*5;i++)this.paint(55+this.random()*(this.width-110),60+this.random()*(this.height-120),28+this.random()*46,.65+this.random()*.35);
    this.clearArea(this.player.x,this.player.y,56,false);
    // Ensure every generated room starts meaningfully below the victory threshold.
    for(let n=0;this.cleanExact>75&&n<100;n++)this.paint(60+this.random()*(this.width-120),60+this.random()*(this.height-120),65,.9);
    const commission=COMMISSIONS[this.room];
    if(commission?.dirt){
      this.dirt.fill(.32);
      for(const [x,y,r] of commission.dirt)this.paint(x*this.width,y*this.height,r*Math.min(this.width,this.height),1);
      this.clearArea(this.player.x,this.player.y,56,false);
    }
    const types=ROOMS[this.room-1].types,count=types.length;
    if(this.room>=5){for(const spot of encounter(this.room,types,this.width,this.height))Object.assign(this.spawnEnemy(spot.type,spot.x,spot.y),spot);}
    else for(let i=0;i<count;i++){
      const angle=(i/count)*Math.PI*2-.8;
      const x=clamp(this.width/2+Math.cos(angle)*this.width*.32,65,this.width-65);
      const y=clamp(this.height/2+Math.sin(angle)*this.height*.31,65,this.height-65);
      const spot=commission?.layout[i];this.spawnEnemy(types[i],spot?spot[0]*this.width:x,spot?spot[1]*this.height:y);
    }
    this.initialEnemies=this.enemies.length;this.gadgets=new Gadgets(this);this.stage=new RoomFeatures(this);
    if(this.room>=10)this.enemies.filter(e=>e.type==='boss').forEach((e,i)=>{e.duet=i;e.engaged=true;});
  }
  spawnEnemy(type,x,y){
    const boss=type==='boss';
    const enemy={id:`${this.room}:${this.enemies.length}`,type,x,y,r:boss?36:type==='mini'?13:type==='splitter'?26:type==='spitter'?22:21,
      hp:boss?210:type==='splitter'?52:type==='mini'?16:36,maxHp:boss?210:type==='splitter'?52:type==='mini'?16:36,armor:boss?85:type==='runner'?12:type==='mini'?0:24,maxArmor:boss?85:type==='runner'?12:type==='mini'?0:24,
      speed:boss?38:type==='spitter'?44:type==='runner'?98:type==='mini'?88:58+this.room*4,slow:0,alive:true,phase:this.random()*6.28,
      attack:1.4+this.random()*1.7,windup:0,trail:.3,hit:0,knockX:0,knockY:0};
    if(SPECIAL_ENEMIES[type]){Object.assign(enemy,SPECIAL_ENEMIES[type]);enemy.maxHp=enemy.hp;enemy.maxArmor=enemy.armor;}
    if(this.room>=5){
      const scale=1+(this.room-4)*.14;enemy.hp*=scale;enemy.maxHp=enemy.hp;
      if(boss&&this.room>=10){enemy.hp=this.room===12?900:720;enemy.maxHp=enemy.hp;enemy.armor=120;enemy.maxArmor=120;}
    }
    this.enemies.push(enemy);return enemy;
  }
  get aliveCount(){return this.enemies.reduce((n,e)=>n+(e.alive?1:0),0);}
  get cleanPercent(){return Math.floor(this.cleanExact+1e-6);}
  get cleanExact(){let total=0,n=0;for(let row=2;row<this.rows-2;row++)for(let col=2;col<this.cols-2;col++){total+=this.dirt[row*this.cols+col];n++;}return Math.max(0,100*(1-(total+(this.gadgets?.pendingDirt||0)+(this.stage?.pendingDirt||0))/n));}
  paint(x,y,r,amount=1){
    const minX=Math.max(2,Math.floor((x-r)/TILE)),maxX=Math.min(this.cols-3,Math.ceil((x+r)/TILE));
    const minY=Math.max(2,Math.floor((y-r)/TILE)),maxY=Math.min(this.rows-3,Math.ceil((y+r)/TILE));
    for(let row=minY;row<=maxY;row++)for(let col=minX;col<=maxX;col++){
      const d=Math.hypot(col*TILE+TILE/2-x,row*TILE+TILE/2-y);
      if(d<r){const idx=row*this.cols+col;this.dirt[idx]=Math.max(this.dirt[idx],amount*Math.min(1,(r-d)/12));}
    }
  }
  clearArea(x,y,r,count=true){
    let total=0;for(let row=Math.max(2,Math.floor((y-r)/TILE));row<=Math.min(this.rows-3,Math.ceil((y+r)/TILE));row++)
      for(let col=Math.max(2,Math.floor((x-r)/TILE));col<=Math.min(this.cols-3,Math.ceil((x+r)/TILE));col++){
        if(Math.hypot(col*TILE+10-x,row*TILE+10-y)<r){const idx=row*this.cols+col;total+=this.dirt[idx];this.dirt[idx]=0;}
      }
    if(count)this.stats.cleaned+=total;return total;
  }
  inCone(x,y){const dx=x-this.player.x,dy=y-this.player.y,d=Math.hypot(dx,dy);const facing=(dx*Math.cos(this.player.angle)+dy*Math.sin(this.player.angle))/d;return d<this.mods.range*(this.mods.doublemouth?.75:1)&&(d<30||(this.mods.doublemouth?Math.abs(facing):facing)>Math.cos(this.mods.cone));}
  fire(){
    if(this.state!=='playing'||this.shotCooldown>0)return false;
    if(this.player.ammo<20){this.emit('empty');this.shotCooldown=.2;return false;}
    const amount=this.weapon==='foam'?20:this.player.ammo;
    this.player.ammo=this.player.ammo-amount+amount*this.mods.refund;this.shotCooldown=(this.weapon==='foam'?.19:.4)*(this.mods.compressor?1.8:1);
    const p=this.player,a=p.angle,spread=this.weapon==='scatter'?[-.23,0,.23]:[0];
    for(const offset of spread){const speed=this.weapon==='foam'?420:650;
      this.shots.push({x:p.x+Math.cos(a)*27,y:p.y+Math.sin(a)*27,vx:Math.cos(a+offset)*speed,vy:Math.sin(a+offset)*speed,
        r:(this.weapon==='foam'?11:8+amount*.1)*Math.sqrt(this.mods.power),damage:(this.weapon==='foam'?24:24+amount*.6)*this.mods.power*(this.weapon==='scatter'?.52:1),life:2.1,amount,
        weapon:this.weapon,pierce:this.mods.pierce,bounces:this.mods.bounces,hitIds:[]});
    }
    for(const s of this.shots.slice(-spread.length)){if(this.mods.compressor){s.r*=1.6;s.damage*=1.5;s.pierce+=2;}if(this.mods.returner){s.returning=true;s.returnValue=amount*.25/spread.length;}}
    if(evolved(this,'pinball')&&this.weapon!=='foam'&&amount>=60){
      for(const s of this.shots.slice(-spread.length)){s.returning=true;s.returnValue=amount*.25/spread.length;s.evolvedReturn=true;s.bounces=Math.max(1,s.bounces);}
    }
    if(this.catchBoost>0){for(const s of this.shots.slice(-spread.length))s.damage*=1.35;this.catchBoost=0;this.emit('catch-shot',{x:p.x,y:p.y});}
    this.gadgets.commandDelivery();this.stats.shots++;this.log('fire',{charge:Math.round(amount),weapon:this.weapon});this.emit('fire',{x:p.x,y:p.y,angle:a,amount});return true;
  }
  addFoam(x,y){if(this.foam.length>=30)this.foam.shift();this.foam.push({x,y,r:62,life:3.5});this.emit('foam',{x,y});}
  finishRoom(reason){
    if(this.state!=='playing')return;
    this.clearReason=reason;const result={room:this.room,reason,seconds:+this.roomTime.toFixed(2),remaining:this.aliveCount,clean:+this.cleanExact.toFixed(2)};
    result.flavor=this.stage?.flavor.name;result.parcels=this.stage?.parcels.filter(p=>p.opened).length||0;this.stage?.finish();
    this.roomResults.push(result);this.state='clearing';this.stats.rooms++;this.gadgets.reset();this.hostileShots=[];this.hazards=[];this.shots=[];this.foam=[];this.sweep=0;
    for(const e of this.enemies)if(e.alive){e.alive=false;this.emit('flee',{x:e.x,y:e.y});}
    this.log('clear',result);this.emit('clear',{reason});
  }
  rollOffers(exclude=[]){this.offers=chooseOffers(this,exclude);}
  markBuild(id){
    if(!['ready','upgrade'].includes(this.state)||!EVOLUTIONS.some(e=>e.id===id))return false;
    this.buildGoal=this.buildGoal===id?null:id;this.log('build-goal',{id:this.buildGoal});return true;
  }
  rerollOffers(){
    if(this.state!=='upgrade'||this.rerolls<=0)return false;
    const previous=[...this.offers];this.rollOffers(previous);this.rerolls--;this.log('reroll',{previous,offers:[...this.offers],left:this.rerolls});return true;
  }
  evolutionUse(id){
    const record=this.evolutionHistory.find(e=>e.id===id);if(!record)return;
    record.uses++;if(record.firstUseAt===null)record.firstUseAt=this.time;
  }

  hurtPlayer(source='碰到捣蛋鬼'){
    const p=this.player;if(this.state!=='playing'||p.invincible>0)return;
    p.hp--;p.invincible=1.3;this.stats.hits++;this.log('hurt',{hp:p.hp,source});this.emit('hurt',{x:p.x,y:p.y,source});
    if(p.hp<=0){this.state='lost';this.log('lost');this.emit('lost');}
  }
  hitEnemy(e,damage,kind='shot'){
    if(!e.alive)return;
    if(e.type==='boss'&&e.vulnerable){damage*=1.3;if(!['suction','mop','brush','drone'].includes(kind))this.stats.windowHits=(this.stats.windowHits||0)+1;}
    if(!['suction','drone'].includes(kind)||e.hit<=0){e.hit=.14;e.impactStrength=['suction','drone'].includes(kind)?.035:.18;}
    if(e.armor>0){const absorbed=Math.min(e.armor,damage);e.armor-=absorbed;damage-=absorbed;if(e.armor<=.001){e.armor=0;this.emit('shell',{x:e.x,y:e.y});}}
    e.hp-=damage;
    if(e.hp<=0){e.alive=false;this.stats.kills++;if(kind==='chain')this.stats.chains++;this.deathQueue.push(e);this.log('kill',{enemy:e.type,kind});}
  }
  resolveDeaths(){
    // Queue instead of recursive blasts; each enemy can enter this queue once.
    while(this.deathQueue.length){
      const dead=this.deathQueue.shift(),radius=this.mods.burst*(dead.type==='boss'?1.5:1);
      this.clearArea(dead.x,dead.y,radius);this.emit('burst',{x:dead.x,y:dead.y,r:radius,enemyType:dead.type});
      for(const other of this.enemies)if(other.alive&&distance(dead,other)<radius+other.r){
        this.hitEnemy(other,this.mods.chainDamage,'chain');
        const a=Math.atan2(other.y-dead.y,other.x-dead.x);other.knockX+=Math.cos(a)*120;other.knockY+=Math.sin(a)*120;
      }
      if(dead.type==='splitter'){for(const side of [-1,1])this.spawnEnemy('mini',dead.x+side*23,dead.y+12);}
    }
  }
  chooseUpgrade(id){
    if(this.state!=='upgrade'||!this.offers.includes(id))return false;
    const previousEvolutions=new Set(availableEvolutions(this).map(e=>e.id));
    if(RULES.includes(id))this.mods[id]=1;
    if(GADGETS.includes(id))this.mods[id]=Math.min(3,this.mods[id]+1);
    if(id==='wide'){this.mods.range+=38;this.mods.cone+=.16;this.mods.suction*=1.22;}
    if(id==='power')this.mods.power*=1.35;
    if(id==='chain'){this.mods.burst+=38;this.mods.chainDamage+=17;}
    if(id==='battery')this.mods.capacity+=40;
    if(id==='pierce')this.mods.pierce++;
    if(id==='bounce')this.mods.bounces=Math.min(2,this.mods.bounces+1);
    if(id==='recycle')this.mods.refund=Math.min(.5,this.mods.refund+.25);
    if(id==='skates'){this.player.speed*=1.15;this.mods.skates++;}
    if(id==='drone')this.mods.drones=Math.min(3,this.mods.drones+1);
    if(id==='magnet'){this.mods.yield*=1.45;this.mods.range+=15;}
    if(id==='frost')this.mods.frost++;
    if(id==='heart'){this.player.hp=this.player.maxHp;this.mods.suction*=1.1;}
    this.loadout.push(id);this.log('upgrade',{id});this.room++;this.player.hp=Math.min(this.player.maxHp,this.player.hp+1);
    this.setupRoom();this.state='playing';this.emit('room',{room:this.room});for(const e of availableEvolutions(this))if(!previousEvolutions.has(e.id)){this.emit('evolution',{name:e.name});this.log('evolution',{id:e.id});this.evolutionHistory.push({id:e.id,room:this.room,at:this.time,activeSeconds:0,uses:0,firstUseAt:null});}return true;
  }
  update(dt,input={}){
    if(!Number.isFinite(dt)||dt<=0)return;dt=Math.min(dt,1/30);
    if(this.state==='clearing'){
      this.sweep+=dt;const radius=this.sweep*760;this.clearArea(this.player.x,this.player.y,radius);
      if(this.sweep>1.5){this.dirt.fill(0);this.state=this.room===ROOMS.length?'won':'upgrade';if(this.state==='upgrade')this.rollOffers();this.log(this.state);this.emit(this.state);}
      return;
    }
    if(this.state!=='playing')return;
    this.time+=dt;this.roomTime+=dt;this.catchBoost=Math.max(0,this.catchBoost-dt);for(const e of this.evolutionHistory)e.activeSeconds+=dt;this.dronePhase+=dt*2.5;this.shotCooldown=Math.max(0,this.shotCooldown-dt);
    const p=this.player;p.invincible=Math.max(0,p.invincible-dt);
    let mx=input.x||0,my=input.y||0,mag=Math.hypot(mx,my);if(mag>1){mx/=mag;my/=mag;}
    p.x=clamp(p.x+mx*p.speed*dt,42,this.width-42);p.y=clamp(p.y+my*p.speed*dt,42,this.height-42);
    if(Number.isFinite(input.angle))p.angle=input.angle;
    else if(input.autoAim){const target=this.enemies.filter(e=>e.alive).sort((a,b)=>distance(a,p)-distance(b,p))[0];if(target)p.angle=Math.atan2(target.y-p.y,target.x-p.x);else if(mag>.1)p.angle=Math.atan2(my,mx);}
    let gathered=0;
    const reach=this.mods.range;
    for(let row=Math.max(2,Math.floor((p.y-reach)/TILE));row<=Math.min(this.rows-3,Math.ceil((p.y+reach)/TILE));row++)
      for(let col=Math.max(2,Math.floor((p.x-reach)/TILE));col<=Math.min(this.cols-3,Math.ceil((p.x+reach)/TILE));col++){
        const idx=row*this.cols+col;if(this.dirt[idx]<=0||!this.inCone(col*TILE+10,row*TILE+10))continue;
        const taken=Math.min(this.dirt[idx],dt*1.9*this.mods.suction);this.dirt[idx]-=taken;gathered+=taken;
        if(taken>0&&this.random()<dt*6)this.emit('suck',{x:col*TILE+10,y:row*TILE+10});
      }
    let converted=0;if(this.mods.backpack&&gathered>0&&this.gadgets.bubbles.length<12){converted=gathered*.3;this.packCharge=(this.packCharge||0)+converted*2.5;if(this.packCharge>=12){this.packCharge-=12;this.gadgets.makeBubble(p.x-35*Math.cos(p.angle),p.y-35*Math.sin(p.angle),p.angle+Math.PI);}}
    this.gathering=gathered/dt;this.stats.cleaned+=gathered;p.ammo=clamp(p.ammo+(gathered-converted)*2.5*this.mods.yield,0,this.mods.capacity);
    if(this.mods.skates)this.clearArea(p.x,p.y,24+this.mods.skates*4);
    for(const f of this.foam){f.life-=dt;this.clearArea(f.x,f.y,f.r);}
    this.foam=this.foam.filter(f=>f.life>0);
    for(let i=0;i<this.mods.drones;i++){
      const a=this.dronePhase+i*Math.PI*2/this.mods.drones,x=p.x+Math.cos(a)*75,y=p.y+Math.sin(a)*75;
      this.clearArea(x,y,24);for(const e of this.enemies)if(e.alive&&Math.hypot(e.x-x,e.y-y)<e.r+17)this.hitEnemy(e,25*dt,'drone');
    }
    this.gadgets.update(dt);this.stage.update(dt);
    for(const e of this.enemies){
      if(!e.alive)continue;if(e.trapped){if(e.type==='fan'){e.gust=0;e.windup=0;e.attack=3.8;}if(e.type==='charger'){e.dash=0;e.windup=0;e.attack=3.4;}continue;}e.slow=Math.max(0,e.slow-dt);e.hit=Math.max(0,e.hit-dt);e.phase+=dt*4;
      let dx=p.x-e.x,dy=p.y-e.y,d=Math.hypot(dx,dy)||1;
      const sucking=this.inCone(e.x,e.y);
      if(sucking){
        const strip=24*dt*this.mods.suction;
        if(e.armor>0){const removed=Math.min(e.armor,strip);e.armor-=removed;p.ammo=clamp(p.ammo+removed*.7,0,this.mods.capacity);if(e.armor<=.001){e.armor=0;this.emit('shell',{x:e.x,y:e.y});}}
        else this.hitEnemy(e,14*dt*this.mods.suction,'suction');
      }
      if(!e.alive)continue;
      const intent=enemyIntent(e,p);e.reload=Math.max(0,(e.reload||0)-dt);
      if(intent.attack)updateSpecial(this,e,dt);
      const foamed=this.foam.some(f=>distance(f,e)<f.r+e.r);
      const speed=e.speed*(e.type==='boss'&&this.room>=10?0:1)*(sucking?.45:1)*(e.windup>0?.1:1)*(foamed||e.slow>0?.45:1);
      const dashSpeed=310*(foamed||e.slow>0?.45:1);
      e.x=clamp(e.x+(e.dash>0?Math.cos(e.chargeAngle)*dashSpeed:intent.x*speed)*dt+e.knockX*dt,35+e.r,this.width-35-e.r);
      e.y=clamp(e.y+(e.dash>0?Math.sin(e.chargeAngle)*dashSpeed:intent.y*speed)*dt+e.knockY*dt,35+e.r,this.height-35-e.r);
      e.knockX*=Math.exp(-7*dt);e.knockY*=Math.exp(-7*dt);
      e.trail-=dt;if(e.trail<=0){this.paint(e.x,e.y,e.type==='boss'?31:19,.85);e.trail=.6;}
      if(distance(e,p)<e.r+p.r-3)this.hurtPlayer();
      if(intent.attack&&(e.type==='spitter'||(e.type==='boss'&&this.room<10))){
        if(e.windup>0){e.windup-=dt;if(e.windup<=0){
          const a=Math.atan2(p.y-e.y,p.x-e.x),spread=e.type==='boss'?[-.32,0,.32]:[0];
          for(const offset of spread)this.hostileShots.push({x:e.x,y:e.y,vx:Math.cos(a+offset)*185,vy:Math.sin(a+offset)*185,r:9,life:3.3});
          e.reload=.8;this.emit('spit',{x:e.x,y:e.y});
        }}else{e.attack-=dt;if(e.attack<=0){e.windup=.75;e.attack=e.type==='boss'?2.3:3.1;}}
      }
    }
    updateHazards(this,dt);
    // Gentle separation prevents a single unreadable pile of enemies.
    for(let i=0;i<this.enemies.length;i++)for(let j=i+1;j<this.enemies.length;j++){
      const a=this.enemies[i],b=this.enemies[j];if(!a.alive||!b.alive)continue;
      const dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy),min=(a.r+b.r)*.9;
      if(d>0&&d<min){const push=(min-d)*dt*2;a.x-=dx/d*push;a.y-=dy/d*push;b.x+=dx/d*push;b.y+=dy/d*push;}
    }
    for(const shot of this.hostileShots){
      shot.life-=dt;shot.x+=shot.vx*dt;shot.y+=shot.vy*dt;
      if(this.inCone(shot.x,shot.y)){shot.life=0;p.ammo=clamp(p.ammo+12,0,this.mods.capacity);this.emit('catch',{x:shot.x,y:shot.y});}
      else if(distance(shot,p)<p.r+shot.r){shot.life=0;this.hurtPlayer('被泥弹击中');}
      else if(shot.x<35||shot.x>this.width-35||shot.y<35||shot.y>this.height-35||shot.life<=0){this.paint(shot.x,shot.y,34);shot.life=0;}
    }
    this.hostileShots=this.hostileShots.filter(s=>s.life>0);
    if(input.fire)this.fire();
    for(const shot of this.shots){
      if(shot.returning&&shot.life<1.3){const d=distance(shot,p)||1;shot.vx=(p.x-shot.x)/d*650;shot.vy=(p.y-shot.y)/d*650;if(d<p.r+shot.r){p.ammo=Math.min(this.mods.capacity,p.ammo+shot.returnValue);shot.life=0;this.stats.returns=(this.stats.returns||0)+1;if(shot.evolvedReturn){this.catchBoost=5;this.evolutionUse('pinball');this.emit('return-catch',{x:p.x,y:p.y});}continue;}}
      shot.life-=dt;shot.x+=shot.vx*dt;shot.y+=shot.vy*dt;this.clearArea(shot.x,shot.y,shot.r+8);
      // A manual garbage shot picks up foam once, rather than multiplying every frame.
      if(shot.weapon!=='foam'&&!shot.foamBoosted&&this.foam.some(f=>distance(f,shot)<f.r)){
        shot.foamBoosted=true;shot.damage*=1.25;shot.r*=1.2;
        this.stats.foamShots=(this.stats.foamShots||0)+1;this.emit('foam-boost',{x:shot.x,y:shot.y,r:shot.r+24});
      }
      const enemy=this.enemies.find(e=>e.alive&&!shot.hitIds.includes(e.id)&&distance(e,shot)<e.r+shot.r);
      if(enemy){
        if(shot.foamBoosted)this.addFoam(shot.x,shot.y);
        this.clearArea(shot.x,shot.y,shot.r+18+Math.min(shot.amount,160)*.18);
        if(shot.weapon==='foam')this.addFoam(shot.x,shot.y);this.gadgets.triggerWash(shot);this.hitEnemy(enemy,shot.damage);shot.hitIds.push(enemy.id);if(this.mods.frost)enemy.slow=2;
        enemy.knockX+=shot.vx*.22;enemy.knockY+=shot.vy*.22;
        if(shot.pierce>0)shot.pierce--;else shot.life=0;
        this.emit('impact',{x:shot.x,y:shot.y,r:shot.r+18});
      }
      else if(shot.x<30||shot.x>this.width-30||shot.y<30||shot.y>this.height-30){if(shot.returning){shot.life=Math.min(shot.life,1.29);shot.x=clamp(shot.x,31,this.width-31);shot.y=clamp(shot.y,31,this.height-31);}else if(shot.bounces>0){
          if(shot.x<30||shot.x>this.width-30)shot.vx*=-1;
          if(shot.y<30||shot.y>this.height-30)shot.vy*=-1;
          shot.x=clamp(shot.x,31,this.width-31);shot.y=clamp(shot.y,31,this.height-31);shot.bounces--;
        }else{shot.life=0;if(shot.weapon==='foam')this.addFoam(shot.x,shot.y);}
        this.clearArea(shot.x,shot.y,shot.r*3);this.emit('impact',{x:shot.x,y:shot.y,r:shot.r*2});}
    }
    for(const shot of this.shots)if(shot.life<=0)this.gadgets.triggerWash(shot);
    for(const shot of this.shots)if(shot.life<=0&&shot.weapon==='foam'&&!this.foam.some(f=>Math.hypot(f.x-shot.x,f.y-shot.y)<5))this.addFoam(shot.x,shot.y);
    this.shots=this.shots.filter(s=>s.life>0);this.resolveDeaths();
    if(this.state==='playing'){if(this.aliveCount===0)this.finishRoom('combat');else if(this.cleanExact+1e-6>=CLEAN_TARGET)this.finishRoom('clean');}
  }
  summary(){return{version:11,buildGoal:this.buildGoal,rerolls:this.rerolls,evolutionHistory:this.evolutionHistory.map(e=>({...e,activeSeconds:+e.activeSeconds.toFixed(2)})),preset:this.preset||'normal',rules:RULES.filter(id=>this.mods[id]),equipment:Object.fromEntries(GADGETS.map(id=>[id,this.mods[id]])),weapon:this.weapon,roomResults:[...this.roomResults],seed:this.seed,state:this.state,room:this.room,seconds:+this.time.toFixed(1),stats:{...this.stats},loadout:[...this.loadout],events:[...this.journal]};}
}
