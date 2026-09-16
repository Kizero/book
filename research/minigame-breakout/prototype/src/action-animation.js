// Render-time only. Shots remain immediate; no input delay or gameplay freeze.
export class ActionAnimation{
 constructor(){this.reset();}
 reset(){this.age=99;this.sucking=0;this.power=0;}
 fire(amount){this.age=0;this.power=Math.min(1,amount/100);}
 update(dt,{active,gathering=0}){if(!active)return;this.age+=dt;this.sucking+=((gathering>1?1:0)-this.sucking)*(1-Math.exp(-12*dt));}
 get pose(){return this.age<.055?'brace':this.age<.2?'recoil':this.sucking>.25?'suction':'idle';}
 get kick(){if(this.age>.32)return 0;return Math.sin(Math.min(1,this.age/.32)*Math.PI)*(3+this.power*4);}
}
