# Гео-цирк — мультфильм на Blender 5.3.0

**Blender 5.3.0** (installer из релиза `maksummatatov10-spec1231/blender1231@install`, SHA-256 проверен).

## Что внутри

Куб-робот с настоящим скелетом разбегается, прыгает через золотое кольцо, приземляется, танцует, машет рукой; синий шар скачет по дугам, фиолетовый конус в удивлении кувыркается, а сундук из `сундук.blend` открывается и выбрасывает конфетти. 120 кадров / 24 fps / 5 секунд.

## Техника

* Арматура `HeroRig`: 18 костей, 3 IK-констрейнта, 22 меша на вершинных группах + Armature modifier.
* 12 принципов анимации: squash & stretch с сохранением объёма, anticipation, follow-through, arcs, slow in/out, secondary action, exaggeration, appeal.
* Motion Paths рассчитаны операторами Blender и дополнительно запечены в видимые кривые траекторий.
* F-кривые сглажены через `bpy_extras.anim_utils.action_get_channelbag_for_slot` (в 5.3 `Action.fcurves` удалён).
* Cycles CPU + деноузинг; в `.blend` сохранены 24 сэмпла и motion blur 180°.
* 11/11 автоматических проверок пройдено: конечные координаты, непрерывность дуг, объём, достижимость IK, кадрирование, покрытие кадров.

## Ассеты релиза

* `geo_cartoon.mp4` — видео
* `geo_cartoon.blend` — сцена
* `contact_sheet.png`, `all_frames.png`, `skeleton.png`, `motion_paths.png`, `skeleton_overlay.png`, `frame_0001.png`, `frame_0044.png`, `frame_0120.png` — изображения
* `renders_frames.zip` — все 120 PNG-кадров

Полная «лаборатория» с покадровым отслеживанием: `lab/index.html` в репозитории.

Ссылка на ветку: https://github.com/maksummatatov10-spec1231/blender/tree/arena/758e5991-blender
