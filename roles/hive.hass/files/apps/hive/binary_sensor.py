from .base import AlertApp


class BinarySensorAlert(AlertApp):
    def initialize(self):
        super().initialize()
        self.telegram_list = self.args.get("telegram_list") or []
        self.state = self.args.get("state")
        self.message = self.args.get("message")
        self.done_message = self.args.get("done_message")
        self.camera = self.args.get("camera")

    def should_trigger(self, old, new):
        return new == self.state

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
                    "telegram_bot/send_photo", target=target, file=self.camera_output
                )
            self.call_service(
                "telegram_bot/send_message", target=target, message=message
            )
