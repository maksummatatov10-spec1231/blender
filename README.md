# GEO STORY v2 — «Красный идёт в гости к Синему»

Полная замена первого «Гео-цирка». Сделано **только в Blender 5.3.0** (установщик из релиза `install` репозитория `blender1231`), Cycles CPU, 240 кадров / 24 fps / 10 с, 960×540.

Ветка: https://github.com/maksummatov10-spec1231/blender/tree/arena/758e5991-blender

## Сюжет
1. **1–88** — Красный выходит из тёплого кирпичного домика и **забывает закрыть дверь**; идёт по изогнутой каменной дорожке и проходит **сквозь** садовую арку, развёрнутую по оси +X.
2. **89–128** — Синий робот с другим лицом выглядывает из круглого окна своей высокой голубой башни и видит Красного.
3. **129–168** — Красный подходит, стучит; Синий открывает дверь.
4. **169–204** — Красный заходит внутрь, Синий протягивает подарочную коробку.
5. **205–240** — Крышка открывается, из коробки вылетают ленты и конфетти, оба робота радуются.

## Что внутри
- 2 разных дома, реальные дверные/оконные проёмы, двери на петлях, скруглённые углы, bevel + weighted normals.
- Процедурные текстуры Brick / Noise / Voronoi / Wave с bump, мягкие area-светильники, AgX, деноузинг.
- 2 скелета по 23 кости, 6 IK-констрейнтов, shape keys мимики, походка с anticipation / follow-through / squash & stretch.
- 5 камерных планов через timeline markers, движение камер, Motion Paths, BEZIER/AUTO_CLAMPED F-кривые.
- 90 элементов хлопушки, покадровая лаборатория на 240 кадров, 16 автоматических QA-проверок.

## Главное исправление ошибки с кольцом
Арка повёрнута `(0, 90°, 0)`, отверстие смотрит по **+X** — по направлению движения. На кадре **54** проверены все деформированные вершины Красного: максимальный радиус **1.722 < 1.85** внутреннего радиуса. Робот проходит **сквозь** арку, а не рядом. Доказательства: `renders/v2/screenshots/arch_pass.png`, `qa_trajectory.png`, `lab/data/qa.json`.

## Файлы
| Файл | Назначение |
| --- | --- |
| `geo_story_v2.blend` | исходная сцена Blender 5.3.0 |
| `geo_story_v2.mp4` | финальный H.264 мультфильм |
| `renders_v2_frames.zip` | архив 240 кадров |
| `renders/v2/screenshots/` | раскадровка, все кадры, скелет, Motion Paths, QA, арка |
| `lab/` | лаборатория: кадры, позиции, кости, траектории, проверки, источники |
| `scripts/build_scene_v2.py` | полный билдер сцены |
| `scripts/render_v2.py`, `encode_v2_mp4.py`, `make_v2_archive.py`, `verify_v2_screens.py`, `make_qa_plot.py` | рендер, сборка MP4, архив, диагностика |

## Воспроизведение
```bash
BIN="$PWD/tools/blender-5.3.0-linux-x64/blender"
export LD_LIBRARY_PATH="$PWD/tools/syslibs22:$PWD/tools/blender-5.3.0-linux-x64/lib:$LD_LIBRARY_PATH"
export LIBGL_DRIVERS_PATH="$PWD/tools/syslibs22/dri"
export BLENDER_USER_CONFIG="$PWD/tools/blender_config"
"$BIN" --background --factory-startup --python scripts/build_scene_v2.py
"$BIN" --background geo_story_v2.blend --python scripts/render_v2.py -- 1 240 14 100 0 renders/v2/frames
tools/venv/bin/python scripts/encode_v2_mp4.py
tools/venv/bin/python scripts/make_v2_archive.py
```

Лаборатория открывается через локальный статический сервер из корня репозитория: `/lab/`.

> `geo_cartoon.*`, `renders/frames/` и `RELEASE_NOTES.md` — историческая v1, пользователем не принята. Финальная работа — **v2**.
