import appdaemon.plugins.hass.hassapi as hass

from time import time
from uuid import uuid1


class AlertApp(hass.Hass):
    def initialize(self):
        self._timer_handles = []
        self._listen_state_handles = []
        self._waiting_handle = None

        # is the alert active?
        self.active = None

        # a unique id for the currently active alert
        self.alert_id = None

        # should we skip the first alert? used with repeat
        self.skip_first = self.args.get("skip_first") or False

        # can we acknowledge this via service calls?
        self.can_acknowledge = self.args.get("can_acknowledge", True) or False

        # when this alert first became active
        self.first_active_at = None

        # the last time the alert was active (repeat)
        self.last_active_at = None

        # repeat config, in minutes - e.g. [1, 5]
        self.repeat = self.args.get("repeat") or []

        # the current repeat generation
        self.repeat_idx = 0

        # the entity we are monitoring for state changes
        self.entity_id = self.args.get("entity_id")

        # delay to activate
        self.delay = self.args.get("delay")

        # used to store the state of whether this alert is active
        self.input_boolean = self.args.get("input_boolean")
        # self.notify_list = self.args.get("notify") or []
        # TODO: add sonos list?
        # TODO: add script list?

        self._listen_state_handles.append(
            self.listen_state(self._state_change, self.entity_id)
        )

    def should_trigger(self, old, new):
        """
        Given the old state, and the new state, should this alert become active?
        """
        raise NotImplementedError

    def on_activate(self, old, new):
        """
        Handle activation condition.
        """

    def on_deactivate(self, old, new):
        """
        Handle deactivation condition.
        """

    def _get_attributes(self):
        return {
            "first_active_at": self.first_active_at,
            "last_active_at": self.last_active_at,
            "repeat_idx": self.repeat_idx,
            "alert_id": self.alert_id,
        }

    def _state_change(self, entity, attribute, old, new, kwargs):
        now = time()

        if self.active is None:
            # restore previous state
            if self.input_boolean:
                state = self.get_state(self.input_boolean)
                self.log("loading initial state: {}".format(state))
                self.active = state == "on"
                self.first_active_at = (
                    self.get_state(self.entity_id, attribute="first_active_at") or now
                )
                self.last_active_at = (
                    self.get_state(self.entity_id, attribute="last_active_at") or now
                )
                self.repeat_idx = (
                    self.get_state(self.entity_id, attribute="repeat_idx") or 0
                )
                self.alert_id = self.get_state(self.entity_id, attribute="alert_id")
            else:
                self.active = False

        if self.should_trigger(old=old, new=new):
            if not self.active:
                self.active = True
                self.alert_id = uuid1().hex
                self.first_active_at = self.last_active_at = now
                self.repeat_idx = 0
                self.log("{} is: {} - now active".format(entity, new))
                if self.input_boolean is not None:
                    self.set_state(
                        self.input_boolean,
                        state="on",
                        attributes=self._get_attributes(),
                    )
                if not self.skip_first:
                    self.on_activate(old, new)

            elif self.repeat:
                if (self.last_active_at + (self.repeat[self.repeat_idx] * 60)) <= now:
                    self.repeat_idx = max(self.repeat_idx + 1, len(self.repeat) - 1)
                    self.last_active_at = now
                    self.set_state(
                        self.input_boolean,
                        state="on",
                        attributes=self._get_attributes(),
                    )
                    self.on_activate(old, new)
        elif (
            self.active
            and self._waiting_handle is None
            and not self.should_trigger(old=old, new=new)
        ):
            self.log("Waiting: {} seconds to notify.".format(self.delay))
            self._waiting_handle = self.run_in(self._on_deactivate, self.delay)
            self._timer_handles.append(self._waiting_handle)

        # Power usage goes up before delay
        elif (
            new is not None
            and new != ""
            and self.active
            and self._waiting_handle is not None
            and float(new) > self.threshold
        ):
            self.log("Cancelling timer")
            self.cancel_timer(self._waiting_handle)
            self._waiting_handle = None
            self.alert_id = None

    def _on_deactivate(self, kwargs):
        self.active = False
        self.log("Setting active to: {}".format(self.active))
        if self.input_boolean is not None:
            self.set_state(self.input_boolean, state="off", attributes={})
        self.on_deactivate()
        self.alert_id = None

    def terminate(self):
        for handle in self._timer_handles:
            self.cancel_timer(handle)

        for handle in self._listen_state_handles:
            self.cancel_listen_state(handle)
