from datetime import datetime

from base import AlertApp


def parse_tod(tod):
    if not tod:
        return None

    return {
        "after": list(map(int, tod["after"].split(":"))),
        "before": list(map(int, tod["after"].split(":"))),
    }


def parse_state(state):
    if isinstance(state, list):
        return frozenset([str(s) for s in state])
    return frozenset([str(state)])


class GenericAlert(AlertApp):
    def initialize(self):
        self.telegram_list = self.args.get("telegram") or []
        self.states = parse_state(self.args.get("state"))
        self.message = self.args.get("message")
        self.done_message = self.args.get("done_message")
        self.camera = self.args.get("camera")
        self.camera_output = self.args.get("camera_output")
        self.tod = parse_tod(self.args.get("tod"))
        super().initialize()

    def should_trigger(self, old, new):
        if self.tod:
            # TODO: this doesnt handle things like 0000-0700
            now = datetime.now()
            before = datetime.now().replace(
                hour=self.tod["before"][0], minute=self.tod["before"][1]
            )
            after = datetime.now().replace(
                hour=self.tod["after"][0], minute=self.tod["after"][1]
            )
            if not (now > after or now < before):
                self.log("not correct time of day")
                return False
        return new in self.states

    def on_activate(self, *args, **kwargs):
        if self.message:
            self.send_notifications(self.message)
        else:
            self.log("Not notifying")

    def on_deactivate(self, *args, **kwargs):
        if self.done_message:
            self.send_notifications(self.done_message)
        else:
            self.log("Not notifying")

    def send_notifications(self, message):
        if self.camera:
            self.call_service(
                "camera/snapshot",
                entity_id=self.camera,
                filename=self.camera_output.format(alert_id=self.alert_id),
            )

        for target in self.telegram_list:
            self.log(f"Notifying telegram {target}")
            if self.camera:
                self.call_service(
                    "telegram_bot/send_photo",
                    target=target,
                    file=self.camera_output.format(alert_id=self.alert_id),
                )
            self.call_service(
                "telegram_bot/send_message", target=target, message=message
            )
