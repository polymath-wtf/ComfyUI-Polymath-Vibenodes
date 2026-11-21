# Vibenodes для ComfyUI

Ноды для сборки промптов, загрузки медиа и выбора кадров. Категория в ComfyUI: **Vibenode**.
<img width="1280" height="720" alt="Custom Vibe" src="https://github.com/user-attachments/assets/9aedba75-b2ee-4688-8e66-35977b49908a" />

## Vibenode Polyprompt JSON

### Why

Чтобы из n8n в один клик собрать датасет для LoRA с Qwen-Edit: задайте персонажа один раз и меняйте сцену, позу и действие.

<img width="420" alt="Нода Polymath JSON с шаблоном промпта" src="https://github.com/user-attachments/assets/0f1cfd41-a19b-406d-a517-fa36daa0335d" />

<img width="48%" alt="Пример с пандой" src="https://github.com/user-attachments/assets/84f59aba-e121-4ed1-935d-eb130baec933" /> <img width="48%" alt="Панда делает сальто" src="https://github.com/user-attachments/assets/f0b88386-9de0-4e23-a7ac-b5b71a26c389" />

### Example template

```text
{>subject {character} in {scene}, {action}, {pose}}.
{>shot {camera}, lit by {light}}. Inspired by {style}.
```

Имена ключей вы выбираете сами. Запишите их в поле `template` — нода добавит порты:

| Запись | Как работает |
| --- | --- |
| `{key}` | Создаёт вход `key`. Подключите к нему строку — она встанет в промпт на место `{key}`. |
| `{>key}` | Создаёт вход **и выход** `key`. Та же строка попадёт и в промпт, и на отдельный выход. |
| `{>shot {camera}, lit by {light}}` | Создаёт входы `camera` и `light`. Из них собирает фразу, вставляет её в промпт и отдаёт отдельно на выход `shot`. |

**Пример:** введите `{character} in {>scene}`. Подключите через **Text Vibe** строки `panda` к `character` и `forest` к `scene`. Выход `prompt` отдаст `panda in forest`, а выход `scene` — только `forest`. Его можно подключить к другой ноде, которой нужно лишь место действия.

## Установка

В папке `ComfyUI/custom_nodes` выполните:

```sh
git clone https://github.com/polymath-wtf/ComfyUI-Polymath-Vibenodes.git
```

Перезапустите ComfyUI и обновите вкладку. Нужна версия ComfyUI с API V3 (`comfy_api.latest`); дополнительные пакеты устанавливать не требуется.

## Текст и промпты

| Нода | Когда использовать |
| --- | --- |
| **Text Vibe** | Ввести один многострочный промпт. Выход `STRING` сохраняет пробелы и переносы. |
| **Vibenode Prompt Lines** | Перебрать варианты сцены или стиля: каждая непустая строка становится отдельным значением списка. Порядок и повторы сохраняются. |
| **Vibenode Polyprompt JSON** | Собрать полный `prompt` из строковых входов и при необходимости вывести отдельные фрагменты. `{scene}` создаёт вход, `{>scene}` — вход и выход, `{>shot {camera}, {light}}` — выход `shot` с текстом из двух входов. |
| **Vibenode JSON List** | Извлечь варианты из JSON: для `{"scenes":["forest","city"]}` путь `$.scenes` вернёт обе строки через `values`. Также доступны `keys`, `count` и списки `int`/`float` для чисел. В шаблоне `{day}` без кавычек создаёт вход, а `"{day}"` остаётся текстом. |
| **Vibenode Prompt Preview** | После запуска графа пролистать итоговые промпты и скопировать выбранный кнопкой **Copy**. |

## Загрузка медиа

**Load image url** принимает прямую HTTP(S)-ссылку на картинку или страницу файла на tmpfiles.org. Подключите `image` к `Preview Image`; `mask` содержит прозрачность (1 — прозрачный пиксель). Для анимации берётся первый кадр. VHS и Art Venture не требуются. API: `VibenodeLoadImageURL`, вход `url`.

**Локальное хранилище Laravel.** Если в `inputs.url` приходит, например, `http://localhost:8000/storage/ref.png`, укажите адрес доверенного сервера **в окружении ComfyUI**. В Windows Portable добавьте перед запуском Python в `.bat`:

```bat
set "VIBENODE_IMAGE_STORAGE_ORIGIN=http://localhost:8000"
```

Перезапустите ComfyUI. Укажите схему, имя хоста и порт из вашей ссылки, без пути к файлу. Разрешение действует для этого адреса и в превью, и при выполнении графа. Нужна прямая ссылка, которая отдаёт файл без редиректа. `localhost` означает машину или контейнер, где работает ComfyUI; если Laravel запущен отдельно, используйте в ссылке и настройке адрес, доступный из ComfyUI.

**Load video url api** принимает публичную HTTP(S)-ссылку через `path` (поле, STRING-соединение или API). Поддерживает прямые MP4/MOV/WebM/MKV/GIF и страницы скачивания tmpfiles.org. Для декодирования нужен **ComfyUI-VideoHelperSuite**. Частота, размеры, пропуск и лимит кадров, `select_every_nth`, `format`, `meta_batch` и `vae` работают через VHS. Выходы: `IMAGE` (с VAE — `LATENT`), `frame_count`, `audio`, `video_info`. Видео до 1 ГиБ кэшируется по URL в `temp/vibenode-video`. После запуска в ноде доступен плеер исходного файла; для просмотра выбранных кадров подключите `Preview Image`. API: `class_type: VibenodeLoadVideoURL`, ссылка в `inputs.path`.

## Кадры и числовые диапазоны

В **Image Select** и **Frame Select Vibe** номера кадров начинаются с **1**. В старых графах прибавьте 1 к прежним индексам этих двух нод. В **Image Cut Select** параметр `start` — смещение от начала батча (0 — с самого начала).

| Нода | Когда использовать |
| --- | --- |
| **First Frame Vibe** | Взять первый кадр батча как референс. |
| **Last Frame Vibe** | Взять последний кадр, например для начала следующего клипа. |
| **Frame Select Vibe** | Получить один кадр по подключённому `INT`: `index=7` вернёт седьмой кадр. |
| **Vibenode Image Select** | Собрать новый батч по номерам кадров. `4,1,4` вернёт четвёртый, первый и снова четвёртый кадр. |
| **Vibenode Image Cut Select** | Вырезать непрерывный диапазон: `start=0, length=8` берёт первые восемь кадров; `length=-1` — все до конца. `batch` отдаёт их вместе, `frames` — списком по одному. |
| **Vibe Mid Calc** | Равномерно выбрать до 256 точек по целым `start`, `end` и `output count`. Обе границы включены; одна точка даёт `start`. Выходы: список `int` без дробной части, список `float`, строка `indices` и отдельный `INT` на каждую точку. |
| **Vibenode Batch Info** | Передать ширину, высоту и число кадров в другие ноды через выходы `width`, `height`, `count`. |
| **Vibenode Ping Pong** | Сделать петлю без дублирования крайних кадров: `0,1,2,3` превращается в `0,1,2,3,2,1`. |

**Пример: три контрольных кадра.** В **Vibe Mid Calc** по умолчанию `start=1`, `end=16`, `output count=3`. Для видео подключите `frame_count` к `end`, а `indices` — к **Vibenode Image Select**. Из 130 кадров получите `1,65,130`. Если нужен только средний, подключите выход `2` к `index` в **Frame Select Vibe**.
