from datetime import datetime, time
from typing import List

from base import AlertApp


def parse_tod(tod: List[str]):
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


def between(dt: datetime, start: time, stop: time) -> bool:
    if stop > start:  # range does not cross midnight
        return stop >= dt.time() >= start
    else:
        return not (dt.time() <= start and dt.time() >= stop)


if __name__ == "__main__":
    now = datetime(2020, 4, 1, 21, 10)
    assert between(now, time(0), time(1)) is False
    assert between(now, time(0), time(22)) is True
    assert between(now, time(19), time(7)) is True
    assert between(now, time(23), time(7)) is False

    now = datetime(2020, 4, 1, 1, 10)
    assert between(now, time(0), time(1)) is False
    assert between(now, time(0), time(22)) is True
    assert between(now, time(19), time(7)) is True
    assert between(now, time(22), time(7)) is True
    assert between(now, time(4), time(23)) is False

    now = datetime(2020, 4, 1, 17, 10)
    assert between(now, time(23, 59), time(7, 0)) is False


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
            now = datetime.now()
            before = time(self.tod["before"][0], self.tod["before"][1])
            after = time(self.tod["after"][0], self.tod["after"][1])
            if not between(now, before, after):
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
