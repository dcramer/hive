# import adbase as ad
import appdaemon.plugins.hass.hassapi as hass

VALID_COMMANDS = frozenset(["/house", "/houseNormal", "/houseVacation"])


class HouseModeBot(hass.Hass):
    def initialize(self):
        self.entity_id = self.args.get("entity_id")
        self.telegram_list = self.args.get("telegram") or []

        self._pending_state = None
        self._timeout_handle = None

        self.listen_state(self.receive_state_change, self.entity_id)
        self.listen_event(self.receive_telegram_command, "telegram_command")

    def _cancel_timers(self):
        if self._timeout_handle:
            self.cancel_timer(self._timeout_handle)
            self._timeout_handle = None

    def _timeout_state_change(self, kwargs):
        if self._pending_state is None:
            return

        self.log(f"timed out on setting {self.entity_id} to _{self._pending_state}")
        self._send_message(
            message=f"WARNING: Timed out waiting for {self.entity_id} to set to _{self._pending_state}"
        )

        self._pending_state = None
        self._cancel_timers()

    def _send_message(self, message, target_list=None):
        if target_list is None:
            target_list = self.telegram_list
        for target in target_list:
            self.call_service(
                "telegram_bot/send_message",
                target=target,
                message=f"*House Mode:* {message}",
            )

    def receive_state_change(self, entity, attribute, old, new, kwargs):
        assert entity == self.entity_id

        if self._pending_state and new == self._pending_state:
            self._pending_state = None
            self._send_message(f"Set to _{new}_")
            if self._timeout_handle:
                self.cancel_timer(self._timeout_handle)
                self._timeout_handle = None
        elif new == old:
            return

    def receive_telegram_command(self, event_id, payload_event, *args):
        assert event_id == "telegram_command"

        command = payload_event["command"]
        if command not in VALID_COMMANDS:
            return

        self.log(f"received {command} command")

        chat_id = payload_event["chat_id"]
        current = self.get_state(self.entity_id)

        if command == "/houseVacation":
            state = "vacation"
        elif command == "/houseNormal":
            state = "normal"
        elif command == "/house":
            self._send_message(
                message=f"Currently set to _{current}_", target_list=[chat_id]
            )
            return
        else:
            return

        if current == state:
            self._send_message(
                message=f"Already set to _{state}_", target_list=[chat_id]
            )
            return

        self._pending_state = state
        self._send_message(message=f"Setting mode to _{state}_", target_list=[chat_id])
        self.call_service(
            "input_select/select_option", entity_id=self.entity_id, option=state
        )
