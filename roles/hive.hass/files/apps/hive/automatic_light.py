from base import AlertApp, parse_state


class AutomaticLight(AlertApp):
    EMPTY_NEW_VALUES = frozenset([None, "", "unavailable"])

    def initialize(self):
        self.states = parse_state(self.args.get("state"))
        self.light_entity = self.args.get("light_entity")

        super().initialize()

    def should_trigger(self, old, new):
        return new in self.states

    def on_activate(self, *args, **kwargs):
        self.call_service(
            "light/turn_on", entity_id=self.light_entity, brightness_pct=100
        )

    def on_deactivate(self, *args, **kwargs):
        self.call_service("light/turn_off", entity_id=self.light_entity)
