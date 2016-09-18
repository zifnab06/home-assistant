"""
Support for a local MQTT broker.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/mqtt/#use-the-embedded-broker
"""
import asyncio
import logging
import tempfile

from homeassistant.components.mqtt import PROTOCOL_311
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.util.async import run_coroutine_threadsafe

REQUIREMENTS = ['hbmqtt==0.7.1']
DEPENDENCIES = ['http']


@asyncio.coroutine
def broker_coro(loop, config):
    """Start broker coroutine."""
    from hbmqtt.broker import Broker
    broker = Broker(config, loop)
    yield from broker.start()
    return broker


def start(hass, server_config):
    """Initialize MQTT Server."""
    from hbmqtt.broker import BrokerException

    try:
        passwd = tempfile.NamedTemporaryFile()

        if server_config is None:
            server_config, client_config = generate_config(hass, passwd)
        else:
            client_config = None

        future = run_coroutine_threadsafe(
            broker_coro(hass.loop, server_config), hass.loop)

        broker = future.result()
    except BrokerException:
        logging.getLogger(__name__).exception('Error initializing MQTT server')
        return False, None
    finally:
        passwd.close()

    @asyncio.coroutine
    def shutdown_mqtt_server(event):
        """Shut down the MQTT server."""
        yield from broker.shutdown()

    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, shutdown_mqtt_server)

    return True, client_config


def generate_config(hass, passwd):
    """Generate a configuration based on current Home Assistant instance."""
    config = {
        'listeners': {
            'default': {
                'max-connections': 50000,
                'bind': '0.0.0.0:1883',
                'type': 'tcp',
            },
            'ws-1': {
                'bind': '0.0.0.0:8080',
                'type': 'ws',
            },
        },
        'auth': {
            'allow-anonymous': hass.config.api.api_password is None
        },
        'plugins': ['auth_anonymous'],
    }

    if hass.config.api.api_password:
        username = 'homeassistant'
        password = hass.config.api.api_password

        # Encrypt with what hbmqtt uses to verify
        from passlib.apps import custom_app_context

        passwd.write(
            'homeassistant:{}\n'.format(
                custom_app_context.encrypt(
                    hass.config.api.api_password)).encode('utf-8'))
        passwd.flush()

        config['auth']['password-file'] = passwd.name
        config['plugins'].append('auth_file')
    else:
        username = None
        password = None

    client_config = ('localhost', 1883, username, password, None, PROTOCOL_311)

    return config, client_config
