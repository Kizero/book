export const CLEAN_TARGET = 90;
export const WEAPONS = [
  {id:'pressure',name:'橘子汽水',tag:'高压弹球',color:'#eaa657',description:'把整舱垃圾压成大弹球。攒得越满，打得越痛。',icon:'pressure'},
  {id:'scatter',name:'薄荷旋风',tag:'三联散射',color:'#75aa82',description:'宽口吸入，三发齐射。近身打散一群小麻烦。',icon:'scatter'},
  {id:'foam',name:'蓝莓泡泡',tag:'泡沫喷射',color:'#8496c8',description:'每发消耗 20 点。留下泡沫，持续清洁并减速。',icon:'foam'}
];
export const ROOMS = [
 {name:'薄荷后院',theme:'garden',subtitle:'薄荷花园 · 午后',types:['blob','blob','blob','blob','spitter']},
 {name:'花圃捣蛋鬼',theme:'garden',subtitle:'薄荷花园 · 花圃',types:['blob','blob','spitter','blob','runner','blob','runner']},
 {name:'茶会备餐区',theme:'garden',subtitle:'薄荷花园 · 备餐区',types:['spitter','blob','runner','blob','splitter','blob','spitter','runner']},
 {name:'滚滚大扫除',theme:'garden',subtitle:'薄荷花园 · 茶会前夕',types:['boss','runner','blob','splitter','spitter','blob','runner','blob']},
 {name:'玻璃暖房',theme:'greenhouse',subtitle:'蓝莓温室 · 种植区',types:['splitter','runner','spitter','blob','splitter','runner','spitter','blob','blob']},
 {name:'花园守护战',theme:'greenhouse',subtitle:'蓝莓温室 · 守护行动',types:['boss','splitter','runner','spitter','blob','runner','splitter','spitter','blob']},
 {name:'快递小径',theme:'garden',subtitle:'薄荷花园 · 冲撞初见',tip:'冲撞怪先亮出直线，再冲过来。横向让开，或用泡泡打断。',types:['fan','charger','runner','blob','blob','spitter','splitter','blob','runner','blob']},
 {name:'雨点苗圃',theme:'garden',subtitle:'薄荷花园 · 留意落点',tip:'橙色圆圈是即将落下的泥团，离开圈子就能躲开。',types:['fan','lobber','charger','spitter','runner','blob','splitter','blob','runner','blob','blob']},
 {name:'补壳维修站',theme:'workshop',subtitle:'橘子工坊 · 补壳小队',tip:'拿刷子的补壳怪会修复附近泥壳。先处理它，或把怪引出修补范围。',types:['mender','mender','charger','lobber','splitter','runner','spitter','blob','blob','runner','blob','blob']},
 {name:'打翻颜料桶',theme:'workshop',subtitle:'橘子工坊 · 混合骚动',tip:'冲撞和落泥会同时出现，留一条横向撤退的路。',types:['boss','charger','charger','lobber','mender','splitter','splitter','runner','spitter','blob','blob','runner','blob']},
 {name:'暖房大派对',theme:'greenhouse',subtitle:'蓝莓温室 · 全员捣蛋',tip:'把怪聚到泡泡和泡沫旁，再用垃圾弹打开连锁。',types:['mender','fan','lobber','lobber','charger','charger','splitter','splitter','spitter','runner','runner','blob','blob','blob']},
 {name:'收工前的狂欢',theme:'greenhouse',subtitle:'蓝莓温室 · 最后行动',tip:'两只大块头带队！清到 90% 或清空捣蛋鬼，都能收工。',types:['boss','boss','fan','lobber','charger','charger','splitter','splitter','spitter','runner','runner','blob','blob','blob','blob']}
];
export const UPGRADES = [
 {id:'brush',name:'弹簧刷盘',icon:'brush',category:'弹射 · 最高 III',description:'掷出撞墙折返的刷盘，沾到泡沫后一路铺开。升级扩大刷地范围、增强伤害。'},
 {id:'bucket',name:'磁力回收桶',icon:'bucket',category:'回收 · 最高 III',description:'把周围垃圾收拢入桶。近吸、弹球或泡泡打包完成回收；升级扩大范围。'},
 {id:'compressor',name:'超大压缩仓',icon:'compressor',category:'改造 · 唯一',description:'发射间隔增加 80%；弹球变大 60%，伤害增加 50%，多穿透两只怪。'},
 {id:'doublemouth',name:'双头吸嘴',icon:'doublemouth',category:'改造 · 唯一',description:'吸入距离缩短 25%，同时吸入前后两个方向。'},
 {id:'returner',name:'回旋喷嘴',icon:'returner',category:'改造 · 唯一',description:'存活的弹球转向飞回。接回时返还该发弹药的 25%，每颗只结算一次。'},
 {id:'backpack',name:'泡泡背包',icon:'backpack',category:'改造 · 唯一',description:'将 30% 吸地回收量改装成身后泡泡，其余补入弹舱；泡泡满员时恢复正常回收。'},
 {id:'bubble',name:'肥皂泡泡机',icon:'bubble',category:'打包 · 最高 III',description:'吹泡泡包住小怪；垃圾弹引爆泡泡并连锁清地。升级缩短间隔、增强爆泡。'},
 {id:'electric',name:'静电毛刷',icon:'electric',category:'导电 · 最高 III',description:'周期电弧清地并减速怪物；沿泡沫传导，小鸭可作中继。升级增强放电。'},
 {id:'mop',name:'旋转拖把',icon:'mop',category:'接力 · 最高 III',description:'绕身刷地推怪；接住弹球再击出。升级扩大刷地范围、增强接触伤害。'},
 {id:'duck',name:'小鸭清洁伙伴',icon:'duck',category:'伙伴 · 最高 III',description:'清理遗漏污渍、补充弹药，搬运附近泡泡。升级扩大清理范围。'},
 {id:'wide',name:'大口吸吸',icon:'wide',category:'吸入',description:'吸入更宽、更远，剥泥壳速度提升 22%。'},
 {id:'power',name:'高压打包',icon:'power',category:'弹药',description:'垃圾弹伤害提升 35%，弹球也变大。'},
 {id:'chain',name:'清洁连锁',icon:'chain',category:'连锁',description:'击破冲击更远、更强，可以引发连环清场。'},
 {id:'battery',name:'加大收纳舱',icon:'battery',category:'弹药',description:'容量增加 40 点。高压与散射可攒更大一发。'},
 {id:'pierce',name:'穿透滤芯',icon:'pierce',category:'弹道',description:'每颗弹药可多穿过一只怪物。'},
 {id:'bounce',name:'弹力橡胶',icon:'bounce',category:'弹道',description:'弹药碰到墙面会反弹，最多叠加两次。'},
 {id:'recycle',name:'循环利用',icon:'recycle',category:'补给',description:'每次发射返还 25% 弹药，最多返还 50%。'},
 {id:'skates',name:'溜溜清洁鞋',icon:'skates',category:'移动',description:'移动快 15%，经过的脚下会变干净。'},
 {id:'drone',name:'扫地小卫星',icon:'drone',category:'伙伴',description:'增加一台环绕机器人，擦地并撞伤附近怪物。'},
 {id:'magnet',name:'强力分离器',icon:'magnet',category:'吸入',description:'垃圾转化的弹药增加 45%，吸入略微变远。'},
 {id:'frost',name:'冰凉清洁剂',icon:'frost',category:'控制',description:'弹药使怪物减速 2 秒，方便边走边清。'},
 {id:'heart',name:'暖暖修理包',icon:'heart',category:'补给',description:'恢复全部体力；本局吸入效率提升 10%。'}
];
