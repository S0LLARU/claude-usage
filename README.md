# claude-usage

Сколько токенов Claude Code тратит каждый твой комп и каждый проект — при общем аккаунте Claude на нескольких Mac.

## Как работает

- Раз в час (launchd) скрипт читает локальные логи Claude Code `~/.claude/projects/**/*.jsonl` и считает токены за 5 часов / сутки / неделю — по компу, модели и проекту.
- Сводка этого компа загружается в **секретный gist** под тем GitHub-аккаунтом, что залогинен в `gh` на этом компе. Аккаунты на компах могут быть разными.
- Сводки других компов скачиваются из их gist'ов, и собирается панель `~/.claude/usage-tracker/data/dashboard.html`.

Лимит подписки Claude общий на аккаунт, Anthropic не делит его по устройствам. Поэтому процент лимита на комп ≈ общий процент из Settings → Usage × доля компа на панели.

Учитывается только Claude Code (включая вкладку Code в десктоп-приложении). Обычные чаты claude.ai хранятся на сервере и сюда не попадают.

## Установка

Нужны `python3`, `gh` (`brew install gh`) и `gh auth login`.

```bash
gh repo clone S0LLARU/claude-usage /tmp/claude-usage
bash /tmp/claude-usage/install.sh                 # первый комп
bash /tmp/claude-usage/install.sh <логин>/<id>    # следующие: ссылка gist'а уже установленного компа
```

В конце `install.sh` печатает `This machine's link: <логин>/<id>`. Чтобы компы видели друг друга, добавь ссылку нового компа на старом:

```bash
bash ~/.claude/usage-tracker/install.sh <ссылка нового компа>
```

## Использование

```bash
open ~/.claude/usage-tracker/data/dashboard.html   # панель
sh ~/.claude/usage-tracker/sync.sh                 # обновить прямо сейчас
cat ~/.claude/usage-tracker/data/report.txt        # текстовый отчёт
```

Удалить:

```bash
launchctl bootout gui/$(id -u)/com.user.claude-usage
rm -rf ~/.claude/usage-tracker ~/Library/LaunchAgents/com.user.claude-usage.plist
```

Секретный gist не виден в профиле, но открыть его может любой, у кого есть ссылка. Внутри — только количество токенов и названия папок проектов.
