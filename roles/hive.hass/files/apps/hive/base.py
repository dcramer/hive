# import adbase as ad
import appdaemon.plugins.hass.hassapi as hass

from datetime import datetime, timezone, time
from typing import Dict
from uuid import uuid1


def parse_tod(tod: Dict[str, str], tzinfo=timezone.utc) -> Dict[str, time]:
    if not tod:
        return None

    return {
        "after": time(*[int(x) for x in tod["after"].split(":")], tzinfo=tzinfo),
        "before": time(*[int(x) for x in tod["before"].split(":")], tzinfo=tzinfo),
    }


def parse_list(state):
    if isinstance(state, list):
        return frozenset([str(s) for s in state])
    return frozenset([str(state)])


def between(dt: datetime, start: time, stop: time) -> bool:
    cur_time = dt.time().replace(tzinfo=dt.tzinfo)
    if stop > start:  # range does not cross midnight
        return stop >= cur_time >= start
    else:
        return not (cur_time <= start and cur_time >= stop)


class AlertApp(hass.Hass):
    EMPTY_NEW_VALUES = frozenset([None, ""])

    def initialize(self):
        self._timer_handles = []
        self._listen_state_handles = []
        self._delay_handle = None
        self._tick_handle = None

        # is the alert active?
        self.active = None

        # did this alert trigger? (e.g. with skip_first + repeat)
        self.did_alert = False

        # a unique id for the currently active alert
        self.alert_id = None

        # should we skip the first alert? used with repeat
        self.skip_first = self.args.get("skip_first") or False

        # can we acknowledge this via service calls?
        self.can_acknowledge = self.args.get("can_acknowledge", True) or False

        # telegram to ack
        self.ack_command = self.args.get("ack_command") or "/ack"

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
        self.delay = self.args.get("delay") or 0

        # used to store the state of whether this alert is active
        self.input_boolean = self.args.get("input_boolean")
        # self.notify_list = self.args.get("notify") or []
        # TODO: add sonos list?
        # TODO: add script list?

        self._load_previous_state()
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

    # TODO: when we up to appd 4.x
    # @ad.app_lock
    def _load_previous_state(self):
        if self.input_boolean:
            now = float(datetime.utcnow().strftime("%s"))
            state = self.get_state(self.input_boolean)
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
        else:
            self.active = False
            state = None

        if self.active:
            self.log("{} previous state is: {} - active".format(self.entity_id, state))
            self._tick_handle = self.run_every(self._tick, datetime.now(), 60)
            self._test_state(self.last_value, self.get_state(self.entity_id))
        else:
            self.log(
                "{} previous state is: {} - inactive".format(self.entity_id, state)
            )

    def _get_attributes(self):
        return {
            "first_active_at": self.first_active_at,
            "last_active_at": self.last_active_at,
            "last_value": self.last_value,
            "repeat_idx": self.repeat_idx,
            "alert_id": self.alert_id,
        }

    def _tick(self, *args, **kwargs):
        if not self.repeat:
            return
        if not self.active:
            self.log("{} is is ticking but inactive".format(self.entity_id))
            return
        now = float(datetime.utcnow().strftime("%s"))
        if self.repeat_idx > len(self.repeat) - 1:
            self.repeat_idx = len(self.repeat) - 1
        if (self.last_active_at + (self.repeat[self.repeat_idx] * 60)) <= now:
            old = self.last_value
            new = self.get_state(self.entity_id)
            self.repeat_idx = max(self.repeat_idx + 1, len(self.repeat) - 1)
            self.last_active_at = now
            self.last_value = new
            # self.did_alert = (
            #     not self.skip_first or self.last_active_at > self.first_active_at
            # )
            if self.input_boolean is not None:
                self.set_state(
                    self.input_boolean, state="on", attributes=self._get_attributes(),
                )
            self.log("{} is: {} - active [repeat]".format(self.entity_id, new,))
            self.did_alert = True
            self.on_activate(old, new)

    def _state_change(self, entity, attribute, old, new, kwargs):
        self.log("Received state change for {}: {} -> {}".format(entity, old, new))
        self._test_state(old, new)

    def _test_state(self, old, new):
        now = float(datetime.utcnow().strftime("%s"))

        if not self.active and self.should_trigger(old=old, new=new):
            self.active = True
            self.alert_id = uuid1().hex
            self.first_active_at = self.last_active_at = now
            self.repeat_idx = 0
            self.log("{} is: {} - active".format(self.entity_id, new,))
            if self.input_boolean is not None:
                self.set_state(
                    self.input_boolean, state="on", attributes=self._get_attributes(),
                )
            if not self.skip_first:
                self.did_alert = True
                self.on_activate(old, new)
            self._cancel_timers()
            self._tick_handle = self.run_every(self._tick, datetime.now(), 60)
        elif (
            self.active
            and self._delay_handle is None
            and not self.should_trigger(old=old, new=new)
        ):
            self.log(
                "{} is: {} - inactive [waiting {} to notify]".format(
                    self.entity_id, new, self.delay
                )
            )
            self._cancel_timers()
            self._delay_handle = self.run_in(
                self._on_deactivate, self.delay, old=old, new=new
            )

        # Power usage goes up before delay
        elif (
            self.active
            and self._delay_handle is not None
            and self.should_trigger(old=old, new=new)
        ):
            self.log(
                "{} is: {} - reactivated [cancelling timer]".format(self.entity_id, new)
            )
            self._cancel_timers()
            self._tick_handle = self.run_every(self._tick, datetime.now(), 60)
        self.last_value = new

    def _on_deactivate(self, kwargs):
        self.active = False
        if self.input_boolean is not None:
            self.set_state(
                self.input_boolean, state="off", attributes=self._get_attributes()
            )
        if self.did_alert:
            self.on_deactivate(kwargs["old"], kwargs["new"])
        self.alert_id = None
        self.did_alert = False

    def _cancel_timers(self):
        if self._tick_handle:
            self.cancel_timer(self._tick_handle)
        self._tick_handle = None

        if self._delay_handle:
            self.cancel_timer(self._delay_handle)
        self._delay_handle = None

    def terminate(self):
        self._cancel_timers()

        for handle in self._timer_handles:
            self.cancel_timer(handle)

        for handle in self._listen_state_handles:
            self.cancel_listen_state(handle)

    def receive_telegram_command(self, event_id, payload_event, *args):
        if not self.can_acknowledge:
            return
        assert event_id == "telegram_command"
        if self.active and payload_event["command"] == self.ack_command:
            self.log(f"alert acked")
            self._cancel_timers()


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

    now = datetime(2020, 4, 1, 17, 10, tzinfo=timezone.utc)
    assert (
        between(now, time(23, 59, tzinfo=timezone.utc), time(7, 0, tzinfo=timezone.utc))
        is False
    )

    conf = parse_tod({"before": "07:00", "after": "00:00"}, timezone.utc)
    assert conf == {
        "before": time(7, 00, tzinfo=timezone.utc),
        "after": time(0, 0, tzinfo=timezone.utc),
    }

    import pytz

    la_timezone = pytz.timezone("America/Los_Angeles")
    now = datetime(2020, 4, 13, 22, 22, 17, tzinfo=la_timezone)
    after = time(0, 0, tzinfo=la_timezone)
    before = time(7, 0, tzinfo=la_timezone)
    assert not between(now, after, before)
