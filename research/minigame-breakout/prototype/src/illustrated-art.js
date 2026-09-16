import {framePlacement} from './character-frames.js?v=11';
// Art presentation only: collision, dirt quantities and victory stay in Game.
import {ActionAnimation} from './action-animation.js?v=11';
const TAU=Math.PI*2;
function oval(c,x,y,rx,ry,color){c.fillStyle=color;c.beginPath();c.ellipse(x,y,rx,ry,0,0,TAU);c.fill();}
export class IllustratedArt {
  constructor(assets,game){
    this.assets=assets;this.game=game;this.action=new ActionAnimation();this.last={x:game.player.x,y:game.player.y};this.stride=0;this.motion=0;this.kick=0;this.recoil=0;this.fill=0;
    this.mask=document.createElement('canvas');this.mask.width=game.cols*3;this.mask.height=game.rows*3;
    this.surface=document.createElement('canvas');this.surface.width=game.width;this.surface.height=game.height;this.sc=this.surface.getContext('2d');this.mudPattern=this.sc.createPattern(assets['art-mud'],'repeat');
    this.mc=this.mask.getContext('2d');this.pixels=this.mc.createImageData(this.mask.width,this.mask.height);
  }
  update(dt,active){
    const p=this.game.player,d=Math.hypot(p.x-this.last.x,p.y-this.last.y);this.last={x:p.x,y:p.y};
    this.action.update(dt,{active,gathering:this.game.state==='playing'?(this.game.gathering||0):0});
    if(!active)return;
    this.motion=d>.08&&d<40?1:0;
    if(this.motion)this.stride+=d*.13;
    this.kick*=Math.exp(-18*dt);this.recoil*=Math.exp(-15*dt);this.fill+=(p.ammo/this.game.mods.capacity-this.fill)*(1-Math.exp(-12*dt));
  }
  sprite(c,key,x,y,width,height,flip=false){
    const image=this.assets[`art-${key}`],scale=Math.min(width/image.width,height/image.height);
    c.save();c.translate(x,y);if(flip)c.scale(-1,1);c.drawImage(image,-image.width*scale/2,-image.height*scale/2,image.width*scale,image.height*scale);c.restore();
  }
  background(c,w,h,theme='garden'){
    const image=this.assets[theme==='garden'?'art-courtyard':`art-${theme}-v1`];
    // Portrait crops the sides instead of stretching circular floor mosaics.
    const scale=Math.max(w/image.width,h/image.height);
    c.drawImage(image,(w-image.width*scale)/2,(h-image.height*scale)/2,image.width*scale,image.height*scale);
    c.strokeStyle='#614b33';c.lineWidth=5;c.strokeRect(2.5,2.5,w-5,h-5);
  }
  dirt(c){
    const g=this.game,{width,height}=this.mask,data=this.pixels.data;
    const sample=(x,y)=>x<2||y<2||x>=g.cols-2||y>=g.rows-2?0:g.dirt[y*g.cols+x];
    // Bilinear density field keeps the existing simulation grid but removes
    // the regularly scalloped cell outlines from the visible mud surface.
    for(let y=0;y<height;y++)for(let x=0;x<width;x++){
      const gx=x/3-.5+Math.sin(y*.65+x*.31)*.16,gy=y/3-.5+Math.sin(x*.73-y*.27)*.16,ix=Math.floor(gx),iy=Math.floor(gy),fx=gx-ix,fy=gy-iy;
      const a=sample(ix,iy)*(1-fx)+sample(ix+1,iy)*fx,b=sample(ix,iy+1)*(1-fx)+sample(ix+1,iy+1)*fx;
      const density=a*(1-fy)+b*fy,i=(y*width+x)*4;
      const grain=((x*13+y*17)%11)-5;
      data[i]=111+grain;data[i+1]=96+grain;data[i+2]=76+grain;
      data[i+3]=Math.round(Math.min(1,Math.max(0,(density-.015)*2.2))*255);
    }
    this.mc.putImageData(this.pixels,0,0);
    const sc=this.sc;sc.clearRect(0,0,g.width,g.height);sc.drawImage(this.mask,0,0,g.width,g.height);sc.globalCompositeOperation='source-in';sc.fillStyle=this.mudPattern;sc.fillRect(0,0,g.width,g.height);sc.globalCompositeOperation='source-over';c.drawImage(this.surface,0,0);
    // Recognisable litter rather than abstract light dots.
    for(let row=3;row<g.rows-3;row+=3)for(let col=3;col<g.cols-3;col+=3){
      const amount=g.dirt[row*g.cols+col];if(amount<.55)continue;
      const n=(col*17+row*7)%5,x=col*20+10+Math.sin(col*91+row)*17,y=row*20+10+Math.cos(row*73+col)*17;c.save();c.translate(x,y);c.rotate(n*.8);
      if(n<3){oval(c,0,0,7,3.5,n===0?'#c99754':'#b1a074');c.strokeStyle='#786240';c.lineWidth=.8;c.beginPath();c.moveTo(-6,0);c.lineTo(6,0);c.stroke();}
      else{c.fillStyle='#ddcdb0';c.fillRect(-4,-3,8,6);c.fillStyle='#b9a384';c.fillRect(-3,1,6,1);}
      c.restore();
    }
  }
  player(c,p){
    const g=this.game,flip=Math.cos(p.angle)<0,bob=this.motion?Math.sin(this.stride)*1.8:0;
    oval(c,p.x,p.y+16,23,8,'#493a293d');
    c.save();c.translate(p.x-Math.cos(p.angle)*this.recoil,p.y-Math.sin(p.angle)*this.recoil);
    const fullness=this.fill;
    if(p.invincible>0&&g.state==='playing'){c.strokeStyle='#fff4c9';c.lineWidth=2;c.beginPath();c.ellipse(0,15,25,9,0,0,TAU);c.stroke();}
    const drawTool=()=>{
      c.save();c.translate(Math.cos(p.angle)*(24-this.kick),Math.sin(p.angle)*20+5);c.rotate(p.angle);c.scale(1+fullness*.09,1+fullness*.16);
      if(flip)c.scale(1,-1);
      if(g.weapon==='pressure')this.sprite(c,'vacuum',0,0,58,31);
      else this.sprite(c,g.weapon+'-v1',0,0,64,34);
      c.restore();
    };
    // Aim behind the body occludes the tool, instead of painting over the face.
    if(Math.sin(p.angle)<-.35)drawTool();
    c.save();c.rotate((this.motion?Math.sin(this.stride)*.055:0)-Math.cos(p.angle)*this.recoil*.018);c.scale(1+this.recoil*.013,1-this.recoil*.012);const key=this.action.pose==='recoil'?'cleaner-recoil-v1':['suction','brace'].includes(this.action.pose)?'cleaner-suction-v1':'cleaner';const img=this.assets['art-'+key];const frame=framePlacement(key);c.save();if(flip)c.scale(-1,1);c.drawImage(img,...frame.crop,frame.x,16+bob+frame.y,frame.width,frame.height);c.restore();c.restore();
    if(Math.sin(p.angle)>=-.35)drawTool();
    c.restore();
    if(g.state==='playing'&&p.ammo>=20){
      c.strokeStyle=p.ammo>=g.mods.capacity*.8?'#e3a539':'#fff1ba';c.lineWidth=3;c.beginPath();c.ellipse(p.x,p.y+19,27,10,0,Math.PI*.1,Math.PI*.1+TAU*.8*p.ammo/g.mods.capacity);c.stroke();
    }
  }
  enemy(c,e){
    const r=e.r,bob=Math.sin(e.phase)*1.5;
    oval(c,e.x,e.y+r*.62,r*.85,r*.29,'#493a293d');
    c.save();
    // A narrow light outline separates brown bodies from brown mud.
    c.shadowColor='#fff0c6';c.shadowBlur=2;c.shadowOffsetY=0;
    if(e.hit>0)c.filter=`brightness(${1+(e.impactStrength||.04)*2*Math.min(1,e.hit/.14)})`;
    c.translate(e.x,e.y);const squash=e.hit>0?(e.impactStrength||.04)*Math.sin(Math.min(1,e.hit/.14)*Math.PI*.8):Math.sin(e.phase)*.025;const wide=e.type==='charger'?1.2:e.type==='mender'?1.12:1,tall=e.type==='lobber'?1.2:e.type==='charger'?.85:1;const wind=e.windup>0?.08:0;c.scale((1+squash+wind)*wide,(1-squash-wind)*tall);c.translate(-e.x,-e.y);
    this.sprite(c,['spitter','mender','fan'].includes(e.type)?'moss-spitter':'mudling',e.x,e.y-r*.25+bob,r*2.5,r*2.85,e.x>this.game.player.x);
    c.restore();
    if(e.armor>0){
      c.strokeStyle='#dfc18a';c.lineWidth=3;c.beginPath();c.arc(e.x,e.y+r*.2,r+3,.15, .15+Math.PI*.8*e.armor/e.maxArmor);c.stroke();
    }
    if(e.windup>0){
      c.strokeStyle='#e77c46';c.lineWidth=3;c.beginPath();c.arc(e.x,e.y,r+9,0,TAU*(1-e.windup/.75));c.stroke();
      c.fillStyle='#773718';c.font='bold 18px sans-serif';c.textAlign='center';c.fillText('!',e.x,e.y-r-17);
    }
    if(e.slow>0){c.strokeStyle='#b9eff7';c.lineWidth=2;c.beginPath();c.arc(e.x,e.y,r+3,0,TAU);c.stroke();}
    if(e.hp<e.maxHp){c.fillStyle='#57432c';c.fillRect(e.x-17,e.y-r-20,34,4);c.fillStyle='#ee9973';c.fillRect(e.x-17,e.y-r-20,34*Math.max(0,e.hp/e.maxHp),4);}
  }
}
