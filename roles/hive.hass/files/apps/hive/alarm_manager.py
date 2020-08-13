import appdaemon.plugins.hass.hassapi as hass

VALID_COMMANDS = frozenset(["/alarm", "/stopArm", "/disarm", "/armAway", "/armHome"])


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

        self.alarm_code = self.args.get("alarm_code")

        self.house_mode_entity = "input_select.house_mode"

        self.run_daily(self.on_reminder, self.reminder_time)
        self.run_daily(self.on_deactivate, self.deactivate_time)
        self.listen_event(self.receive_telegram_command, "telegram_command")
        self.listen_state(self.receive_state_change, self.alarm)

        self._alarm_state = AlarmState.none

        self._activation_handle = None
        self._timeout_handle = None

    def _timeout_state_change(self, kwargs):
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
        self._cancel_timers()

    def _cancel_timers(self):
        if self._timeout_handle:
            self.cancel_timer(self._timeout_handle)
            self._timeout_handle = None

        if self._activation_handle:
            self.cancel_timer(self._activation_handle)
            self._activation_handle = None

    def _send_message(self, message, target_list=None):
        if target_list is None:
            target_list = self.telegram_list
        for target in target_list:
            self.call_service(
                "telegram_bot/send_message",
                target=target,
                message=f"*Alarm:* {message}",
            )

    def on_reminder(self, kwargs):
        alarm_state = self.get_state(self.alarm)
        if alarm_state != "disarmed":
            self.log(f"not arming; state is {alarm_state}")
            return

        self._send_message(
            message=f"Will automatically arm in {self.activation_delay} minutes /stopArm"
        )
        self._cancel_timers()
        self._activation_handle = self.run_in(
            self.on_activate, self.activation_delay * 60
        )

    def on_activate(self, kwargs):
        self._cancel_timers()
        self._timeout_handle = self.run_in(self._timeout_state_change, 60)
        self._alarm_state = AlarmState.waiting_arm
        # if we're in vacation mode, we arm in away mode
        if (
            self.house_mode_entity
            and self.get_state(self.house_mode_entity) == "vacation"
        ):
            self.call_service(
                "alarm_control_panel/alarm_arm_away",
                entity_id=self.alarm,
                code=self.alarm_code,
            )
        else:
            self.call_service(
                "alarm_control_panel/alarm_arm_home",
                entity_id=self.alarm,
                code=self.alarm_code,
            )

    def on_deactivate(self, kwargs):
        # TODO: what should we do if they had stopped the auto arm?
        alarm_state = self.get_state(self.alarm)
        if alarm_state != "armed_home":
            self.log(f"not disarming; state is {alarm_state}")
            return

        self._alarm_state = AlarmState.waiting_disarm
        self._cancel_timers()
        self._timeout_handle = self.run_in(self._timeout_state_change, 60)
        self.call_service(
            "alarm_control_panel/alarm_disarm",
            entity_id=self.alarm,
            code=self.alarm_code,
        )

    def receive_state_change(self, entity, attribute, old, new, kwargs):
        assert entity == self.alarm

        if self._alarm_state == AlarmState.waiting_arm:
            if new == "armed_home" or new == "armed_away":
                mode = new.split("_", 1)[-1]
                self._send_message(f"System armed in _{mode} mode_ /disarm")
                self._alarm_state = AlarmState.none
                if self._timeout_handle:
                    self.cancel_timer(self._timeout_handle)
                    self._timeout_handle = None
            elif new == "arming":
                pass
            else:
                self.log(
                    f"received unexpected alarm state change to {new} while waiting_arm"
                )

        elif self._alarm_state == AlarmState.waiting_disarm:
            if new == "disarmed":
                self._send_message("System disarmed")
                self._alarm_state = AlarmState.none
                if self._timeout_handle:
                    self.cancel_timer(self._timeout_handle)
                    self._timeout_handle = None
            else:
                self.log(
                    f"received unexpected alarm state change to {new} while waiting_disarm"
                )

    def _manual_arm(self, mode, telegram_target):
        if self.get_state(self.alarm) == f"armed_{mode}":
            self._send_message(
                message=f"Already armed in _{mode} mode_",
                target_list=[telegram_target],
            )
            return

        delay = self.get_state(self.alarm, attribute=f"exit_delay_{mode}") or 0
        self._cancel_timers()
        self._timeout_handle = self.run_in(self._timeout_state_change, delay + 60)
        self._alarm_state = AlarmState.waiting_arm
        self.call_service(
            f"alarm_control_panel/alarm_arm_{mode}",
            entity_id=self.alarm,
            code=self.alarm_code,
        )

        if delay > 5:
            self._send_message(
                message=f"Arming in _{mode} mode_ ({delay} countdown) /stopArm",
                target_list=[telegram_target],
            )

    def receive_telegram_command(self, event_id, payload_event, *args):
        assert event_id == "telegram_command"

        command = payload_event["command"]

        if command not in VALID_COMMANDS:
            return

        self.log(f"received {command} command")

        chat_id = payload_event["chat_id"]

        if command == "/alarm":
            mode = self.get_state(self.alarm).split("_", 1)[-1]
            self._send_message(f"Currently in _{mode} mode_")
            return

        # all valid commands will cancel automatic arming
        if self._activation_handle:
            self.cancel_timer(self._activation_handle)
            self._activation_handle = None
            if self.get_state(self.alarm) == "disarmed":
                self.log(f"automatic arming cancelled")
                self._send_message(
                    message="Automatic arming has been cancelled",
                    target_list=[chat_id],
                )

        if command == "/stopArm":
            if self.get_state(self.alarm) == "arming":
                if self._timeout_handle:
                    self.cancel_timer(self._timeout_handle)
                self._timeout_handle = self.run_in(self._timeout_state_change, 60)
                self._alarm_state = AlarmState.waiting_disarm
                self.call_service(
                    "alarm_control_panel/alarm_disarm",
                    entity_id=self.alarm,
                    code=self.alarm_code,
                )

        elif command == "/disarm":
            if self.get_state(self.alarm) != "disarmed":
                self._cancel_timers()
                self._timeout_handle = self.run_in(self._timeout_state_change, 60)
                self._alarm_state = AlarmState.waiting_disarm
                self.call_service(
                    "alarm_control_panel/alarm_disarm",
                    entity_id=self.alarm,
                    code=self.alarm_code,
                )
            else:
                self._send_message(
                    message="System is not armed", target_list=[chat_id],
                )

        elif command == "/armHome":
            self._manual_arm("home", telegram_target=[chat_id])

        elif command == "/armAway":
            self._manual_arm("away", telegram_target=[chat_id])

    def terminate(self):
        self._cancel_timers()
