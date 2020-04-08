"""
Support for interface with a Netia Player

For more details about this platform, please refer to the documentation at
https://github.com/korasinski/ha-neti
"""
import logging
import time
import voluptuous as vol
from pyNetia import PyNetia
from homeassistant.components.media_player import (
    MediaPlayerDevice, PLATFORM_SCHEMA)
try:
    from homeassistant.components.media_player.const import (
        SUPPORT_NEXT_TRACK, SUPPORT_PAUSE, SUPPORT_PREVIOUS_TRACK,
        SUPPORT_TURN_ON, SUPPORT_TURN_OFF, SUPPORT_VOLUME_MUTE, SUPPORT_PLAY,
        SUPPORT_PLAY_MEDIA, SUPPORT_VOLUME_STEP, SUPPORT_VOLUME_SET,
        SUPPORT_SELECT_SOURCE, SUPPORT_STOP, MEDIA_TYPE_TVSHOW, MEDIA_TYPE_APP)
except ImportError:
    from homeassistant.components.media_player import (
        SUPPORT_NEXT_TRACK, SUPPORT_PAUSE, SUPPORT_PREVIOUS_TRACK,
        SUPPORT_TURN_ON, SUPPORT_TURN_OFF, SUPPORT_VOLUME_MUTE, SUPPORT_PLAY,
        SUPPORT_PLAY_MEDIA, SUPPORT_VOLUME_STEP, SUPPORT_VOLUME_SET,
        SUPPORT_SELECT_SOURCE, SUPPORT_STOP)
from homeassistant.const import (
    CONF_HOST, CONF_PORT, CONF_NAME, STATE_OFF, STATE_ON, STATE_PLAYING)
import homeassistant.helpers.config_validation as cv
from homeassistant.util.dt import utcnow

_VERSION = "0.1.0"

_LOGGER = logging.getLogger(__name__)

SUPPORT_NETIA = \
    SUPPORT_TURN_ON | SUPPORT_TURN_OFF | SUPPORT_VOLUME_MUTE | SUPPORT_VOLUME_STEP | \
    SUPPORT_PREVIOUS_TRACK | SUPPORT_NEXT_TRACK | SUPPORT_PLAY_MEDIA | SUPPORT_PAUSE

DEFAULT_NAME = 'Netia Player'
DEVICE_CLASS_TV = 'tv'

# Config file
DEFAULT_PORT = '8080'
CONF_APP = 'app_support'
CONF_APP_LIST = 'app_list'

# Some additional info to show specific for Netia Player
TV_WAIT = 'TV started, waiting for program info'
TV_APP_OPENED = 'App opened'
TV_NO_INFO = 'No info'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_APP, default=False): cv.boolean,
    vol.Optional(CONF_APP_LIST, default=['tv']): vol.All(
        cv.ensure_list, [cv.string])
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Netia Player platform."""
    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)
    name = config.get(CONF_NAME)
    app_support = config.get(CONF_APP)
    app_list = config.get(CONF_APP_LIST)

    if host is None:
        _LOGGER.error(
            "No Netia Player IP address found in configuration file")
        return

    add_devices([Netia(host, port, name, app_support, app_list)])


class Netia(MediaPlayerDevice):
    """Representation of a Netia Player."""

    def __init__(self, host, port, name, app_support, app_list):
        """Initialize the Netia Player device."""
        _LOGGER.info("Setting up Netia Player")

        self._netia = PyNetia(host, port)
        self._name = name
        self._app_support = app_support
        self._app_list = app_list
        self._state = None
        self._muted = False
        self._program_name = None
        self._channel_name = None
        self._channel_number = None
        self._available_keys = self._netia.available_keys()
        self._supported_apps = self._netia.supported_apps()
        self._application_list = {}
        self._media_episode = None
        self._media_channel = None
        self._media_image_url = None
        self._sound_mode = None
        self._source = None
        self._source_list = []
        self._duration = None
        self._playing = False
        self._media_content_type = None
        self._volume = None
        self._start_time = None
        self._end_time = None
        self._device_class = DEVICE_CLASS_TV
        self._unique_id = '{}-{}'.format(host, name)
        _LOGGER.debug("Seting up Netia Player with IP: %s:%s and app support: %s.", host, port, app_support)

        self.update()

    def update(self):
        """Update Netia Player device info."""
        try:
            standby_status = self._netia.get_standby_status()
            self._reset_channel_info()
            if standby_status == 'off':  # Device is turned ON!
                self._state = STATE_ON
                self._refresh_volume()
                app_info = self._netia.get_app_info()
                if app_info is not None:
                    self._refresh_apps(app_info.get('id'), app_info.get('name'))
                    if app_info.get('id') is 'tv':
                        channel_info = self._netia.get_channel_info()
                        if channel_info is not None:
                            self._media_channel = channel_info.get('media_channel')
                            self._channel_name = channel_info.get('channel_name')
                            self._program_name = TV_WAIT
                            self._state = STATE_PLAYING
                            channel_details = self._netia.get_channel_details(channel_info.get('id'))
                            if channel_details is not None:
                                self._reset_channel_info()
                                self._media_channel = channel_info.get('media_channel')
                                self._channel_name = channel_info.get('channel_name')
                                self._media_image_url = channel_details.get('image')
                                self._program_name = channel_details.get('program_name')
                                self._media_content_type = channel_details.get('program_media_type')
                                self._media_episode = channel_details.get('media_episode')
                                self._sound_mode = channel_details.get('sound_mode')
                                self._duration = channel_details.get('duration')
                                self._start_time = channel_details.get('start_time')
                                self._end_time = channel_details.get('end_time')
                            else:
                                self._program_name = TV_NO_INFO
                        else:
                            self._program_name = TV_NO_INFO
                    else:
                        self._reset_channel_info()
                        self._channel_name = app_info.get('name')
                        self._media_image_url = app_info.get('image')
                        self._state = TV_APP_OPENED
            else:  # Device is turned OFF
                if self._program_name is TV_WAIT:
                    # Device is starting up, takes some time before it responds
                    _LOGGER.info("TV is starting, no info available yet")
                else:
                    self._state = STATE_OFF

        except Exception as exception_instance:  # pylint: disable=broad-except
            _LOGGER.debug("No data received from device. Error message: %s", exception_instance)
            self._state = STATE_OFF

    def _reset_channel_info(self):
        """Reset channel details."""
        self._program_name = None
        self._channel_name = None
        self._media_content_type = None
        self._channel_number = None
        self._media_channel = None
        self._media_episode = None
        self._sound_mode = None
        self._content_uri = None
        self._duration = None
        self._start_time = None
        self._end_time = None
        self._media_image_url = None

    def _refresh_volume(self):
        """Refresh volume information."""
        volume_info = self._netia.get_volume_info()
        if volume_info is not None:
            self._volume = volume_info.get('volume')
            self._muted = volume_info.get('muted')
        else:
            self._volume = None
            self._muted = None

    def _refresh_apps(self, current_id, current_name):
        """Refresh application list."""
        if self._app_support is True:
            self._application_list = self._netia.application_list()

            source_list = []
            if self._app_list is not None:
                if 'tv' not in self._app_list:
                    source_list.append('TV')
                if current_id not in self._app_list:
                    self._app_list.append(current_id)
                for app in self._app_list:
                    for app_name in self._application_list:
                        if app == app_name.get('id'):
                            source_list.append(app_name.get('name'))
            else:
                for app in self._application_list:
                    source_list.append(app.get('name'))
            if current_name in source_list:
                self._source = current_name
                self._source_list = source_list
        else:
            self._source = None
            self._source_list = []

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        if self._volume is not None:
            return self._volume / 100
        return None

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._muted

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique ID of the device."""
        return self._unique_id

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def source(self):
        """Return the current input source."""
        return self._source

    @property
    def source_list(self):
        """List of available input sources."""
        return self._source_list

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        supported = SUPPORT_NETIA
        if self._app_support is True:
            supported = supported ^ SUPPORT_SELECT_SOURCE
        return supported

    @property
    def media_content_type(self):
        """Content type of current playing media.
        Used for program information below the channel in the state card. """
        return MEDIA_TYPE_TVSHOW

    @property
    def media_title(self):
        """Title of current playing media.
        Used to show TV channel info."""
        return_value = None
        if self._channel_name is not None:
            return_value = self._channel_name
        return return_value

    @property
    def media_series_title(self):
        """Title of series of current playing media, TV show only.
        Used to show TV program info.
        """
        return_value = None
        if self._program_name is not None:
            return_value = self._program_name
        else:
            if not self._channel_name:  # This is empty when app is opened
                return_value = TV_APP_OPENED
        return return_value

    @property
    def media_content_id(self):
        """Content ID of current playing media."""
        return self._channel_name

    @property
    def media_episode(self):
        """Episode of current playing media, TV show only."""
        if self._media_episode is not None:
            return_value = self._media_episode
        else:
            return_value = None
        return return_value

    @property
    def media_channel(self):
        """Channel currently playing."""
        if self._media_channel is not None:
            return_value = self._media_channel
        else:
            return_value = None
        return return_value

    @property
    def media_image_url(self):
        """Image url of current playing media."""
        if self._media_image_url is not None:
            return_value = self._media_image_url
        else:
            return_value = None
        return return_value

    @property
    def media_duration(self):
        """Duration of current playing media in seconds."""
        if self._duration is not None:
            return_value = self._duration
        else:
            return_value = None
        return return_value

    @property
    def media_position(self):
        """Position of current playing media in seconds."""
        if self.media_duration is not None:
            start_time = self._start_time
            current_time = int(time.time())
            return_value = current_time - start_time
        else:
            return_value = None
        return return_value

    @property
    def media_position_updated_at(self):
        """When was the position of the current playing media valid.
        Returns value from homeassistant.util.dt.utcnow()."""
        if self.media_position is not None:
            return utcnow()
        return None

    @property
    def sound_mode(self):
        """Name of the current sound mode."""
        if self._sound_mode is not None:
            return_value = self._sound_mode
        else:
            return_value = None
        return return_value

    @property
    def device_class(self):
        """Return the device class of the media player."""
        return self._device_class

    def turn_on(self):
        """Turn the media player on."""
        self._netia.turn_on()
        self._reset_channel_info()
        self._state = STATE_ON
        self._program_name = TV_WAIT

    def turn_off(self):
        """Turn the media player off."""
        self._netia.turn_off()
        self._state = STATE_OFF

    def volume_up(self):
        """Volume up the media player."""
        self._netia.volume_up()

    def volume_down(self):
        """Volume down media player."""
        self._netia.volume_down()

    def mute_volume(self, mute):
        """Send mute command."""
        self._netia.mute_volume()

    # def media_play_pause(self):
    #     """Simulate play pause media player."""
    #     if self._playing:
    #         self.media_stop()
    #     else:
    #         self.media_play()
    #
    # def media_play(self):
    #     """Send play command."""
    #     self._playing = True
    #     self._netia.media_play()
    #
    def media_pause(self):
        """Send media pause command to media player."""
        self._netia.turn_off()
        self._state = STATE_OFF

    # def media_stop(self):
    #     """Send media pause command to media player."""
    #     self._netia.turn_off()
    #     self._state = STATE_OFF

    def media_next_track(self):
        """Send next track command."""
        self._netia.media_next_track()

    def media_previous_track(self):
        """Send the previous track command."""
        self._netia.media_previous_track()

    def select_source(self, source):
        """Set the input source."""
        for app in self._application_list:
            if app.get('name') == source:
                self._netia.open_app(app.get('id'))

    def play_media(self, media_type, media_id, **kwargs):
        """Play media."""
        _LOGGER.debug("Play media: %s (%s)", media_id, media_type)
        if media_id in self._available_keys:
            self._netia.send_command(media_id)
        else:
            _LOGGER.warning("Unsupported media_id: %s", media_id)
