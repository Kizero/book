import {drawRoomFeatures} from './room-feature-render.js?v=11';
import {Feedback} from './feedback.js?v=11';
import {COMMISSIONS} from './commissions.js?v=11';
import {drawGadgets} from './gadget-render.js?v=11';
import {IllustratedArt} from './illustrated-art.js?v=11';
import {TILE,ROOMS,WEAPONS} from './engine.js?v=11';
const TAU=Math.PI*2;
function ellipse(c,x,y,rx,ry,color){c.fillStyle=color;c.beginPath();c.ellipse(x,y,rx,ry,0,0,TAU);c.fill();}
function circle(c,x,y,r,color){ellipse(c,x,y,r,r,color);}
function line(c,points,color,width=2){c.strokeStyle=color;c.lineWidth=width;c.lineCap='round';c.lineJoin='round';c.beginPath();points.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.stroke();}
function rect(c,x,y,w,h,r,color){c.fillStyle=color;c.beginPath();c.roundRect(x,y,w,h,r);c.fill();}
function sparkle(c,x,y,r,color){c.fillStyle=color;c.beginPath();c.moveTo(x,y-r);c.quadraticCurveTo(x+2,y-2,x+r,y);c.quadraticCurveTo(x+2,y+2,x,y+r);c.quadraticCurveTo(x-2,y+2,x-r,y);c.quadraticCurveTo(x-2,y-2,x,y-r);c.fill();}
const hash=(x,y)=>{const n=Math.sin(x*127.1+y*311.7)*43758.5453;return n-Math.floor(n);};

export class Renderer{
  constructor(canvas,game,assets){
    this.feedback=new Feedback();this.assets=assets;this.theme=null;this.art=new IllustratedArt(assets,game);
    this.canvas=canvas;this.ctx=canvas.getContext('2d');this.game=game;this.particles=[];this.rings=[];this.shake=0;this.clock=0;
    this.background=document.createElement('canvas');this.background.width=game.width;this.background.height=game.height;
    this.dirtLayer=document.createElement('canvas');this.dirtLayer.width=game.width;this.dirtLayer.height=game.height;this.makeBackground();this.resize();
    this.observer=new ResizeObserver(()=>this.resize());this.observer.observe(canvas);
  }
  resize(){const box=this.canvas.getBoundingClientRect(),dpr=Math.min(window.devicePixelRatio||1,2);this.canvas.width=Math.round(box.width*dpr);this.canvas.height=Math.round(box.height*dpr);this.scale=Math.min(this.canvas.width/this.game.width,this.canvas.height/this.game.height);this.offsetX=(this.canvas.width-this.game.width*this.scale)/2;this.offsetY=(this.canvas.height-this.game.height*this.scale)/2;}
  point(clientX,clientY){const r=this.canvas.getBoundingClientRect();return{x:((clientX-r.left)*this.canvas.width/r.width-this.offsetX)/this.scale,y:((clientY-r.top)*this.canvas.height/r.height-this.offsetY)/this.scale};}
  sprite(c,name,x,y,w,h,angle=0){
    const img=this.assets[name];if(!img)return;c.save();c.translate(x,y);c.rotate(angle);c.drawImage(img,-w/2,-h/2,w,h);c.restore();
  }
  makeBackground(){
    const c=this.background.getContext('2d'),w=this.game.width,h=this.game.height,theme=ROOMS[this.game.room-1].theme;this.theme=theme;
    this.art.background(c,w,h,this.game.room<=4?'garden':theme);
  }

  event(event){
    const {type,x,y}=event;this.feedback.event(event,this.game);
    if(type==='fire'){this.art.action.fire(event.amount);this.art.kick=event.amount>=80?11:6;this.art.recoil=event.amount>=80?7:4;}
    if(type==='suck')this.particles.push({x,y,life:.36,max:.36,type:'suck',r:2+Math.random()*2});
    if(['burst','impact','shell','catch','hurt','fire','flee','foam','foam-boost','mud-land','parcel-open'].includes(type)){
      const color=type==='hurt'?'#dc9974':type==='shell'?'#bd9978':type==='burst'?'#f5efb5':'#cbe7b4';
      const count=type==='burst'?24:type==='fire'?8:12;
      for(let i=0;i<count;i++){const a=Math.random()*TAU,speed=40+Math.random()*180;this.particles.push({x,y,vx:Math.cos(a)*speed,vy:Math.sin(a)*speed,life:.4+Math.random()*.3,max:.7,type:'spark',r:2+Math.random()*4,color});}
      if(['burst','impact','foam-boost','mud-land','parcel-open'].includes(type))this.rings.push({x,y,r:event.r,life:.5,max:.5});
      if(type==='burst')this.shake=5;if(type==='hurt')this.shake=7;if(type==='fire')this.shake=event.amount>75?3:1;
    }
    if(this.particles.length>450)this.particles.splice(0,this.particles.length-450);
  }
  reset(){this.feedback.reset();this.art.recoil=0;this.art.action.reset();this.particles=[];this.rings=[];this.shake=0;}
  draw(dt){
    const c=this.ctx,g=this.game,w=g.width,h=g.height,active=!['paused','won','lost'].includes(g.state);
    this.feedback.update(dt,g);this.art.update(dt,active);if(active)this.clock+=dt;if(this.theme!==ROOMS[g.room-1].theme)this.makeBackground();
    c.setTransform(1,0,0,1,0,0);c.fillStyle='#b7cc9f';c.fillRect(0,0,this.canvas.width,this.canvas.height);
    c.translate(this.offsetX,this.offsetY);c.scale(this.scale,this.scale);c.save();
    if(active&&this.shake>.1){c.translate((Math.random()-.5)*this.shake,(Math.random()-.5)*this.shake);this.shake*=Math.exp(-13*dt);}
    c.drawImage(this.background,0,0);
    if(g.room===4&&this.feedback.clearAge>1.5&&g.state==='upgrade'&&this.assets['art-tea-courtyard-v2']){
      const img=this.assets['art-tea-courtyard-v2'],scale=Math.max(w/img.width,h/img.height);
      c.save();c.globalAlpha=Math.min(1,(this.feedback.clearAge-1.5)/1.3);c.drawImage(img,(w-img.width*scale)/2,(h-img.height*scale)/2,img.width*scale,img.height*scale);c.restore();
    }
    this.art.dirt(c);drawRoomFeatures(c,g,this.clock);
    if(COMMISSIONS[g.room]){
      // Flowers appear where the nearby ground is actually clean.
      for(let i=0;i<10;i++){
        const x=70+i*(w-140)/9,y=i%2?58:h-58,idx=Math.floor(y/20)*g.cols+Math.floor(x/20),clean=1-(g.dirt[idx]||0);
        if(clean<.45)continue;c.save();c.globalAlpha=clean;line(c,[[x,y+10],[x,y-4]],'#6b9567',3);
        for(let j=0;j<5;j++){const a=j*TAU/5;circle(c,x+Math.cos(a)*5,y-5+Math.sin(a)*5,4,i%2?'#eabfa8':'#e8d692');}circle(c,x,y-5,3,'#f9efd0');c.restore();
      }
    }
    if(g.room<=4&&['upgrade','won'].includes(g.state)){
      for(let i=0;i<4;i++){const x=w*(.2+i*.2),y=h*.22+Math.sin(i*2+this.clock*.4)*25;ellipse(c,x-4,y,2+Math.abs(Math.sin(this.clock*6+i))*3,8,'#e7b4a6');ellipse(c,x+4,y,2+Math.abs(Math.sin(this.clock*6+i))*3,8,'#ebd99b');line(c,[[x,y-5],[x,y+5]],'#977655',2);}

    }
    for(const f of g.foam){c.globalAlpha=Math.min(.48,f.life*.25);circle(c,f.x,f.y,f.r,'#b7e5ec');c.globalAlpha=.65;for(let i=0;i<7;i++){const a=i*TAU/7+this.clock*.2;sparkle(c,f.x+Math.cos(a)*f.r*.7,f.y+Math.sin(a)*f.r*.7,3,'#f4ffff');}c.globalAlpha=1;}
    for(let i=0;i<g.mods.drones;i++){
      const a=g.dronePhase+i*TAU/g.mods.drones,x=g.player.x+Math.cos(a)*75,y=g.player.y+Math.sin(a)*75;
      ellipse(c,x,y+6,17,8,'#284c4324');ellipse(c,x,y,17,13,'#d7e8de');ellipse(c,x,y-3,14,9,'#88ae9e');rect(c,x-5,y-7,10,3,1,'#f1ecae');
    }
    if(g.state==='playing'||g.state==='ready')this.vacuum(c);
    for(const s of g.hostileShots){ellipse(c,s.x+2,s.y+5,9,4,'#6d537529');circle(c,s.x,s.y,9,'#ad7047');circle(c,s.x-2,s.y-3,3,'#e0ae75');}
    for(const h of g.hazards){
      c.save();circle(c,h.x,h.y,h.r,'#f5a65438');c.strokeStyle='#d87232';c.lineWidth=3;c.setLineDash([7,5]);c.beginPath();c.arc(h.x,h.y,h.r,0,TAU);c.stroke();c.setLineDash([]);
      c.beginPath();c.arc(h.x,h.y,h.r*(1-h.life/h.duration),0,TAU);c.stroke();line(c,[[h.x-7,h.y],[h.x+7,h.y]],'#974624',3);line(c,[[h.x,h.y-7],[h.x,h.y+7]],'#974624',3);c.restore();
    }
    for(const e of g.enemies)if(e.alive&&!e.trapped&&e.type==='charger'&&(e.windup>0||e.dash>0)){
      c.save();c.globalAlpha=.45;c.setLineDash([10,7]);line(c,[[e.x,e.y],[e.x+Math.cos(e.chargeAngle)*186,e.y+Math.sin(e.chargeAngle)*186]],'#d66c35',e.r*1.2);c.restore();
    }
    drawRoomFeatures(c,g,this.clock,true);
    for(const e of g.enemies)if(e.alive){
      if(e.type==='fan'&&(e.windup>0||e.gust>0)){c.save();c.globalAlpha=e.gust>0?.45:.23;c.strokeStyle='#6fa4b0';c.lineWidth=3;const a=e.gustAngle;for(let i=-1;i<=1;i++){c.beginPath();c.moveTo(e.x,e.y);c.lineTo(e.x+Math.cos(a+i*.35)*220,e.y+Math.sin(a+i*.35)*220);c.stroke();}c.restore();}
      if(e.type==='boss'&&e.act==='warning'){c.save();c.translate(e.x,e.y);c.rotate(e.chargeAngle);c.fillStyle='#d8804330';c.fillRect(0,-e.r,245,e.r*2);c.strokeStyle='#c96f39';c.lineWidth=2;c.setLineDash([10,7]);c.strokeRect(0,-e.r,245,e.r*2);c.setLineDash([]);for(let x=55;x<240;x+=60)line(c,[[x-7,-9],[x+4,0],[x-7,9]],'#b96536',2);c.restore();}
      if(e.type==='boss'&&e.vulnerable){c.strokeStyle='#e5bd64';c.lineWidth=3;c.beginPath();c.ellipse(e.x,e.y+18,e.r+16,18,0,0,TAU);c.stroke();}
    }
    const entities=[...g.enemies.filter(e=>e.alive).map(e=>({y:e.y,draw:()=>this.enemy(c,e)})),{y:g.player.y,draw:()=>this.raccoon(c,g.player)}];
    entities.sort((a,b)=>a.y-b.y).forEach(e=>e.draw());
    drawGadgets(c,g,this.clock,this.assets);
    for(const s of g.shots){
      c.save();c.globalAlpha=.24;line(c,[[s.x-s.vx*.065,s.y-s.vy*.065],[s.x,s.y]],s.foamBoosted?'#d2ffff':s.weapon==='foam'?'#a8dce6':'#efd59a',s.r*1.3);c.restore();
      c.save();c.translate(s.x,s.y);c.rotate(this.clock*13);circle(c,2,3,s.r+1,'#526d5555');circle(c,0,0,s.r,s.weapon==='foam'?'#a8dce6':s.weapon==='scatter'?'#98c993':'#e8ad75');circle(c,-s.r*.23,-s.r*.25,s.r*.72,s.weapon==='foam'?'#e4faf8':'#edc58d');
      for(let i=0;i<5;i++){const a=i*TAU/5;rect(c,Math.cos(a)*s.r*.6-2,Math.sin(a)*s.r*.6-2,5,4,1,i%2?'#a3b882':'#8ca09a');}c.restore();
      if(s.foamBoosted){c.strokeStyle='#d2ffff';c.lineWidth=3;c.beginPath();c.arc(s.x,s.y,s.r+4,0,TAU);c.stroke();}
      sparkle(c,s.x-s.vx*.02,s.y-s.vy*.02,5,'#f4eed0');
    }
    for(const r of this.rings){if(active)r.life-=dt;const progress=1-r.life/r.max;c.globalAlpha=Math.max(0,r.life/r.max);c.strokeStyle='#fff8c9';c.lineWidth=5*(1-progress)+1;c.beginPath();c.arc(r.x,r.y,r.r*progress,0,TAU);c.stroke();c.lineWidth=2;c.strokeStyle='#bdd99b';c.beginPath();c.arc(r.x,r.y,r.r*progress*.86,0,TAU);c.stroke();}c.globalAlpha=1;this.rings=this.rings.filter(r=>r.life>0);
    for(const p of this.particles){
      if(active){p.life-=dt;if(p.type==='suck'){const dx=g.player.x+Math.cos(g.player.angle)*32-p.x,dy=g.player.y+Math.sin(g.player.angle)*32-p.y;p.x+=dx*dt*12;p.y+=dy*dt*12;}else{p.x+=p.vx*dt;p.y+=p.vy*dt;p.vx*=Math.exp(-3*dt);p.vy*=Math.exp(-3*dt);}}
      c.globalAlpha=Math.max(0,p.life/p.max);if(p.type==='suck')circle(c,p.x,p.y,p.r,'#b59a71');else sparkle(c,p.x,p.y,p.r,p.color);
    }c.globalAlpha=1;this.particles=this.particles.filter(p=>p.life>0);
    if(g.state==='clearing'){
      c.strokeStyle='#fffbea';c.lineWidth=8*(1-g.sweep/1.6);c.globalAlpha=Math.max(0,1-g.sweep/1.6);c.beginPath();c.arc(g.player.x,g.player.y,g.sweep*760,0,TAU);c.stroke();c.globalAlpha=1;
      for(let i=0;i<14;i++){const x=45+hash(i,2)*(w-90),y=45+hash(i,3)*(h-90);sparkle(c,x,y,(Math.sin(g.sweep*5+i)+1)*5,'#fffced');}
    }
    this.feedback.draw(c,g);c.restore();
  }
  vacuum(c,back=false){
    const g=this.game,p=g.player,r=g.mods.range*(g.mods.doublemouth?.75:1),a=p.angle+(back?Math.PI:0);
    if(g.mods.doublemouth&&!back)this.vacuum(c,true);
    c.save();c.translate(p.x,p.y);c.rotate(a);
    const gradient=c.createRadialGradient(25,0,0,25,0,r);gradient.addColorStop(0,'#fff8c047');gradient.addColorStop(.5,'#f2efb226');gradient.addColorStop(1,'#fbf7d000');
    c.fillStyle=gradient;c.beginPath();c.moveTo(23,0);c.arc(0,0,r,-g.mods.cone,g.mods.cone);c.closePath();c.fill();
    for(let i=0;i<8;i++){
      const t=(this.clock*1.8+i*.137)%1,d=35+(1-t)*(r-40),s=Math.sin(i*41)*g.mods.cone*.8;
      c.globalAlpha=Math.sin(t*Math.PI)*.4;line(c,[[Math.cos(s)*d,Math.sin(s)*d],[Math.cos(s)*(d+10),Math.sin(s)*(d+10)]],'#fffdf0',1.7);
    }c.globalAlpha=1;c.restore();
  }
  raccoon(c,p){this.art.player(c,p);}
  enemy(c,e){
    if(['charger','lobber','mender','fan'].includes(e.type)){
      this.art.enemy(c,e);
      const x=e.x,y=e.y-e.r*.9;
      if(e.type==='fan'){c.save();c.translate(x+18,e.y);c.rotate(this.clock*(e.gust>0?20:3));for(let i=0;i<4;i++){c.rotate(Math.PI/2);ellipse(c,0,-12,6,13,'#9ecac8');}circle(c,0,0,7,'#ca9b5d');c.restore();}
      else if(e.type==='charger'){
        line(c,[[x-17,y+8],[x-12,y-8],[x-4,y+5]],'#bd7540',6);line(c,[[x+4,y+5],[x+12,y-8],[x+17,y+8]],'#bd7540',6);
      }else if(e.type==='lobber'){
        ellipse(c,x,y,24,9,'#d6a464');ellipse(c,x,y-5,16,10,'#829877');circle(c,x+8,y-10,6,'#b58d62');
      }else{
        rect(c,x-16,y-7,32,13,4,'#d9e7b7');line(c,[[x-5,y],[x+5,y]],'#558a60',3);line(c,[[x,y-5],[x,y+5]],'#558a60',3);
        line(c,[[x+20,e.y+9],[x+28,e.y-14]],'#997149',5);rect(c,x+22,e.y-23,17,12,3,'#b4c789');
        if(e.repairFlash>0){c.save();c.globalAlpha=e.repairFlash/.45;c.strokeStyle='#91b577';c.lineWidth=3;c.beginPath();c.arc(e.x,e.y,145*(1-e.repairFlash/.45),0,TAU);c.stroke();c.restore();}
      }
      return;
    }
    if(['blob','spitter','runner','splitter','mini','boss'].includes(e.type)){
      this.art.enemy(c,e);
      const x=e.x,y=e.y-e.r;
      if(e.type==='runner')line(c,[[x-12,y],[x,y-9],[x+12,y]],'#e4b36c',5);
      if(e.type==='splitter'||e.type==='mini'){circle(c,x-7,y,6,'#99b875');circle(c,x+7,y,6,'#bdd09a');}
      if(e.type==='boss'){
        line(c,[[x-19,y],[x-16,y-16],[x-5,y-8],[x,y-23],[x+8,y-9],[x+18,y-16],[x+19,y]],'#e1b365',5);
        c.save();c.translate(x+e.r,e.y);c.rotate(e.toss?-.7:.2);rect(c,-12,-13,24,29,5,'#ab8965');ellipse(c,0,-13,12,5,'#dbc199');ellipse(c,0,-12,8,3,'#765440');c.restore();
      }return;
    }
    const g=this.game,boss=e.type==='boss',r=e.r,bob=Math.sin(e.phase)*2,armor=e.armor>0;
    const theme={blob:{body:'darkD',part:'dark',eye:'eye_human'},spitter:{body:'blueA',part:'blue',eye:'eye_human'},runner:{body:'redE',part:'red',eye:'eye_angry_red'},splitter:{body:'greenF',part:'green',eye:'eye_human'},boss:{body:'yellowD',part:'yellow',eye:'eye_angry_red'},mini:{body:'greenF',part:'green',eye:'eye_human'}}[e.type];
    ellipse(c,e.x+1,e.y+r*.6,r*.95,r*.32,'#30433830');c.save();c.translate(e.x,e.y+bob);
    const step=Math.sin(e.phase*1.8)*.15;
    this.sprite(c,`leg_${theme.part}D`,-r*.42,r*.51,r*.55,r*.6,step);this.sprite(c,`leg_${theme.part}D`,r*.42,r*.51,r*.55,r*.6,-step);
    this.sprite(c,`arm_${theme.part}B`,-r*.88,-r*.02,r*.5,r*.9,-.4+step);this.sprite(c,`arm_${theme.part}B`,r*.88,-r*.02,r*.5,r*.9,.4-step);
    if(e.hit>0)c.filter='brightness(1.55)';
    this.sprite(c,`body_${theme.body}`,0,-r*.12,r*1.9,r*1.95);c.filter='none';
    if(armor){
      c.save();c.globalAlpha=.65*e.armor/e.maxArmor;c.fillStyle='#9c8990';c.beginPath();c.ellipse(0,-r*.18,r*.86,r*.83,0,Math.PI,TAU);c.fill();
      line(c,[[-r*.6,-r*.72],[-r*.2,-r*.46],[-r*.35,-r*.22]],'#e0cdb54d',3);c.restore();
    }
    if(e.type==='splitter'||e.type==='mini'){this.sprite(c,theme.eye,0,-r*.3,r*.74,r*.74);}
    else{this.sprite(c,theme.eye,-r*.36,-r*.31,r*.57,r*.57);this.sprite(c,theme.eye,r*.36,-r*.31,r*.57,r*.57);}
    this.sprite(c,e.type==='spitter'?'mouthB':armor?'mouth_closed_sad':'mouthA',0,r*.22,r*.65,r*.32);
    if(e.type==='runner'){this.sprite(c,'detail_red_horn_small',-r*.5,-r*.95,12,15,-.4);this.sprite(c,'detail_red_horn_small',r*.5,-r*.95,12,15,.4);}
    if(boss){this.sprite(c,'detail_yellow_antenna_small',-r*.4,-r*1.02,18,30,-.3);this.sprite(c,'detail_yellow_antenna_small',r*.4,-r*1.02,18,30,.3);}
    if(e.windup>0){c.strokeStyle='#eeb86d';c.lineWidth=3;c.beginPath();c.arc(0,2,r+10,0,TAU*(1-e.windup/.75));c.stroke();sparkle(c,0,-r-18,6,'#fce4a2');}
    if(e.slow>0){c.strokeStyle='#b9eff7';c.lineWidth=2;c.beginPath();c.arc(0,0,r+3,0,TAU);c.stroke();}
    c.restore();
    if(e.hp<e.maxHp||e.armor<e.maxArmor||boss){const y=e.y-r-20,w=boss?58:34;rect(c,e.x-w/2,y,w,4,2,'#4552494a');rect(c,e.x-w/2,y,w*Math.max(0,e.hp/e.maxHp),4,2,'#e29886');if(e.armor>0)rect(c,e.x-w/2,y-4,w*e.armor/e.maxArmor,2,1,'#c6b194');}
  }
}
