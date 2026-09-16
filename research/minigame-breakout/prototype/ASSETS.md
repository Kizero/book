# 素材来源与使用说明

本版选用 Kenney 的四套 CC0 素材。官方页面与下载包内 `License.txt` 均已核查。只打包实际挑选的 61 个 PNG，共约 98 KB；游戏运行时从本地加载，不依赖远程素材地址。

| 来源 | 本项目用途 | 包内许可证 |
|---|---|---|
| [Animal Pack Remastered](https://kenney.nl/assets/animal-pack-remastered) | `dog.png` 作为浣熊头像的底图，另绘圆耳、眼罩与表情；不是将原始狗头像宣称为现成浣熊素材。另保留兔子、熊猫作后续角色备选。 | [LICENSE-animal.txt](assets/kenney/LICENSE-animal.txt) |
| [Top-down Shooter](https://kenney.nl/assets/top-down-shooter) | 地板、草地、树丛、盆栽、木桌、箱子、玻璃边框、地面纸屑；未使用该包的人类枪手角色。 | [LICENSE-topdown.txt](assets/kenney/LICENSE-topdown.txt) |
| [Monster Builder Pack](https://kenney.nl/assets/monster-builder-pack) | 怪物身体、手脚、眼睛、嘴、触角；在绘制时组合并加上泥壳、步行动画和受击反馈。 | [LICENSE-monster.txt](assets/kenney/LICENSE-monster.txt) |
| [UI Pack 2.0](https://kenney.nl/assets/ui-pack) | 装备选中标记和界面图形备选；界面布局、排版和面板样式为本项目编写。 | [LICENSE-ui.txt](assets/kenney/LICENSE-ui.txt) |

作者：Kenney / Kenney Vleugels。许可：[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)。检索与获取日期：2026-09-13。原文件路径、项目路径及 SHA-256 保存在 [manifest.json](assets/kenney/manifest.json)。包内许可允许个人、教育及商业项目使用；此处仍保留鸣谢与原始许可。

## 本项目新增部分

`assets/original/pressure.svg`、`scatter.svg`、`foam.svg` 是为清洁主题编写的矢量清洁器，分别表现高压、散射与泡沫喷射，不冒充从开源包找到的现成吸尘器。

`assets/original/raccoon.svg` 嵌入 Animal Pack 的 CC0 底图，并组合本项目绘制的浣熊特征。其余同目录 SVG 为本项目编写的升级图标。角色身体、环绕机器人、污渍、光照、粒子与特效由绘制代码完成。未使用生成式图片、商用游戏截图或来源不明素材。

## 选择与局限

选择同一作者的平涂素材，使颜色、轮廓和细节密度较接近；清洁器与图标按相同方向补齐。未将写实素材、像素地牢和扁平卡通混用。

这些素材为当前可玩版本提供统一基础，不是完整的专属角色动画资产。地图已有三个主题，但仍采用边界摆件与开放场地，未把装饰物伪装成已实现碰撞的障碍物。

## 2026-09-14 · 第一关美术样板

`assets/illustrated/` 为本项目使用内置 image_gen 生成的新画稿，**不属于 Kenney 素材，不宣称 CC0 或开源许可**。包含庭院、浣熊、泥团怪、苔藓喷射怪、基础吸尘器和泥层纹理。完整提示词保存在同目录 `prompts.json`。原始 PNG 保留为美术源文件；运行时使用 WebP，透明角色仅裁去透明边距并缩小，保留 alpha。

庭院用于 garden 场景；主角和基础吸尘器、两种基础敌人替换对应旧图。其余武器、后续场景与敌人暂时保留原素材，不能称为全游戏美术统一完成。竖屏按比例裁切庭院两侧，避免把圆形地砖图案拉长。后续正式资源打包应只包含运行时 WebP，不包含源 PNG。

新的渲染模块 `src/illustrated-art.js` 只读取游戏状态：污渍外观由已有密度网格生成遮罩；碰撞、清洁率和过关判定不变。主角位移驱动走动起伏，静止停止，朝后瞄准时工具被身体遮挡。当前仍是单张角色贴图，不是完整方向动画。

## 2026-09-14 · 组合装备

`assets/original/bubble.svg`、`electric.svg`、`mop.svg`、`duck.svg` 为本项目新增的 SVG 图标，沿用现有线稿图标风格。气泡、电弧、拖把、小鸭采用 `src/gadget-render.js` 的 Canvas 图形，不标为 Kenney 或 AI 生成图片。小鸭当前仍是简化的动画图形，后续可替换为匹配庭院的正式美术。

组合扩展新增 brush / bucket / compressor / doublemouth / returner / backpack 六枚 SVG 图标。刷盘、回收桶、带电泡泡和泡沫轨迹继续使用项目 Canvas 绘制，没有新增第三方资源。

2026-09-14：茶会收工背景 `assets/illustrated/tea-courtyard-v2.webp` 为 built-in image_gen 基于原庭院制作；原图和完整最终提示词同目录保存。增加约 197 KB 运行时素材。用于第四关结束渐显，不改变战斗地面或碰撞。

### 2026-09-15 全程画风补齐
`assets/illustrated/greenhouse-v1.webp`、`workshop-v1.webp`、`foam-v1.webp`、`scatter-v1.webp`、`duck-v1.webp`：本项目通过内置 image_gen 生成，**不属于 Kenney CC0 素材**。参考本项目已有 courtyard/vacuum 的绘本风格；以 Sharp 转为 WebP，武器宽 480 px、伙伴宽 320 px，保留透明通道。背景保留原始 1536×1024。

提示词与生成源路径见 `assets/illustrated/round9-prompts.md`。地图中央保持开放，装饰只在边缘，不增加隐形碰撞。

### 核心动作关键帧（第十轮）
`cleaner-suction-v1.webp` 与 `cleaner-recoil-v1.webp` 基于现有角色，经内置 image_gen 生成透明关键姿势；代码统一脚底锚点并驱动吸入／喷射动作。不是新下载的开源资产。提示规格与生成路径见 `assets/illustrated/round10-prompts.md`。
