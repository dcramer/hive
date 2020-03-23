import logging

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

import appdaemon.utils as utils
import hassapi as hass


class Sentry(hass.Hass):
    def initialize(self):
        # https://docs.sentry.io/platforms/python/logging/
        sentry_logging = LoggingIntegration(
            level=logging.INFO,  # Capture info and above as breadcrumbs
            event_level=logging.ERROR,  # Send errors as events
        )

        sentry_sdk.init(
            dsn=self.args.get("dsn"),
            environment=self.args.get("environment"),
            integrations=[sentry_logging],
            release=self.args.get("release") or f"appdaemon-{utils.__version__}",
        )
