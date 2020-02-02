import {
  LitElement,
  html,
  css
} from "https://unpkg.com/lit-element@2.0.1/lit-element.js?module";

class NextBusCard extends LitElement {
  static get properties() {
    return {
      hass: Object,
      _config: Object
    };
  }

  render() {
    if (!this._config || !this.hass) {
      return html``;
    }

    // We want:
    // J Church Inbound       1 min
    // Church St & 24th St    16 min

    // state is
    // agency: San Francisco Muni
    // route: J-Church
    // stop: Church St & 24th St
    // message: Ride Muni Free starting at 8pm on New Years Eve until 5am 1/1.
    // direction: Inbound to Embarcadero Station
    // upcoming: '7, 26, 43, 63, 77'
    // friendly_name: sf-muni J
    // icon: 'mdi:bus'
    // device_class: timestamp
    return html`
      <ha-card .header=${this._config.name}>
        <div>
          ${this._config.entities.map(entity => {
            const stateObj = this.hass.states[entity];

            if (!stateObj) {
              return html`
                <hui-error-entity-row
                  .entity="${entity}"
                ></hui-error-entity-row>
              `;
            }

            const isInbound =
              stateObj.attributes.direction.indexOf("Inbound") === 0;
            const routeName = `${stateObj.attributes.route} ${
              isInbound ? "Inbound" : "Outbound"
            }`;

            return html`
              <div>
                <div class="state">
                  ${routeName}
                </div>
              </div>
            `;
          })}
        </div>
      </ha-card>
    `;
  }

  setConfig(config) {
    if (!config.entities || config.entities.length === 0) {
      throw new Error("You need to define at least one entity");
    }
    this._config = {
      name: "Public Transit",
      ...config
    };
  }

  getCardSize() {
    return this._config.entities.length + 1;
  }
}

customElements.define("nextbus-card", NextBusCard);
