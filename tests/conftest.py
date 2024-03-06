import pytest
import FlashX_RecipeTools as flashx

from loguru import logger
from _pytest.logging import LogCaptureFixture


@pytest.fixture(autouse=True)
def caplog(caplog: LogCaptureFixture):
    handler_id = logger.add(
        caplog.handler,
        format="{message}",
        level=0,
        filter=lambda record: record["level"].no >= caplog.handler.level,
        enqueue=False,  # Set to 'True' if your test is spawning child processes.
    )
    yield caplog
    logger.remove(handler_id)


@pytest.fixture(autouse=True)
def reportlog(pytestconfig):
    logging_plugin = pytestconfig.pluginmanager.getplugin("logging-plugin")
    handler_id = logger.add(logging_plugin.report_handler, format="{message}")
    yield
    logger.remove(handler_id)


def pytest_configure(config):
    logger.remove()
    logger.enable(flashx.__name__)


def pytest_unconfigure(config):
    logger.disable(flashx.__name__)

