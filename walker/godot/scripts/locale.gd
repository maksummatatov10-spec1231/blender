class_name Locale

const RU := {
	"title": "СТРАННИК",
	"sub": "Долина четырёх ветров",
	"play": "Играть",
	"settings": "Настройки",
	"quit": "Выйти",
	"back": "Назад",
	"resume": "Продолжить",
	"settings_title": "Настройки",
	"lang": "Язык",
	"gfx": "Графика",
	"bye_title": "До встречи",
	"bye": "Горы будут ждать тебя.",
	"hint": "WASD — ходьба · Shift — бег · Пробел — прыжок · мышь — осмотр · V — вид 1/3 лицо · E — табличка · Esc — меню",
	"press_e": "E — прочитать",
	"close": "Закрыть",
	"gfx_low": "Низкая",
	"gfx_medium": "Средняя",
	"gfx_high": "Высокая",
	"gfx_ultra": "Ультра",
	"loc_valley": "Долина",
	"loc_village": "Деревня",
	"loc_forest": "Лес",
	"loc_mountain": "Горы",
	"loc_falls": "Водопад",
	"loc_lake": "Озеро",
	"compass": ["С", "СВ", "В", "ЮВ", "Ю", "ЮЗ", "З", "СЗ"],
	"sign_village": ["Деревня Тихий Дол", "Здесь пахнет дымом и хлебом. Жители ушли в поля, но двери открыты для путника."],
	"sign_forest": ["Старый лес", "Сосны здесь помнят первые тропы. Не сходи с пути, когда туман спускается с гор."],
	"sign_mountain": ["Предгорье", "Выше — только ветер и камни. Перевал закрыт снегом до самой весны."],
	"sign_falls": ["Серебряный водопад", "Вода падает с высоты тринадцати шагов. Говорят, если умыться ею, дорога станет легче."],
	"sign_lake": ["Озеро Тихое", "Самая глубокая вода долины. Рыбаки говорят, что на дне спит старый валун."],
}

const EN := {
	"title": "WANDERER",
	"sub": "Valley of the Four Winds",
	"play": "Play",
	"settings": "Settings",
	"quit": "Quit",
	"back": "Back",
	"resume": "Resume",
	"settings_title": "Settings",
	"lang": "Language",
	"gfx": "Graphics",
	"bye_title": "See you",
	"bye": "The mountains will wait for you.",
	"hint": "WASD — walk · Shift — run · Space — jump · mouse — look · V — 1st/3rd person · E — sign · Esc — menu",
	"press_e": "E — read",
	"close": "Close",
	"gfx_low": "Low",
	"gfx_medium": "Medium",
	"gfx_high": "High",
	"gfx_ultra": "Ultra",
	"loc_valley": "Valley",
	"loc_village": "Village",
	"loc_forest": "Forest",
	"loc_mountain": "Mountains",
	"loc_falls": "Waterfall",
	"loc_lake": "Lake",
	"compass": ["N", "NE", "E", "SE", "S", "SW", "W", "NW"],
	"sign_village": ["Quiet Dale Village", "It smells of smoke and bread here. The villagers are out in the fields, but the doors are open to travellers."],
	"sign_forest": ["The Old Forest", "These pines remember the first trails. Stay on the path when the fog rolls down from the mountains."],
	"sign_mountain": ["The Foothills", "Above there is only wind and stone. The pass is sealed with snow until spring."],
	"sign_falls": ["Silver Falls", "The water drops thirteen paces. They say washing your face here makes the road easier."],
	"sign_lake": ["Quiet Lake", "The deepest water in the valley. Fishermen say an old boulder sleeps at the bottom."],
}

static func t(key: String, lang: String) -> String:
	var table: Dictionary = RU if lang == "ru" else EN
	if table.has(key):
		return str(table[key])
	return key

static func t_arr(key: String, lang: String) -> Array:
	var table: Dictionary = RU if lang == "ru" else EN
	if table.has(key) and table[key] is Array:
		return table[key]
	return ["", ""]
