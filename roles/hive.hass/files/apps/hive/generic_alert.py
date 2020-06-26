from base import AlertApp, parse_list, parse_tod, between


class GenericAlert(AlertApp):
    def initialize(self):
        self.telegram_list = self.args.get("telegram") or []
        self.states = parse_list(self.args.get("state"))
        self.message = self.args.get("message")
        self.done_message = self.args.get("done_message")
        self.camera = self.args.get("camera")
        self.camera_output = self.args.get("camera_output")
        self.tod = parse_tod(self.args.get("tod"), tzinfo=self.AD.tz)
        super().initialize()

    def should_trigger(self, old, new):
        if self.tod:
            now = self.datetime(aware=True)
            # TODO(dcramer): pretty sure i should just be using the builtin and didnt need to write this code
            # if not self.now_is_between("sunset - 00:45:00", "sunrise + 00:45:00"):
            if not between(now, self.tod["after"], self.tod["before"]):
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
