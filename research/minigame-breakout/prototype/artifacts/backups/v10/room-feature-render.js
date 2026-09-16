const TAU=Math.PI*2;
export function drawRoomFeatures(c,g,clock,front=false){
 const stage=g.stage;if(!stage)return;const f=stage.flavor,w=g.width,h=g.height;c.save();
 if(!front){
  if(f.sky==='warm'){c.fillStyle='#ffd68d12';c.fillRect(0,0,w,h);}if(f.sky==='evening'){c.fillStyle='#c6c2eb15';c.fillRect(0,0,w,h);}
  if(f.belt){const y=h*.7;c.fillStyle='#426c6140';c.fillRect(45,y-40,w-90,80);c.strokeStyle='#eadbb4';c.lineWidth=3;for(const side of [-1,1]){c.beginPath();c.moveTo(45,y+side*39);c.lineTo(w-45,y+side*39);c.stroke();}c.strokeStyle='#fff3c190';c.lineWidth=2;for(let i=0;i<12;i++){const x=50+((i*85+clock*f.belt*45)%(w-100)+(w-100))%(w-100);c.beginPath();c.moveTo(x-f.belt*7,y-10);c.lineTo(x+f.belt*7,y);c.lineTo(x-f.belt*7,y+10);c.stroke();}}
  if(f.wind){const y=h*.48;c.strokeStyle='#ecf9e899';c.lineWidth=2;for(let i=0;i<10;i++){const x=50+((i*105+clock*f.wind*65)%(w-100)+(w-100))%(w-100),yy=y+Math.sin(i*7)*35;c.beginPath();c.moveTo(x,yy);c.quadraticCurveTo(x+f.wind*14,yy-5,x+f.wind*27,yy);c.stroke();}}
 }else{
  for(const p of stage.parcels){if(p.opened){c.globalAlpha=.45;c.strokeStyle='#88ae72';c.lineWidth=2;c.beginPath();c.arc(p.x,p.y,18,0,TAU);c.stroke();c.globalAlpha=1;continue;}
   c.fillStyle='#493c3233';c.beginPath();c.ellipse(p.x,p.y+16,25,8,0,0,TAU);c.fill();const grad=c.createLinearGradient(p.x-22,p.y-20,p.x+22,p.y+20);grad.addColorStop(0,'#f2dba9');grad.addColorStop(1,'#b68c53');c.fillStyle=grad;c.beginPath();c.roundRect(p.x-22,p.y-20,44,38,9);c.fill();c.strokeStyle='#7f6846';c.lineWidth=2;c.stroke();c.strokeStyle='#688771';c.lineWidth=6;c.beginPath();c.moveTo(p.x-21,p.y-4);c.lineTo(p.x+21,p.y-4);c.moveTo(p.x,p.y-19);c.lineTo(p.x,p.y+17);c.stroke();c.fillStyle='#fff4c8';c.font='bold 17px system-ui';c.textAlign='center';c.fillText('♻',p.x,p.y+5);c.strokeStyle='#fff4c8';c.lineWidth=3;c.beginPath();c.arc(p.x,p.y,29,-Math.PI/2,-Math.PI/2+p.progress*TAU);c.stroke();
  }
  if(f.sky==='rain'){c.strokeStyle='#d7edee55';c.lineWidth=1;for(let i=0;i<28;i++){const x=(i*137+clock*30)%w,y=(i*83+clock*150)%h;c.beginPath();c.moveTo(x,y);c.lineTo(x-3,y+10);c.stroke();}}
  if(f.sky==='petals'){for(let i=0;i<12;i++){const x=(i*127+clock*12)%w,y=(i*73+clock*17)%h;c.fillStyle='#efd3bda0';c.beginPath();c.ellipse(x,y,4,2,clock+i,0,TAU);c.fill();}}
 }
 c.restore();
}
