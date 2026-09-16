// Alpha bounds measured from the packaged assets. Anchor X sits between the
// planted feet; anchor Y is the lowest planted foot, not the source canvas edge.
export const CHARACTER_FRAMES={
 cleaner:{crop:[0,0,302,384],footX:215},
 'cleaner-suction-v1':{crop:[44,37,276,295],footX:188},
 'cleaner-recoil-v1':{crop:[39,31,284,296],footX:200}
};
export function framePlacement(key,height=74){const f=CHARACTER_FRAMES[key],scale=height/f.crop[3];return {crop:f.crop,x:-(f.footX-f.crop[0])*scale,y:-height,width:f.crop[2]*scale,height};}
