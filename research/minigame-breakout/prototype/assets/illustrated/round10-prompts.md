# Core action keyframes — round 10
Tool: built-in image_gen, edit mode. Reference: project cleaner.png.
Generated output is project artwork, not CC0/open-source artwork.

Shared prompt: Edit the exact same full-body raccoon; preserve fur, face, proportions, green overalls, cream rolled sleeves, striped tail and watercolor storybook style. Three-quarter view facing right. No gun or other props (game attaches its own), no shadow, text or sheet, true transparent alpha. Entire character contained, feet near bottom and consistent scale/camera.

- Suction: knees bent, torso leaning slightly right, both paws extended together at waist as if gripping an invisible vacuum hose, concentrated happy face and perked ears.
- Recoil: knees planted wide, head/shoulders lean left, both arms right as if bracing a shot, briefly squinted eyes and puffed cheeks; lively rather than painful.

Sources under /Users/houguanqun/.codex/generated_images/01a08f67-9b0c-7980-947e-c95ccfca3640/:
- exec-8c3c17f1-e3d5-4040-a833-215889cffede.png → cleaner-suction-v1.webp
- exec-52e1e435-fa9e-4084-8465-35f18798e68d.png → cleaner-recoil-v1.webp

Processing: Sharp width 360, WebP quality 92. Both source images verified to have alpha. Anchors implemented in IllustratedArt.player; render-time action state has brace/recoil/recover, suction onset smoothing, pause freeze and reset. The shot itself fires immediately, without animation input delay. Existing idle art is retained.

Final alignment: alpha bounds are cropped at draw time via src/character-frames.js, normalized to 74px height and a shared foot baseline. Browser fixture artifacts/actions-v10.html verified idle/suction/recoil side by side.
