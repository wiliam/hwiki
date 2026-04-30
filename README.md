# hwiki

CLI для работы с Confluence Server/Data Center. Читает страницы, пишет, и делает двусторонний sync wiki-дерева в локальные markdown-файлы.

Использует Personal Access Token (PAT) и REST API v1.

## Установка

```
pipx install 'git+ssh://git@github.com/wiliam/hwiki.git@master'
```

## Конфиг

Создать `~/.hwiki_config`:

```json
{
  "host": "https://your-confluence.example.com",
  "user": "your.username",
  "default_space": "ENG",
  "timeout": 20
}
```

## Авторизация

Сгенерировать PAT в Confluence: профиль → **Personal Access Tokens** → **Create token**.

Сохранить в keychain:

```
hwiki login
```

## Команды

### `hwiki get <id-or-url>`

Получить страницу по ID или URL, вывести как Markdown.

```
hwiki get 12345
hwiki get 'https://wiki.example.com/pages/viewpage.action?pageId=12345'
hwiki get 'https://wiki.example.com/display/ENG/My+Page'
hwiki get 12345 --raw          # сырой Confluence storage XHTML
hwiki get 12345 --json         # полный объект страницы как JSON
hwiki get 12345 -o page.md     # записать в файл
```

### `hwiki search "<cql>"`

Поиск страниц через CQL.

```
hwiki search 'space = ENG AND title ~ "deploy"'
hwiki search 'space = ENG AND text ~ "redis"' -n 10
hwiki search 'space = ENG' --json
```

### `hwiki create --space KEY --title T`

Создать новую страницу. Тело из md-файла или stdin, конвертируется в storage XHTML.

```
hwiki create --space ENG --title "My Page" --file page.md
hwiki create --space ENG --title "Draft" --stdin < draft.md
hwiki create --space ENG --title "Child" --file page.md --parent 12345
```

### `hwiki update <id-or-url>`

Обновить существующую страницу.

```
hwiki update 12345 --file updated.md
hwiki update 12345 --title "New Title" --file updated.md
hwiki update 12345 --version 7 --title "New Title" --file updated.md
```

### `hwiki attach <id-or-url> <file>`

Загрузить файл как вложение к странице.

```
hwiki attach 12345 diagram.png
hwiki attach 12345 report.pdf -m "Q4 report"
```

---

## Sync: pull / push

### `hwiki pull <id-or-url> [-n depth] [-d dir]`

Скачать страницу и дочерние (глубина -n) в локальную папку.

```
hwiki pull 12345 -d ./wiki/            # только корень (default depth=0)
hwiki pull 12345 -n 2 -d ./wiki/       # корень + 2 уровня дочерних
hwiki pull 12345 -n 1 -d ./wiki/ --attachments   # + скачать изображения
```

Создаёт файлы вида `{page_id}-{slug}.md` с front-matter:

```markdown
---
id: "12345"
title: Название страницы
space: ENG
version: 42
parent_id: null
---
# Содержимое...
```

Внутренние ссылки на страницы из pull-сета становятся локальными (`./67890-other-page.md`).
Манифест `.hwiki.json` хранит метаданные для push.

### `hwiki push [file|id|url] [-d dir]`

Загрузить изменённые файлы обратно на wiki.

```
hwiki push -d ./wiki/                   # все изменённые файлы
hwiki push -d ./wiki/ --dry-run         # показать что изменится
hwiki push ./wiki/12345-my-page.md      # один файл
hwiki push 12345 -d ./wiki/             # по ID
hwiki push -d ./wiki/ --force           # перезаписать даже при конфликте версий
```

Изменение определяется по хешу содержимого. Если версия на wiki опередила локальную — конфликт (пропускается без `--force`).

---

## Поддерживаемый Markdown

**При записи на wiki (md → storage):**
h1–h6, параграфы, bold/italic/code, ссылки, изображения, списки (2 уровня),
code blocks с языком, blockquote, hr, таблицы, callout-блоки (`> [!INFO]`, `[!WARNING]`, `[!NOTE]`, `[!TIP]`)

**При чтении с wiki (storage → md):**
Всё из записи + expand-макросы (`<details>`), section/column layout (flatten),
panel, aura-tab (→ секции), task-list (→ `- [ ]`/`- [x]`), user mentions (`@mention_unresolved:<key>`).
Неизвестные теги сохраняются как ` ```xml ` блок.

---

## Флаги

- `-v` / `--verbose` — логировать HTTP-запросы в stderr

Коды выхода: `0` — успех, `2` — ошибка аргументов/конфига, `3` — ошибка API.

## Ограничения

- Только Confluence Server / Data Center (REST API v1). Cloud не поддерживается.
- Нет команды `delete`.
- `push` только обновляет существующие страницы (no create/delete).
- Таблицы с rowspan/colspan рендерятся как HTML (в Obsidian нужно включить Settings → Editor → "Render HTML in notes").
- User mentions сохраняются как `@mention_unresolved:<userkey>` — resolve планируется.
