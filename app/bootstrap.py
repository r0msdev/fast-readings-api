"""Composition roots — wire all bus handlers for each process entry point."""


def _register_commands() -> None:
    from app.core.bus import command_bus  # pylint: disable=import-outside-toplevel
    from app.commands.create_reading import CreateReadingCommand, CreateReadingHandler  # pylint: disable=import-outside-toplevel
    from app.commands.delete_reading import DeleteReadingCommand, DeleteReadingHandler  # pylint: disable=import-outside-toplevel

    command_bus.register(CreateReadingCommand, CreateReadingHandler().handle)
    command_bus.register(DeleteReadingCommand, DeleteReadingHandler().handle)


def _register_queries() -> None:
    from app.core.bus import query_bus  # pylint: disable=import-outside-toplevel
    from app.queries.readings import (  # pylint: disable=import-outside-toplevel
        GetReadingByIdQuery, GetReadingByIdHandler,
        ListReadingsQuery, ListReadingsHandler,
    )
    from app.queries.stats import (  # pylint: disable=import-outside-toplevel
        GetDailyStatsQuery, GetDailyStatsHandler,
        GetStatsListQuery, GetStatsListHandler,
    )

    query_bus.register(ListReadingsQuery, ListReadingsHandler().handle)
    query_bus.register(GetReadingByIdQuery, GetReadingByIdHandler().handle)
    query_bus.register(GetStatsListQuery, GetStatsListHandler().handle)
    query_bus.register(GetDailyStatsQuery, GetDailyStatsHandler().handle)


def _register_events() -> None:
    from app.core.bus import event_bus  # pylint: disable=import-outside-toplevel
    from app.domain.events import ReadingCreated, ReadingDeleted  # pylint: disable=import-outside-toplevel
    from app.messaging.handlers import on_reading_created, on_reading_deleted  # pylint: disable=import-outside-toplevel

    event_bus.register(ReadingCreated, on_reading_created)
    event_bus.register(ReadingDeleted, on_reading_deleted)


def bootstrap_api() -> None:
    """Register all command, query, and event handlers for the HTTP API process."""
    _register_commands()
    _register_queries()
    _register_events()


def bootstrap_worker() -> None:
    """Register all command handlers for the worker process."""
    from app.core.bus import command_bus  # pylint: disable=import-outside-toplevel
    from app.commands.recalculate_stats import (  # pylint: disable=import-outside-toplevel
        RecalculateStatsCommand, RecalculateStatsHandler,
    )

    command_bus.register(RecalculateStatsCommand, RecalculateStatsHandler().handle)
