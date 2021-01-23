from base import AlertApp


class PowerUsageAlert(AlertApp):
    EMPTY_NEW_VALUES = frozenset([None, "", "unavailable"])

    def initialize(self):
        self.telegram_list = self.args.get("telegram") or []
        self.notify_list = self.args.get("notify") or []
        self.sonos_entity_id = self.args.get("sonos_entity_id")
        self.sonos_volume = float(self.args.get("sonos_volume") or 0.5)
        self.threshold = int(self.args.get("threshold") or 2)
        try:
            self.message = self.args.get("message")
        except KeyError:
            self.message = None
        try:
            self.done_message = self.args.get("done_message")
        except KeyError:
            self.done_message = None
        super().initialize()

    def should_trigger(self, old, new):
        return new not in self.EMPTY_NEW_VALUES and float(new) > self.threshold

    def on_activate(self, *args, **kwargs):
        if self.message:
            self.send_notifications(self.message)
        else:
            self.log("Not notifying user")

    def on_deactivate(self, *args, **kwargs):
        if self.done_message:
            self.send_notifications(self.done_message)
        else:
            self.log("Not notifying user")

    def send_notifications(self, message):
        for notify_name in self.notify_list:
            self.log(f"Notifying notify.{notify_name}")
            self.notify(message, name=notify_name)

        self.log(f"Notifying via broadcast to {self.sonos_entity_id}")
        self.call_service(
            "script/sonos_broadcast_say",
            entity_id=self.sonos_entity_id,
            volume=self.sonos_volume,
            message=message,
            delay="00:00:05",
        )
        for target in self.telegram_list:
            self.call_service(
                "telegram_bot/send_message", target=target, message=message,
            )
