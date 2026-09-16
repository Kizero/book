// Space belongs to the battle for the whole run, including its result screens.
// Enter/Tab retain native button navigation so firing cannot also pick a reward.
export function createGameKeyboard({state,keys,fire,pause}){
  const movement=new Set(['KeyW','KeyA','KeyS','KeyD','ArrowUp','ArrowDown','ArrowLeft','ArrowRight']);
  return {
    down(e){
      if(e.code==='Escape'){
        e.preventDefault();if(!e.repeat)pause();return;
      }
      if(e.code==='Space'&&state()!=='ready'){
        e.preventDefault();
        if(state()==='playing'){if(!e.repeat)fire();keys.add(e.code);}
        return;
      }
      if(movement.has(e.code)&&state()==='playing'){e.preventDefault();keys.add(e.code);}
    },
    up(e){
      // A key may be released after a state change moved focus to a button.
      if(e.code==='Space'&&state()!=='ready')e.preventDefault();
      keys.delete(e.code);
    }
  };
}
