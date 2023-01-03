from base import AlertApp, parse_list


class AutomaticLight(AlertApp):
    EMPTY_NEW_VALUES = frozenset([None, "", "unavailable"])

    def initialize(self):
        self.states = parse_list(self.args.get("state"))
        self.lights = parse_list(self.args.get("light"))

        super().initialize()

    def should_trigger(self, old, new):
        # dont run if any lights are already manually controlled
        # TODO(dcramer): we can improve this so it only turns on the uncontrolled light
        if any(self.get_state(light) == "on" for light in self.lights):
            return False

        if not self.now_is_between("sunset - 00:45:00", "sunrise + 00:45:00"):
            return False

        return new in self.states

    def on_activate(self, *args, **kwargs):
        for light in self.lights:
            self.call_service("light/turn_on", entity_id=light, brightness_pct=100)

    def on_deactivate(self, *args, **kwargs):
        for light in self.lights:
            self.call_service("light/turn_off", entity_id=light)
