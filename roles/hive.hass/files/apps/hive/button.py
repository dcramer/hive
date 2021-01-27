import appdaemon.plugins.hass.hassapi as hass


class BedsideButton(hass.Hass):
    def initialize(self):
        if "unique_id" not in self.args:
            raise RuntimeError("unique_id not specified for button")

        self.unique_id = self.args.get("unique_id")

        self.listen_event(self.button_event, "zha_event")

    def button_event(self, name, data, kwargs):
        if data["unique_id"] != self.unique_id:
            return
        command = data["command"]
        self.log(f'button.command {command} - {data["unique_id"]}')
        getattr(self, f"{command}_press", lambda: None)()

    def single_press(self):
        if self.get_state("light.master_bedroom_lights") == "off":
            self.turn_on("light.master_bedroom_lights")
        else:
            self.turn_off("light.master_bedroom_lights")

    def double_press(self):
        self.call_service("scene/turn_on", entity_id="scene.bedtime")

    def hold_press(self):
        self.call_service("scene/turn_on", entity_id="scene.lights_out")
