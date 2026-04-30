# hwiki

CLI для Confluence Server/DC — чтение, запись и двусторонний sync wiki-страниц через терминал.

## Репозиторий

`git@github.com:wiliam/hwiki.git` — ветка `main`.
Установка для разработки: `pipx install -e .` (из папки проекта).
Пользовательская установка: `pipx install 'git+ssh://git@github.com/wiliam/hwiki.git@master'`

## Конфиг

`~/.hwiki_config` (JSON):
```json
{
  "host": "https://confluence.example.com",
  "user": "your.username",
  "default_space": "ENG",
  "timeout": 20
}
```

Токен хранится в OS keyring (service=`"hwiki"`, key=`user`). Сохранить: `hwiki login`.

## Архитектура

```
hwiki/
  main.py              # argparse + auto-discovery операций через walk_packages
  _http.py             # httpx + Bearer auth + retry/backoff + Retry-After
  client.py            # ConfluenceClient: get_page, search_pages, create_page,
                       #   update_page, upload_attachment, get_children,
                       #   get_attachment_content, resolve_page_id
  _storage_to_md.py    # Confluence storage XHTML → markdown (lxml + _Ctx dataclass)
  _md_to_storage.py    # markdown → Confluence storage XHTML (markdown-it-py)
  _manifest.py         # sync manifest: load/save .hwiki.json, make_slug, page_filename
  _frontmatter.py      # read/write YAML front-matter в md файлах
  _text.py             # parse_page_id, parse_display_url
  _types.py            # TypedDict: Page, SearchHit, Attachment
  utils.py             # KEYRING_SERVICE, CONFIG_PATH
  operations/
    login.py           # hwiki login
    get.py             # hwiki get
    search.py          # hwiki search
    create.py          # hwiki create
    update.py          # hwiki update
    attach.py          # hwiki attach
    pull.py            # hwiki pull (sync wiki → local)
    push.py            # hwiki push (sync local → wiki)
```

## Команды

```bash
hwiki login
hwiki get <id|url> [--raw] [--json] [-o file.md]
hwiki search '<cql>' [-n 25] [--json]
hwiki create --space KEY --title T [--file f.md | --stdin] [--parent id]
hwiki update <id|url> [--title T] [--file f.md | --stdin] [--version auto|N]
hwiki attach <id|url> file [--message comment]

# Sync
hwiki pull <id|url> [-n depth] [-d ./wiki/] [--attachments [PATH]]
hwiki push [file|id|url] [-d ./wiki/] [--dry-run] [--force]
```

`<id|url>` принимает: числовой id, `viewpage.action?pageId=N`, `/pages/N`, `/display/SPACE/Title`.

## Sync-архитектура

`hwiki pull` скачивает страницу + дочерние (-n уровней) в локальную папку:
- Файлы: `{page_id}-{slug}.md` (транслитерированный kebab-case title)
- Front-matter: `id`, `title`, `space`, `version`, `parent_id`
- Manifest: `.hwiki.json` с метаданными и `content_hash` каждой страницы
- Ссылки на страницы из pull-сета → `./other_id-slug.md` (локальные)
- Ссылки на внешние страницы → wiki URL
- `--attachments` → скачивает файлы в `attachments/`, md использует локальные пути
- Повторный pull без `--attachments` сохранит локальные пути если файлы уже есть

`hwiki push` обновляет изменённые страницы:
- Определяет изменение по `content_hash` (сравнение с manifest)
- Детектит конфликт (wiki version > local version) — пропускает без `--force`
- Поддерживает пофайловый push: `hwiki push file.md` или `hwiki push 12345`
- `--dry-run` показывает что будет сделано без реальных изменений

## Конвертер storage → md

`_storage_to_md.py` использует `_Ctx` dataclass для передачи контекста (без глобальных переменных):
- `link_map`: `{page_id → filename}` для внутренних ссылок при pull
- `title_index`: `{(space, title) → page_id}` для резолва ссылок
- `attachment_dir_rel`: путь для локальных изображений из аттачментов
- `page_id`, `host`, `space_key`: для URL-генерации

Поддерживаемые элементы: h1-h6, p, strong/em/code, a, img (ri:url и ri:attachment),
ul/ol (до 2 уровней), table (md для простых, HTML для rowspan/colspan), blockquote,
hr, code block (ac:structured-macro code с CDATA), callout-макросы (info/warning/note/tip
с заголовком), expand (→ `<details>`), section/column/layout (flatten), panel/details
(flatten), aura-tab-collection/aura-tab (→ #### секции), task-list/task (→ `- [ ]`/`- [x]`),
div (flatten), ac:link (страницы → URL или локальный путь; user → `@mention_unresolved:key`),
span/inline-comment-marker (inline text). Неизвестные теги → ` ```xml ` блок.

## Тесты

```bash
.venv/bin/pytest tests/ -v   # 88 unit tests, без сети
```

Тесты: `test_text.py`, `test_md_to_storage.py`, `test_storage_to_md.py`,
`test_http_retry.py`, `test_client.py`, `test_manifest.py`, `test_frontmatter.py`,
`test_pull_links.py`, `test_push_links.py`.

Нет тестов для operation-модулей (тонкие обёртки, паттерн из bjira).
Live smoke: `tests/smoke.py` (ручной запуск против реального Confluence).

## Зависимости

- `httpx` — HTTP клиент
- `keyring` — OS keychain
- `markdown-it-py` — md парсер
- `lxml` — XML/XHTML парсер
- `python-slugify` — транслитерация для имён файлов
- Dev: `pytest`, `respx`

## Известные ограничения и TODO

- `@mention_unresolved:<userkey>` — userkey есть, displayName не резолвится (TODO: `hwiki resolve-mentions` или батч-резолв при pull через `GET /rest/api/user?key=...`)
- Таблицы с rowspan/colspan рендерятся как HTML (не рендерится в Obsidian без включения "Render HTML in notes")
- `push` не поддерживает create/delete страниц — только update существующих
- Нет команды `delete`
- Только Confluence Server/DC, REST API v1
