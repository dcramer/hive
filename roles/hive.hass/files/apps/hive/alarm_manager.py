import appdaemon.plugins.hass.hassapi as hass


class AlarmState(object):
    none = 0
    waiting_disarm = 1
    waiting_arm = 2


class AlarmManager(hass.Hass):
    def initialize(self):
        # list of chats to notify
        self.telegram_list = self.args.get("telegram") or []
        # entity id
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
        self.listen_state(self.receive_state_change, self.alarm)

        self._alarm_state = AlarmState.none

        self._activation_handle = None
        self._timeout_handle = None

    def _timeout_state_change(self):
        if self._alarm_state == AlarmState.none:
            return

        if self._alarm_state == AlarmState.waiting_disarm:
            self.log("timed out on waiting_disarm")
            self._send_message("WARNING: Timed out waiting for alarm to disarm")

        elif self._alarm_state == AlarmState.waiting_arm:
            self.log("timed out on waiting_arm")
            self._send_message("WARNING: Timed out waiting for alarm to arm")

        else:
            raise NotImplementedError

        self._alarm_state = AlarmState.none
        self._timeout_handle = None
        self._cancel_timers()

    def _cancel_timers(self):
        if self._timeout_handle:
            self.cancel_timer(self._timeout_handle)
            self._timeout_handle = None

        if self._activation_handle:
            self.cancel_timer(self._activation_handle)
            self._activation_handle = None

    def _send_message(self, message):
        for target in self.telegram_list:
            self.call_service(
                "telegram_bot/send_message", target=target, message=message
            )

    def on_reminder(self, kwargs):
        alarm_state = self.get_state(self.alarm)
        if alarm_state != "disarmed":
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
        self._timeout_handle = self.run_in(self._timeout_state_change, 60)
        self._alarm_state = AlarmState.waiting_arm
        self.call_service("alarm_control_panel/alarm_arm_home", entity_id=self.alarm)

    def on_deactivate(self, kwargs):
        # TODO: what should we do if they had stopped the auto arm?
        alarm_state = self.get_state(self.alarm)
        if alarm_state != "armed_home":
            self.log(f"not disarming; state is {alarm_state}")
            return

        self._alarm_state = AlarmState.waiting_disarm
        self._timeout_handle = self.run_in(self._timeout_state_change, 60)
        self.call_service("alarm_control_panel/alarm_disarm", entity_id=self.alarm)

    def receive_state_change(self, entity, attribute, old, new, kwargs):
        assert entity == self.alarm

        if self._alarm_state == AlarmState.waiting_arm:
            if new == "armed_home":
                self._send_message("Alarm has been activated (Home)")
                self._alarm_state = AlarmState.none
            else:
                self.log(
                    f"received unexpected alarm state change to {new} while waiting_arm"
                )

        if self._alarm_state == AlarmState.waiting_disarm:
            if new == "disarmed":
                self._send_message("Alarm has been deactivated (Disarmed)")
                self._alarm_state = AlarmState.none
            else:
                self.log(
                    f"received unexpected alarm state change to {new} while waiting_disarm"
                )

    def receive_telegram_command(self, event_id, payload_event, *args):
        assert event_id == "telegram_command"
        if payload_event["command"] == "/stopArm" and self._activation_handle:
            self.log(f"automatic arming cancelled")
            self.cancel_timer(self._activation_handle)
            self.call_service(
                "telegram_bot/send_message",
                target=payload_event["chat_id"],
                message="Automatic arming has been cancelled",
            )
            self._activation_handle = None

    def terminate(self):
        self._cancel_timers()
