import test from 'node:test';
import assert from 'node:assert/strict';
import {createGameKeyboard} from '../src/keyboard.js';

function setup(){
  let state='playing',shots=0,pauses=0;
  const keys=new Set();
  const keyboard=createGameKeyboard({state:()=>state,keys,fire:()=>shots++,pause:()=>pauses++});
  const event=(code,repeat=false)=>({code,repeat,prevented:false,preventDefault(){this.prevented=true;}});
  return {keyboard,keys,event,setState:s=>state=s,shots:()=>shots,pauses:()=>pauses};
}
test('firing across a clear and reward screen never becomes button activation or scrolling',()=>{
  const h=setup(),press=h.event('Space');h.keyboard.down(press);
  assert.equal(h.shots(),1);assert.ok(press.prevented);assert.ok(h.keys.has('Space'));
  for(const state of ['clearing','upgrade','paused','won','lost']){
    h.setState(state);
    for(const repeat of [false,true]){const e=h.event('Space',repeat);h.keyboard.down(e);assert.ok(e.prevented);}
    const release=h.event('Space');h.keyboard.up(release);assert.ok(release.prevented);assert.ok(!h.keys.has('Space'));
  }
  assert.equal(h.shots(),1);
});
test('menu Enter/Tab and ready-screen Space remain native; resumed combat can fire',()=>{
  const h=setup();h.setState('upgrade');
  for(const code of ['Enter','Tab']){const e=h.event(code);h.keyboard.down(e);assert.equal(e.prevented,false);}
  h.setState('ready');const start=h.event('Space');h.keyboard.down(start);assert.equal(start.prevented,false);
  h.setState('playing');h.keyboard.down(h.event('Space'));h.keyboard.down(h.event('Space',true));assert.equal(h.shots(),1);
  h.keyboard.up(h.event('Space'));assert.equal(h.keys.size,0);
});
test('holding Escape pauses once instead of oscillating between pause and play',()=>{
  const h=setup();h.keyboard.down(h.event('Escape'));h.keyboard.down(h.event('Escape',true));assert.equal(h.pauses(),1);
});
