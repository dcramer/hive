# import adbase as ad
import appdaemon.plugins.hass.hassapi as hass

import datetime
from time import time
from uuid import uuid1


class AlertApp(hass.Hass):
    EMPTY_NEW_VALUES = frozenset([None, ""])

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

        # the previous value seen
        self.last_value = None

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
        self._load_initial_state()

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

    # TODO: when we up to appd 4.x
    # @ad.app_lock
    def _load_initial_state(self):
        if self.input_boolean:
            now = now = time()
            state = self.get_state(self.input_boolean)
            self.log("loading initial state: {}".format(state))
            self.first_active_at = (
                self.get_state(self.input_boolean, attribute="first_active_at") or now
            )
            self.last_active_at = (
                self.get_state(self.input_boolean, attribute="last_active_at") or now
            )
            self.repeat_idx = (
                self.get_state(self.input_boolean, attribute="repeat_idx") or 0
            )
            self.alert_id = self.get_state(self.input_boolean, attribute="alert_id")
            self.last_value = (
                self.get_state(self.input_boolean, attribute="last_value") or None
            )
            self.active = state == "on"
            self._test_state(self.last_value, self.get_state(self.entity_id))
        else:
            self.active = False

        if self.active:
            self._waiting_handle = self.run_minutely(self._tick, datetime.time())

    def _get_attributes(self):
        return {
            "first_active_at": self.first_active_at,
            "last_active_at": self.last_active_at,
            "last_value": self.last_value,
            "repeat_idx": self.repeat_idx,
            "alert_id": self.alert_id,
        }

    def _tick(self, *args, **kwargs):
        if self.repeat:
            return
        now = time()
        if (self.last_active_at + (self.repeat[self.repeat_idx] * 60)) <= now:
            old = self.last_value
            new = self.get_state(self.entity_id)
            self.repeat_idx = max(self.repeat_idx + 1, len(self.repeat) - 1)
            self.last_active_at = now
            self.last_value = new
            self.set_state(
                self.input_boolean, state="on", attributes=self._get_attributes(),
            )
            self.on_activate(old, new)
            self._waiting_handle = self.run_minutely(self._tick, datetime.time())

    def _state_change(self, entity, attribute, old, new, kwargs):
        self._test_state(old, new)

    def _test_state(self, old, new):
        now = time()

        # if self.active is None:
        #     # restore previous state
        #     self._load_initial_state()

        if self.should_trigger(old=old, new=new):
            if not self.active:
                self.active = True
                self.alert_id = uuid1().hex
                self.first_active_at = self.last_active_at = now
                self.repeat_idx = 0
                self.log("{} is: {} - active".format(self.entity_id, new,))
                if self.input_boolean is not None:
                    self.set_state(
                        self.input_boolean,
                        state="on",
                        attributes=self._get_attributes(),
                    )
                if not self.skip_first:
                    self.on_activate(old, new)
                self._waiting_handle = self.run_minutely(self._tick, datetime.time())
        elif (
            self.active
            and self._waiting_handle is None
            and not self.should_trigger(old=old, new=new)
        ):
            self.log(
                "{} is: {} - inactive [waiting {} to notify]".format(
                    self.entity_id, new, self.delay
                )
            )
            if self._waiting_handle:
                self.cancel_timer(self._waiting_handle)
            self._waiting_handle = self.run_in(
                self._on_deactivate, self.delay, old=old, new=new
            )

        # Power usage goes up before delay
        elif (
            new not in self.EMPTY_NEW_VALUES
            and self.active
            and self._waiting_handle is not None
            and self.should_trigger(old=old, new=new)
        ):
            self.log(
                "{} is: {} - reactivated [cancelling timer]".format(self.entity_id, new)
            )
            self.cancel_timer(self._waiting_handle)
            self._waiting_handle = self.run_minutely(self._tick, datetime.time())
        self.last_value = new

    def _on_deactivate(self, kwargs):
        self.active = False
        if self.input_boolean is not None:
            self.set_state(self.input_boolean, state="off", attributes={})
        self.on_deactivate(kwargs["old"], kwargs["new"])
        self.alert_id = None

    def terminate(self):
        if self._waiting_handle:
            self.cancel_timer(self._waiting_handle)

        for handle in self._timer_handles:
            self.cancel_timer(handle)

        for handle in self._listen_state_handles:
            self.cancel_listen_state(handle)
