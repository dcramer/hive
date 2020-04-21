import logging

import sentry_sdk
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

import appdaemon.utils as utils
import hassapi as hass


class Sentry(hass.Hass):
    def initialize(self):
        sentry_sdk.init(
            dsn=self.args.get("dsn"),
            environment=self.args.get("environment"),
            in_app_include=["hive"],
            integrations=[
                AioHttpIntegration(),
                LoggingIntegration(
                    level=logging.INFO,  # Capture info and above as breadcrumbs
                    event_level=logging.ERROR,  # Send errors as events
                ),
            ],
            release=self.args.get("release") or f"appdaemon-{utils.__version__}",
            traces_sample_rate=1.0,
            traceparent_v2=True,
        )
