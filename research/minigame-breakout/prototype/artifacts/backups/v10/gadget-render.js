const TAU=Math.PI*2;
function oval(c,x,y,rx,ry,color){c.fillStyle=color;c.beginPath();c.ellipse(x,y,rx,ry,0,0,TAU);c.fill();}
export function drawGadgets(c,g,clock,assets){
 const fx=g.gadgets;if(g.state!=='playing'&&g.state!=='paused')return;
 c.save();
 for(const bucket of fx.buckets){
  oval(c,bucket.x,bucket.y+13,20,7,'#43362444');c.fillStyle='#568578';c.fillRect(bucket.x-16,bucket.y-10,32,28);oval(c,bucket.x,bucket.y-10,17,6,'#284e46');
  if(bucket.stored>0)oval(c,bucket.x,bucket.y-8,13,Math.min(11,3+bucket.stored*.15),'#b69761');
  c.strokeStyle='#f7d380';c.lineWidth=3;c.strokeRect(bucket.x-6,bucket.y-3,12,12);
  c.strokeStyle='#83bbae66';c.lineWidth=1;c.beginPath();c.arc(bucket.x,bucket.y,60+Math.sin(clock*4)*10,0,TAU);c.stroke();
 }
 for(const d of fx.discs){
  c.save();c.translate(d.x,d.y);c.rotate(clock*12);oval(c,0,3,21,16,'#2c51463b');oval(c,0,0,21,19,d.wet>0?'#bcf0ef':'#e1c88b');oval(c,0,0,12,12,'#668d78');
  c.strokeStyle='#fff5cf';c.lineWidth=3;for(let i=0;i<8;i++){const a=i*TAU/8;c.beginPath();c.moveTo(Math.cos(a)*13,Math.sin(a)*13);c.lineTo(Math.cos(a)*21,Math.sin(a)*21);c.stroke();}c.restore();
 }
 for(const b of fx.bubbles){
  const grad=c.createRadialGradient(b.x-8,b.y-9,1,b.x,b.y,b.r);grad.addColorStop(0,'#ffffff18');grad.addColorStop(.8,'#cbeff526');grad.addColorStop(1,'#b9eaff99');
  oval(c,b.x,b.y,b.r,b.r,grad);c.strokeStyle=b.charged?'#ffe978':'#e7fcff';c.lineWidth=2;c.beginPath();c.arc(b.x,b.y,b.r,0,TAU);c.stroke();
  c.strokeStyle='#f9c7dc';c.beginPath();c.arc(b.x,b.y,b.r-2,.1,1.7);c.stroke();oval(c,b.x-8,b.y-10,5,3,'#ffffffbb');if(b.cargo>0)oval(c,b.x,b.y+6,9,6,'#b49464');
 }
 if(g.mods.mop&&fx.mop){
  const m=fx.mop;c.strokeStyle='#eadfc16b';c.lineWidth=2;c.beginPath();c.arc(g.player.x,g.player.y,60,fx.phase-1.2,fx.phase);c.stroke();
  c.save();c.translate(m.x,m.y);c.rotate(fx.phase);c.strokeStyle='#69513b';c.lineWidth=5;c.beginPath();c.moveTo(-17,0);c.lineTo(15,0);c.stroke();
  oval(c,0,0,21,14,'#4e857e');for(let i=-3;i<=3;i++){c.strokeStyle=i%2?'#f4e7c0':'#b1d9ca';c.lineWidth=3;c.beginPath();c.moveTo(-16,i*3);c.quadraticCurveTo(0,i*6,18,i*3);c.stroke();}c.restore();
 }
 if(g.mods.duck){
  const d=fx.duck;oval(c,d.x,d.y+10,17,6,'#47392335');c.save();c.translate(d.x,d.y+Math.sin(clock*8)*1.3);if(d.x>g.player.x)c.scale(-1,1);
  const img=assets['art-duck-v1'];const scale=Math.min(60/img.width,48/img.height);c.drawImage(img,-img.width*scale/2,-img.height*scale/2,img.width*scale,img.height*scale);c.restore();
 }
 for(const arc of fx.arcs){
  c.globalAlpha=Math.min(1,arc.life*5);c.shadowColor='#9adffb';c.shadowBlur=10;c.strokeStyle='#d5faff';c.lineWidth=3;c.beginPath();c.moveTo(arc.a.x,arc.a.y);
  for(let i=1;i<6;i++){const t=i/6;c.lineTo(arc.a.x+(arc.b.x-arc.a.x)*t+Math.sin(i*18)*7,arc.a.y+(arc.b.y-arc.a.y)*t+Math.cos(i*13)*7);}c.lineTo(arc.b.x,arc.b.y);c.stroke();
 }c.shadowBlur=0;
 for(const pop of fx.pops){c.globalAlpha=Math.min(1,pop.life*3);c.strokeStyle='#d7faff';c.lineWidth=4;c.beginPath();c.arc(pop.x,pop.y,pop.r*(1-pop.life/.6),0,TAU);c.stroke();}
 c.restore();
}
