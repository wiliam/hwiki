# hwiki

A command-line interface for Confluence Server / Data Center. Uses Personal Access Token (PAT) authentication and the REST API v1.

## Install

```
pipx install 'git+ssh://git@github.com/wiliam/hwiki.git@master'
```

## Config

Create `~/.hwiki_config`:

```json
{
  "host": "https://your-confluence.example.com",
  "user": "your.username",
  "default_space": "ENG",
  "timeout": 20
}
```

## Auth

Generate a PAT in Confluence Server: go to your profile menu, choose **Personal Access Tokens**, then click **Create token**. Give it a name and copy the value.

Then store it in your system keychain:

```
hwiki login
```

You will be prompted to paste the token. hwiki will verify it against your Confluence instance and store it securely.

## Commands

### `hwiki login`

Prompt for a PAT and store it in the system keychain. Verifies the token by calling the Confluence API.

```
hwiki login
```

### `hwiki get <id-or-url>`

Fetch a Confluence page by its numeric ID or webui URL, and print it as Markdown.

```
hwiki get 12345
hwiki get https://wiki.example.com/pages/12345
hwiki get 12345 --raw           # output raw storage XHTML
hwiki get 12345 --json          # output full page JSON
hwiki get 12345 -o page.md      # write Markdown to file
```

Options:
- `--raw` — print raw Confluence storage XHTML instead of Markdown
- `--json` — print the full page object as JSON
- `-o FILE` / `--out FILE` — write output to a file instead of stdout

### `hwiki search "<cql>"`

Search Confluence pages using a CQL query. Results are printed in a columnar format with page ID, space key, title, and URL.

```
hwiki search 'space = ENG AND title ~ "deploy"'
hwiki search 'space = ENG AND text ~ "redis"' -n 10
hwiki search 'space = ENG' --json
```

Options:
- `-n N` / `--limit N` — maximum number of results (default: 25)
- `--json` — print results as a JSON array

### `hwiki create --space KEY --title T --file f.md`

Create a new Confluence page. The body is read from a Markdown file or stdin and converted to Confluence storage XHTML.

```
hwiki create --space ENG --title "My New Page" --file page.md
hwiki create --space ENG --title "Draft" --stdin < draft.md
hwiki create --space ENG --title "Child Page" --file page.md --parent 12345
```

Options:
- `--space KEY` — target space key (required)
- `--title T` — page title (required)
- `--file FILE` — read body from a Markdown file
- `--stdin` — read body from stdin
- `--parent ID-or-URL` — attach as child of this page

If neither `--file` nor `--stdin` is given, the page is created with an empty body.

On success, prints: `created page id=<id> title=<title> url=<url>`

### `hwiki update <id-or-url> --file f.md`

Update an existing Confluence page. Fetches the current version automatically unless `--version N` is specified.

```
hwiki update 12345 --file updated.md
hwiki update 12345 --stdin < updated.md
hwiki update 12345 --title "New Title" --file updated.md
hwiki update 12345 --title "New Title" --version 7 --file updated.md
```

Options:
- `--title T` — new page title (optional; keeps existing title if omitted, unless `--version N` is given in which case it is required)
- `--file FILE` — read new body from a Markdown file
- `--stdin` — read new body from stdin
- `--version auto|N` — current version number; `auto` fetches it automatically (default: `auto`); specify a number to skip the extra GET request

Either `--file` or `--stdin` is required.

On success, prints: `updated page id=<id> version=<new_version> title=<title>`

### `hwiki attach <id-or-url> <file>`

Upload a file as an attachment to a Confluence page.

```
hwiki attach 12345 diagram.png
hwiki attach 12345 report.pdf -m "Q4 report"
```

Options:
- `-m COMMENT` / `--message COMMENT` — attachment comment

On success, prints: `attached <filename> id=<attachment_id> to page <page_id>`

## Markdown support

The following Markdown elements are converted to Confluence storage XHTML:

- Headings (H1–H6)
- Paragraphs and line breaks
- Bold, italic, inline code
- Fenced code blocks (with language hint)
- Unordered and ordered lists
- Blockquotes
- Horizontal rules
- Links and images

Explicitly unsupported (deferred):

- Tables
- Confluence macros (e.g., info/warning panels, table of contents)
- Embedded Confluence-specific XHTML pass-through
- Footnotes and task lists

## Flags

- `-v` / `--verbose` — print all HTTP requests and responses to stderr (useful for debugging)

Exit codes:
- `0` — success
- `2` — argument or configuration error (bad args, missing config, missing token)
- `3` — API error (HTTP error from Confluence)

## Limitations

- Confluence Server and Data Center only (REST API v1). Confluence Cloud uses a different API and is not supported.
- No `delete` command. Use the Confluence web UI or direct API calls to delete pages.
- The PAT is stored in the system keychain via the `keyring` library. On headless systems you may need to configure a keyring backend.
