"""Typer CLI — каркас фазы 1. Команды для проверки, что ядро+плагины
реально работают (`version`, `plugins list`, `registry show`, `debug`).
Команда генерации промпта появится в фазе 3 вместе с pipeline.
"""

from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

from egodary._version import APP_VERSION, BUILD_NUMBER
from egodary.bootstrap import build_app
from egodary.core.debug import get_debug_snapshot

app = typer.Typer(name="egodary", help="eGOdary — плагинный движок генерации промптов.")
plugins_app = typer.Typer(help="Работа со списком загруженных плагинов.")
registry_app = typer.Typer(help="Просмотр реестра тегов.")
app.add_typer(plugins_app, name="plugins")
app.add_typer(registry_app, name="registry")

console = Console()


@app.command()
def version() -> None:
    """Показать версию приложения и номер сборки."""
    console.print(f"eGOdary [bold]{APP_VERSION}[/bold] (build {BUILD_NUMBER})")


@plugins_app.command("list")
def plugins_list() -> None:
    """Показать все загруженные плагины: id, версия, вид, источник."""
    _, plugin_manager = build_app()
    summary = plugin_manager.summary()

    table = Table(title=f"Загружено плагинов: {summary['loaded_count']}")
    table.add_column("id")
    table.add_column("версия")
    table.add_column("вид")
    table.add_column("источник")
    table.add_column("категории")
    for p in summary["loaded"]:
        table.add_row(p["id"], p["version"], p["kind"], p["source"], ", ".join(p["category_ids"]) or "—")
    console.print(table)

    if summary["skipped_unsupported_kind"]:
        console.print("\n[yellow]Манифесты с пока не реализованным видом плагина:[/yellow]")
        for s in summary["skipped_unsupported_kind"]:
            console.print(f"  - {s['id']} ({s['kind']}): {s['reason']}")


@registry_app.command("show")
def registry_show(category_id: str) -> None:
    """Показать содержимое одной категории реестра по её id."""
    registry, _ = build_app()
    category = registry.get_category(category_id)
    if category is None:
        console.print(f"[red]Категория '{category_id}' не найдена.[/red]")
        console.print(f"Доступные категории: {', '.join(registry.category_ids())}")
        raise typer.Exit(code=1)

    table = Table(title=f"{category.title} ({category.id})")
    table.add_column("id")
    table.add_column("label")
    table.add_column("tags")
    for item in category.items:
        table.add_row(item.id, item.label, json.dumps(item.tags, ensure_ascii=False))
    console.print(table)


@registry_app.command("list")
def registry_list() -> None:
    """Показать список всех загруженных категорий реестра."""
    registry, _ = build_app()
    table = Table(title="Категории реестра")
    table.add_column("id")
    table.add_column("название")
    table.add_column("тегов")
    table.add_column("источник")
    for category in registry.all_categories():
        table.add_row(
            category.id,
            category.title,
            str(len(category.items)),
            registry.source_of(category.id) or "—",
        )
    console.print(table)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Адрес сервера."),
    port: int = typer.Option(8000, help="Порт."),
    reload: bool = typer.Option(True, help="Автоперезагрузка при изменении кода."),
) -> None:
    """Запустить веб-UI и API (http://127.0.0.1:8000/)."""
    import uvicorn

    from pathlib import Path

    pkg_dir = Path(__file__).resolve().parents[1]
    if reload:
        reload_dirs = [
            str(pkg_dir / "content"),
            str(pkg_dir / "web" / "static"),
            str(pkg_dir / "core"),
            str(pkg_dir / "api"),
            str(pkg_dir / "models_adapters"),
        ]
    else:
        reload_dirs = None

    console.print(f"[green]eGOdary UI:[/green] http://{host}:{port}/")
    console.print("[dim]Остановка: Ctrl+C. Не запускайте второй сервер на том же порту.[/dim]")
    uvicorn.run(
        "egodary.api.main:app",
        host=host,
        port=port,
        reload=reload,
        reload_dirs=reload_dirs,
    )


@app.command()
def debug() -> None:
    """Отладочный снимок (аналог вкладки Debug из eGen 8.6): версия,
    плагины, сводка реестра. Используй при анализе ошибок.
    """
    registry, plugin_manager = build_app()
    snapshot = get_debug_snapshot(registry, plugin_manager)
    console.print_json(json.dumps(snapshot, ensure_ascii=False))


if __name__ == "__main__":
    app()
