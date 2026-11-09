---
date: 2026-11-09
topic: Free human-drawn pixel-art hero sprite sheets to remix into the Roofline night guard
tags: [roofline, sprites, assets, licensing, neo-geo]
status: complete
---

# Free hero assets for Roofline

Licenses were read from each OpenGameArt (OGA) page HTML (fetched with curl on 2026-11-09). Images were viewed by me. Scratch root: `/private/tmp/claude-501/-Users-spot-Code-ArcadeGame/06a12133-dc4e-43e6-b08a-169b50911a0f/scratchpad/assets/`. Not found: an ansimuz "Gunner" pack (search surfaced only the OGA tag "Gunners, Pugilists, and Swordsmen"). The itch.io Cyber Soldier (heosphorus) is a paid pack with no CC0 statement, so it is rejected.

## Ranking

1. Space Police Hero (Master484), CC-BY 4.0 / OGA-BY 4.0. Best fit.
2. Warped City hero (ansimuz), CC0. Best licence, but the character is an acrobatic young woman in a yellow jacket.
3. Space Soldier (M484 Games), CC0. Clean, but small and plain.
4. Space Soldier sprite sheet 32x32 (Luca Pixel), CC0. Weakest art.

## 1. Space Police Hero
- Author: Master484 (OGA user `master484`). URL: https://opengameart.org/content/space-police-hero
- License line on page: "License(s): OGA-BY 4.0 CC-BY 4.0". Attribution Instructions: 'If you use these graphics, mention "Master484" as the original author, and if possible, put a link to my OGA profile.'
- Credit line: `Hero sprites by Master484 (opengameart.org/users/master484), CC-BY 4.0`
- Frames: about 38-42 px tall boxes, irregular sizes (unverified exact; sheet 968x577, `spacepolice_blue.png`). Animations: idle, duck, jump, hit, 8-way aim in standing, jump, duck and run poses, normal run (6 frames), second run with gun movement (6 frames), a gun-recoil twin for every frame, death frames. The author says it was made for a Contra/Turrican-style Amiga game, so shooting while running is built in.
- Quality 8/10. Fit 8/10: helmeted armour with a gun, side view, outlined, Amiga-era shading close to SNES. The overall silhouette is a bulky space marine.
- Remix: recolour the blue armour to navy. Replace the helmet with a cap (about 6 px of head rework across every frame, since the sheet is modular with "same cut point" frames). Add a flashlight to the gun: this is a laser cue, so extend the muzzle with a lens and beam pixels. Palette is small (blue ramp plus grey). Needs a trim into uniform cells.
- Local: `.../assets/space-police-hero/spacepolice_blue.png`

## 2. Warped City (hero)
- Author: ansimuz. URLs: https://opengameart.org/content/warped-city and https://ansimuz.itch.io/warped-city
- License lines: OGA page "License(s): CC0". itch page: "Creative Commons Zero v1.0 Universal". Caveat from OGA page: the music (Pascal Belisle) is separate and needs credit; we do not use it. No credit required for art. Optional line: `Hero base: Warped City by ansimuz (CC0)`.
- Frames: size not stated on either page (unverified, probably about 48 px cells). Animations (author's list): walk, shoot, run-shoot, run, jump, idle, hurt, crouch, climb, back-jump. Also a 16x16 tileset, 3-layer parallax, 2 enemies, 4 vehicles, all CC0.
- Quality 8/10. Fit 5/10: cyberpunk-themed but the hero is a woman with purple hair, yellow jacket and bare legs. The preview shows run-shoot with an extended arm and pistol, which is a good flashlight-hold pose. The preview also shows acrobatic frames not wanted.
- Remix: full redraw of jacket, hair (cap), legs (trousers). Heavier than #1.
- I downloaded only the preview (`01-sprites_2.png`, 700x500, promo layout, not the real strip) and the cover. The real sheet is inside the OGA zip or itch download; I did not fetch it, so frame size and count are unverified.
- Local: `.../assets/warped-city/01-sprites_2.png`, `.../assets/warped-city/cover_21.png`

## 3. Space Soldier (M484 Games)
- Author: Master484. URL: https://opengameart.org/content/space-soldier-m484-games
- License line: "License(s): CC0". Page text: "These graphics are in the Public Domain. Attribution is not needed."
- Frame size: 50x50 cells (sheet text: "The inside area of each animation box is 50*50"); character about 36-40 px tall, sheet 530x580. Animations: stand, duck, jump, damage, 8-frame run cycle, both directions (24 frames), yellow and green themes. Armour uses only 2 colours. No separate shooting frames, though the gun is held out in all frames.
- Quality 7/10. Fit 6/10: a sci-fi gunner, flat shading, easy to recolour.
- Remix: navy recolour, cap, flashlight on the gun, laser FX drawn separately. Plain, so it needs added shading to reach Mega Man X cel look.
- Local: `.../assets/space-soldier-m484/M484SpaceSoldier.png`

## 4. Space Soldier sprite sheet 32x32 (Luca Pixel)
- Author: Luca Pixel (OGA user `luca-pixel`; page shows drakzlin as uploader). URL: https://opengameart.org/content/space-soldier-sprite-sheet-32x32
- License line: "License(s): CC0". No credit text found on the page.
- Frames: 32x32. Animations: walk, run, jump, crouch, attack, idle, death. Includes enemies, boxes, bonuses.
- Quality 5/10. Fit 4/10: orange suit, thick outlines, tiny and crude next to the frozen background.
- Local: `.../assets/space-soldier-luca/all_sprites.png`

## Recommendation
Use Space Police Hero (#1). It is the only one with run (two 6-frame versions), jump, duck, aim and recoil frames in one sheet, and the 8-way aim poses cover the flashlight laser. CC-BY needs a credit on the attract screen: `Hero sprites by Master484, CC-BY 4.0`. Note OGA-BY 4.0 is the same attribution requirement; if CC-BY is a problem, fall back to #2 (CC0), at a higher remix cost. Next step before committing: cut one run frame and check height and the cap rework.
