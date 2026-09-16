export async function loadAssets(){
  const response=await fetch('assets/kenney/manifest.json');
  if(!response.ok)throw new Error('素材清单加载失败');
  const manifest=await response.json(),images={};
  const files=manifest.files.map(f=>({key:f.file.replace('.png',''),url:`assets/kenney/${f.file}`}));
  for(const name of ['raccoon','pressure','scatter','foam'])files.push({key:name,url:`assets/original/${name}.svg`});
  for(const name of ['courtyard','cleaner','mudling','vacuum','moss-spitter','mud','tea-courtyard-v2','greenhouse-v1','workshop-v1','foam-v1','scatter-v1','duck-v1','cleaner-suction-v1','cleaner-recoil-v1'])files.push({key:`art-${name}`,url:`assets/illustrated/${name}.webp`});
  await Promise.all(files.map(async f=>{const img=new Image();img.src=f.url;await img.decode();images[f.key]=img;}));
  return images;
}
