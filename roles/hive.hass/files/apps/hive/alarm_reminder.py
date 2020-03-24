import appdaemon.plugins.hass.hassapi as hass


class AlarmReminder(hass.Hass):
    def initialize(self):
        # if set, disable the next on_activate call
        self.telegram_list = self.args.get("telegram") or []
        self.alarm = self.args.get("alarm")
        # the time to begin the reminder
        self.reminder_time = self.args.get("reminder_time")
        # delay, in minutes, from reminder time to set alarm
        self.activation_delay = int(self.args.get("activation_delay") or 30)
        # the time to disarm the alarm
        self.deactivate_time = self.args.get("deactivate_time")

        self.run_daily(self.on_reminder, self.reminder_time)
        self.run_daily(self.on_deactivate, self.deactivate_time)
        self.listen_event(self.receive_telegram_command, "telegram_command")

        self._activation_handle = None

    def on_reminder(self, kwargs):
        alarm_state = self.get_state(self.alarm)
        if alarm_state == "disarmed":
            self.log(f"not arming; state is {alarm_state}")
            return

        message = f"Alarm will be automatically armed in {self.activation_delay} minutes /stopArm"
        for target in self.telegram_list:
            self.call_service(
                "telegram_bot/send_message", target=target, message=message
            )

        self._activation_handle = self.run_in(
            self.on_activate, self.activation_delay * 60
        )

    def on_activate(self, kwargs):
        self.call_service("alarm_control_panel/alarm_arm_home", entity_id=self.alarm)

        message = "Alarm has been activated (Home)"
        for target in self.telegram_list:
            self.call_service(
                "telegram_bot/send_message", target=target, message=message
            )

    def on_deactivate(self, kwargs):
        # TODO: what should we do if they had stopped the auto arm?
        alarm_state = self.get_state(self.alarm)
        if alarm_state == "armed_home":
            self.log(f"not disarming; state is {alarm_state}")
            return

        self.call_service("alarm_control_panel/alarm_disarm", entity_id=self.alarm)

        message = "Alarm has been deactivated (Disarmed)"
        for target in self.telegram_list:
            self.call_service(
                "telegram_bot/send_message", target=target, message=message
            )

    def receive_telegram_command(self, event_id, payload_event, *args):
        assert event_id == "telegram_command"
        if payload_event["command"] == "/stopArm":
            self.call_service(
                "telegram_bot/send_message",
                target=payload_event["chat_id"],
                message="Automatic arming has been cancelled",
            )
            if self._activation_handle:
                self.cancel_timer(self._activation_handle)
