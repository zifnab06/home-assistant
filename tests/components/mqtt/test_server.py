"""The tests for the MQTT component embedded server."""
from unittest.mock import MagicMock, patch

from homeassistant.bootstrap import _setup_component
import homeassistant.components.mqtt as mqtt

from tests.common import get_test_home_assistant


class TestMQTT:
    """Test the MQTT component."""

    def setup_method(self, method):
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.hass.config.components.append('http')

    def teardown_method(self, method):
        """Stop everything that was started."""
        self.hass.stop()

    @patch('passlib.apps.custom_app_context', return_value='')
    @patch('tempfile.NamedTemporaryFile', return_value=MagicMock())
    @patch('homeassistant.components.mqtt.MQTT')
    @patch('homeassistant.components.mqtt.server.run_coroutine_threadsafe')
    def test_creating_config_with_http_pass(self, mock_run, mock_mqtt,
                                            mock_temp, mock_context):
        """Test if the MQTT server gets started and subscribe/publish msg."""
        password = 'super_secret'

        self.hass.config.api = MagicMock(api_password=password)
        assert _setup_component(self.hass, mqtt.DOMAIN, {})
        assert mock_mqtt.called
        assert mock_mqtt.mock_calls[0][1][5] == 'homeassistant'
        assert mock_mqtt.mock_calls[0][1][6] == password

        mock_mqtt.reset_mock()

        self.hass.config.components.remove('mqtt')
        self.hass.config.api = MagicMock(api_password=None)
        assert _setup_component(self.hass, mqtt.DOMAIN, {})
        assert mock_mqtt.called
        assert mock_mqtt.mock_calls[0][1][5] is None
        assert mock_mqtt.mock_calls[0][1][6] is None

    @patch('homeassistant.components.mqtt.server.run_coroutine_threadsafe')
    def test_broker_config_fails(self, mock_run):
        """Test if the MQTT component fails if server fails."""
        from hbmqtt.broker import BrokerException

        mock_run.side_effect = BrokerException

        self.hass.config.api = MagicMock(api_password=None)
        assert not _setup_component(self.hass, mqtt.DOMAIN, {
            mqtt.DOMAIN: {mqtt.CONF_EMBEDDED: {}}
        })
