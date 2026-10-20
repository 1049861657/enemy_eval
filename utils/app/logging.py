"""应用日志：structlog 经 stdlib ProcessorFormatter 输出，滚动文件 + 开发时 stderr。"""

from __future__ import annotations

import logging
import sys
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler
from types import TracebackType
from typing import cast

import structlog
from platformdirs import user_log_path
from structlog.typing import BindableLogger, EventDict

from .identity import APP_AUTHOR, APP_NAME

_LOG_FILENAME = "enemy-eval.log"
_LOG_MAX_BYTES = 1_000_000
_LOG_BACKUP_COUNT = 3

_configured = False
_std_logger = logging.getLogger(__name__)


def _add_local_timestamp(
    _logger: object, _method: str, event_dict: EventDict
) -> EventDict:
    """本机时区，不含偏移。"""
    event_dict["timestamp"] = datetime.now().astimezone().strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    return event_dict


def _console_renderer(*, colors: bool) -> structlog.dev.ConsoleRenderer:
    """中文事件按 len() 补空格会对不齐；文件日志也不需要列对齐。"""
    return structlog.dev.ConsoleRenderer(
        colors=colors,
        pad_level=False,
        pad_event_to=0,
    )


def setup_logging() -> None:
    """配置根 logger；不依赖 Qt。重复调用无效。"""
    global _configured
    if _configured:
        return

    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        _add_local_timestamp,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=cast(type[BindableLogger], structlog.stdlib.BoundLogger),
        cache_logger_on_first_use=True,
    )

    foreign_pre_chain: list[structlog.typing.Processor] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.ExtraAdder(),
        _add_local_timestamp,
    ]

    log_dir = user_log_path(APP_NAME, appauthor=APP_AUTHOR, ensure_exists=True)
    file_handler = RotatingFileHandler(
        log_dir / _LOG_FILENAME,
        maxBytes=_LOG_MAX_BYTES,
        backupCount=_LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=foreign_pre_chain,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                _console_renderer(colors=False),
            ],
        )
    )

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)

    if sys.stderr is not None:
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                foreign_pre_chain=foreign_pre_chain,
                processors=[
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    _console_renderer(colors=sys.stderr.isatty()),
                ],
            )
        )
        root.addHandler(stream_handler)

    sys.excepthook = _handle_sys_exception
    threading.excepthook = _handle_thread_exception
    _configured = True


def _handle_sys_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    _std_logger.error(
        "未捕获异常", exc_info=(exc_type, exc_value, exc_traceback)
    )


def _handle_thread_exception(args: threading.ExceptHookArgs) -> None:
    extra = {"thread_name": args.thread.name if args.thread else None}
    if args.exc_value is None:
        _std_logger.error("线程未捕获异常", extra=extra)
        return
    _std_logger.error(
        "线程未捕获异常",
        extra=extra,
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )
