# import adbase as ad
import appdaemon.plugins.hass.hassapi as hass


class TelegramBot(hass.Hass):
    def initialize(self):
        self.command_list = self.args.get("commands")

    def receive_telegram_command(self, event_id, payload_event, *args):
        assert event_id == "telegram_command"
        if payload_event["command"] == "/help":
            self.call_service(
                "telegram_bot/send_message",
                target=payload_event["chat_id"],
                message="\n".join(self.command_list),
            )
