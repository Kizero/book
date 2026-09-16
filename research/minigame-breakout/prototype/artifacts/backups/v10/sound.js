// Procedural material sound: filtered air, motor and bounded transient layers.
export class CleaningSound {
 constructor(){this.enabled=false;this.ctx=null;this.voices=0;this.lastCue={};}
 setEnabled(value){
  this.enabled=value;
  if(value&&!this.ctx){
   const c=this.ctx=new (window.AudioContext||window.webkitAudioContext)();
   this.master=c.createGain();this.master.gain.value=.65;this.master.connect(c.destination);
   this.motor=c.createOscillator();this.motor.type='triangle';this.gain=c.createGain();this.gain.gain.value=0;this.motor.connect(this.gain);this.gain.connect(this.master);this.motor.start();
   this.noise=c.createBuffer(1,c.sampleRate*2,c.sampleRate);const a=this.noise.getChannelData(0);for(let i=0;i<a.length;i++)a[i]=Math.random()*2-1;
   this.air=c.createBufferSource();this.air.buffer=this.noise;this.air.loop=true;this.filter=c.createBiquadFilter();this.filter.type='bandpass';this.filter.frequency.value=850;this.filter.Q.value=.7;this.airGain=c.createGain();this.airGain.gain.value=0;this.air.connect(this.filter);this.filter.connect(this.airGain);this.airGain.connect(this.master);this.air.start();
  }
  if(value)this.ctx.resume().catch(()=>{});
  if(this.ctx)this.master.gain.setTargetAtTime(value?.65:0,this.ctx.currentTime,.04);
 }
 update(g){if(!this.ctx)return;const t=this.ctx.currentTime,active=this.enabled&&g.state==='playing',fill=g.player.ammo/g.mods.capacity,collect=Math.min(1,(g.gathering||0)/90);this.motor.frequency.setTargetAtTime(58+fill*55,t,.12);this.gain.gain.setTargetAtTime(active?.008:0,t,.07);this.filter.frequency.setTargetAtTime(550+fill*650+collect*300,t,.1);this.airGain.gain.setTargetAtTime(active?.008+collect*.045:0,t,.07);}
 tone(freq,t,duration,type='sine',volume=.045){
  if(this.voices>=16)return;const c=this.ctx,o=c.createOscillator(),v=c.createGain();this.voices++;o.onended=()=>this.voices--;o.type=type;o.frequency.setValueAtTime(freq,t);o.frequency.exponentialRampToValueAtTime(Math.max(30,freq*.55),t+duration);v.gain.setValueAtTime(.0001,t);v.gain.exponentialRampToValueAtTime(volume,t+.008);v.gain.exponentialRampToValueAtTime(.0001,t+duration);o.connect(v);v.connect(this.master);o.start(t);o.stop(t+duration+.01);
 }
 cue(type){
  if(!this.enabled||!this.ctx)return;const c=this.ctx,t=c.currentTime;if(t-(this.lastCue[type]??-10)<.07)return;this.lastCue[type]=t;
  if(type==='fire'){
   this.tone(125,t,.18,'triangle',.11);const n=c.createBufferSource(),f=c.createBiquadFilter(),v=c.createGain();n.buffer=this.noise;f.type='lowpass';f.frequency.setValueAtTime(1800,t);f.frequency.exponentialRampToValueAtTime(200,t+.14);v.gain.setValueAtTime(.08,t);v.gain.exponentialRampToValueAtTime(.0001,t+.16);n.connect(f);f.connect(v);v.connect(this.master);n.start(t);n.stop(t+.17);return;
  }
  const notes=type==='clear'?[523,659,784,1047]:type==='shell'?[1250,820]:type==='bucket-toss'?[330,247,196]:[620,930];
  notes.forEach((f,i)=>this.tone(f,t+i*.085,type==='clear'?.3:.12,'sine',type==='bucket-toss'?.07:.035));
 }
}
