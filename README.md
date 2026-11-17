# Гео-цирк / Geo Circus

Небольшой мультфильм из геометрических фигур, сделанный в **Blender 5.3.0** (установщик взят из релиза [`maksummatatov10-spec1231/blender1231@install`](https://github.com/maksummatatov10-spec1231/blender1231/releases/tag/install)).

## Файлы

| Файл | Что это |
| --- | --- |
| `geo_cartoon.mp4` | финальная анимация, H.264, 24 fps, 120 кадров (5 с) |
| `geo_cartoon.blend` | исходная сцена: арматура, IK, ключи, Motion Paths, материалы, свет |
| `renders/frames/frame_0001.png … frame_0120.png` | каждый кадр отдельным изображением |
| `renders/screenshots/contact_sheet.png` | раскадровка 12 ключевых кадров |
| `renders/screenshots/all_frames.png` | все 120 кадров на одном листе |
| `renders/screenshots/skeleton.png` | диагностический рендер костей и суставов |
| `renders/screenshots/motion_paths.png` | запеченные траектории |
| `renders/frames.zip` | архив со всеми кадрами |
| `lab/index.html` | «лаборатория» — покадровый просмотр всего |

## Лаборатория

Откройте `lab/index.html` через локальный HTTP-сервер (JSON подгружается `fetch`, поэтому `file://` не подойдёт):

```bash
python3 -m http.server 8000 --bind 0.0.0.0
# затем http://localhost:8000/lab/
```

Лаборатория показывает на каждом кадре: все объекты, все кости, деформированные центры, траектории, скорости, F-кривые, 11 автоматических проверок, принципы анимации, все изображения и источники исследования.

## Как это сделано

* **Скелет**: `HeroRig`, 18 костей, 3 IK-констрейнта (стопы + рука), 22 меша со 100%-ми вершинными группами и модификатором Armature.
* **Принципы**: squash & stretch с сохранением объёма (`xy = 1/sqrt(z)`), anticipation, follow-through антенны, arcs, slow in/out (`BEZIER` + `AUTO_CLAMPED`), secondary action, exaggeration.
* **Траектории**: `bpy.ops.object.paths_calculate` / `bpy.ops.pose.paths_calculate` + покадровый bake в светящиеся кривые `Path_*`.
* **Blender 5.3 API**: `Action.fcurves` удалён — используется `bpy_extras.anim_utils.action_get_channelbag_for_slot(action, slot)`.
* **Рендер**: Cycles CPU, 12 сэмплов + OpenImageDenoise (в `.blend` сохранены 24 сэмпла и motion blur 180° для перерендера), 768×432 в финальной PNG-последовательности.
* **Сундук**: реквизит из лежащего в репозитории `сундук.blend`, с заменой отсутствующих текстур на процедурные материалы.

## Скрипты

```bash
scripts/build_scene.py      # сцена, риг, анимация, экспорт JSON, .blend
scripts/render_frames.py    # PNG-последовательность всех кадров
scripts/verify_screens.py   # скриншоты скелета / траекторий
scripts/make_contact_sheet.py
scripts/encode_mp4.py
```

Blender лежит в игнорируемой `tools/` (архив 406 944 100 байт, SHA-256 `dacb8264197a3f7fda6001285a5a506fc97ee943881261c2c3bd63c882f22e05`).

## Ссылки

* Ветка: https://github.com/maksummatatov10-spec1231/blender/tree/arena/758e5991-blender
* Релиз с файлами: https://github.com/maksummatatov10-spec1231/blender/releases/tag/geo-cartoon-v1.0
