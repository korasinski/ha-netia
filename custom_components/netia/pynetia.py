"""
Netia Player
By Jakub Orasiński
KudlatyWORKSHOP.com

Changelog:
- v.0.0.1 initial release
- v.0.0.2 app support, play media, select source

"""

import time
import json
import logging
import requests

TIMEOUT_INTERNAL = 10  # timeout for internal requests (in seconds)
TIMEOUT_EXTERNAL = 60  # timeout for external requests (in seconds)

URL_STATE = "Main/State/get"
URL_VOLUME = "RemoteControl/Volume/get"
URL_KEY = "RemoteControl/KeyHandling/sendKey?key="

URL_CHANNEL_LIST = "Live/Channels/getList"
URL_CHANNEL_CURRENT = "Live/Channels/getCurrent"
URL_CHANNEL_DETAILS = "EPG/Programs/getRange?channelId="
URL_CHANNEL_IMAGE = "EPG/Programs/getImage?channelId="

URL_APPLICATION_LIST = "Applications/State/get"
URL_APPLICATION_OPEN = "Applications/Lifecycle/open?appId="

# URL_NETIA_EPG_APPS_SETTINGS = "http://epg.dms.netia.pl/xmltv/lib/pilot/netiaPadAppsSettings.json"
# URL_NETIA_EPG_APPS_PROMO = "http://epg.dms.netia.pl/xmltv/lib/pilot/netiaPadPromo.json"

URL_NETIA_EPG_LOGO = "http://epg.dms.netia.pl/xmltv/logo/black/"

AVALIABLE_KEYS = [
    '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', 'on_off', 'mute', 'volume_up', 'volume_down', 'channel_up',
    'channel_down', 'back', 'fullscreen', 'menu', 'up', 'down', 'left', 'right', 'ok', 'play', 'stop', 'prev', 'next',
    'rec', 'guide', 'delete', 'red', 'green', 'yellow', 'blue'
]
_LOGGER = logging.getLogger(__name__)


class Netia(object):
    def __init__(self, host, port):  # mac address is optional but necessary if we want to turn on the TV
        """Initialize the Netia Player class."""
        self._host = host
        self._port = port
        self._commands = AVALIABLE_KEYS
        self._application_list = {}

    def netia_set(self, url, content, log_errors=True):
        """Send key command via HTTP to Netia Player."""
        if content is None:
            return False
        else:
            try:
                response = requests.post('http://' + self._host + ':' + self._port + '/' + url + content,
                                         timeout=TIMEOUT_INTERNAL)

            except requests.exceptions.HTTPError as exception_instance:
                if log_errors:
                    _LOGGER.error("HTTPError: " + str(exception_instance))

            except requests.exceptions.Timeout as exception_instance:
                if log_errors:
                    _LOGGER.error("Timeout occurred: " + str(exception_instance))

            except Exception as exception_instance:  # pylint: disable=broad-except
                if log_errors:
                    _LOGGER.error("Exception: " + str(exception_instance))
            else:
                return_response = response.content
                return return_response

    def netia_req_json(self, url, log_errors=True):
        """ Send request via HTTP json to Netia Player."""
        try:
            response = requests.get('http://' + self._host + ':' + self._port + '/' + url,
                                    timeout=TIMEOUT_INTERNAL)

        except requests.exceptions.HTTPError as exception_instance:
            if log_errors:
                _LOGGER.error("HTTPError: " + str(exception_instance))

        except requests.exceptions.Timeout as exception_instance:
            if log_errors:
                _LOGGER.error("Timeout occurred: " + str(exception_instance))

        except Exception as exception_instance:  # pylint: disable=broad-except
            if log_errors:
                _LOGGER.error("Exception: " + str(exception_instance))
        else:
            if response.status_code == 200:
                response = json.loads(response.content.decode('utf-8'))
                if response is None and log_errors:
                    _LOGGER.error(
                        "Invalid response: %s\n  request path: %s" % (
                            response, url))
            else:
                response = None
            return response

    def send_command(self, command):
        """Sends a command to the TV."""
        self.netia_set(URL_KEY, self.get_command_code(command))

    def get_app_list(self):
        """Get list of apps from device."""
        return_value = []
        resp = self.netia_req_json(URL_APPLICATION_LIST, True)
        if resp is not None:
            for i in range(len(resp)):
                app = resp[i]
                if "promo_channel" not in app.get('id'):
                    if app.get('id') == "youtube":
                        app['name'] = "YouTube"
                    if app.get('name') is None:
                        app['name'] = "Unknown app"
                    return_value.append(app)
        return return_value

    def get_app_info(self):
        """Get information on app that is currently open."""
        return_value = {}
        resp = self.get_app_list()
        if resp is not None:
            self._application_list = resp
            for app in resp:
                if app.get('current') is True:
                    if app.get('id') in ['tv', 'settings', 'epg']:
                        return_value['id'] = 'tv'
                        return_value['name'] = 'TV'
                        return_value['image'] = None
                    else:
                        return_value['id'] = app.get('id')
                        return_value['name'] = app.get('name')
                        return_value['image'] = self.get_app_picture(app.get('id'))
            if len(return_value) is 0:
                return_value['id'] = "tv"
                return_value['name'] = "TV"
                return_value['image'] = None

        return return_value

    def get_app_picture(self, app, log_errors=True):
        """Get application picture from Netia server."""
        url = URL_NETIA_EPG_LOGO + app + '_290x172px.png'
        if app is None:
            return False
        else:
            try:
                response = requests.post(url, timeout=TIMEOUT_EXTERNAL)

            except requests.exceptions.HTTPError as exception_instance:
                if log_errors:
                    _LOGGER.error("HTTPError: " + str(exception_instance))

            except requests.exceptions.Timeout as exception_instance:
                if log_errors:
                    _LOGGER.error("Timeout occurred: " + str(exception_instance))

            except Exception as exception_instance:  # pylint: disable=broad-except
                if log_errors:
                    _LOGGER.error("Exception: " + str(exception_instance))
            else:
                if response.status_code == 200:
                    return url

    def get_channel_info(self):
        """Get information on program that is shown on TV."""
        return_value = {}
        channel = self.netia_req_json(URL_CHANNEL_CURRENT, True)
        if channel is not None:
            return_value['id'] = channel.get('id')
            return_value['media_channel'] = channel.get('zap')
            return_value['channel_name'] = channel.get('name')
            return_value['image'] = 'http://' + self._host + ':' + self._port + "/" + URL_CHANNEL_IMAGE + str(
                requests.utils.quote(channel.get('id')))
        else:
            return_value = None
        return return_value

    def get_channel_details(self, channel_id):
        """Get information on program that is shown on TV."""
        return_value = {}
        timestamp = int(time.time())
        details_url = URL_CHANNEL_DETAILS + str(requests.utils.quote(channel_id)) + "&startTime=" + str(
            timestamp) + "&endTime=" + str(
            timestamp)
        channel_details = self.netia_req_json(details_url, True)
        if channel_details is not None:
            channel_details = channel_details[0]
            return_value['media_channel'] = channel_details.get('channelZap')
            return_value['channel_name'] = channel_details.get('channelName')
            return_value['image'] = 'http://' + self._host + ':' + self._port + str(channel_details.get('image'))
            return_value['program_name'] = channel_details.get('name')
            return_value['program_media_type'] = channel_details.get('subcategory')
            return_value['media_episode'] = channel_details.get('episodeInfo')
            return_value['sound_mode'] = channel_details.get('audio')
            return_value['duration'] = channel_details.get('duration')
            return_value['start_time'] = channel_details.get('startTime')
            return_value['end_time'] = channel_details.get('endTime')
        else:
            return_value = None
        return return_value

    def get_standby_status(self):
        """Get standby status: on, off"""
        return_value = 'on'  # by default the Netia Player is in standby mode
        try:
            resp = self.netia_req_json(URL_STATE, False)
            if resp.get('standby') is False:
                return_value = 'off'
            else:
                return_value = 'on'
        except:  # pylint: disable=broad-except
            pass
        return return_value

    def get_command_code(self, command_name):
        """Check if command is supported."""
        for command_data in self._commands:
            if command_data == command_name:
                return command_data
        return None

    def get_volume_info(self):
        """Get volume info."""
        resp = self.netia_req_json(URL_VOLUME, True)
        if not resp.get('error'):
            result = resp
            return result
        else:
            _LOGGER.error("JSON data error:" + json.dumps(resp, indent=4))
        return None

    def available_keys(self):
        return self._commands

    def application_list(self):
        return self._application_list

    def open_app(self, app):
        """Play content by URI."""
        self.netia_set(URL_APPLICATION_OPEN, app, False)

    def volume_up(self):
        """Volume up the media player."""
        self.netia_set(URL_KEY, self.get_command_code('volume_up'))

    def volume_down(self):
        """Volume down media player."""
        self.netia_set(URL_KEY, self.get_command_code('volume_down'))

    def mute_volume(self):
        """Send mute command."""
        self.netia_set(URL_KEY, self.get_command_code('mute'))

    def turn_on(self):
        """Turn the media player on."""
        self.netia_set(URL_KEY, self.get_command_code('on_off'))

    def turn_off(self):
        """Turn the media player off."""
        self.netia_set(URL_KEY, self.get_command_code('on_off'))

    def media_play(self):
        """Send play command."""
        self.netia_set(URL_KEY, self.get_command_code('play'))

    def media_pause(self):
        """Send media pause command to media player."""
        self.netia_set(URL_KEY, self.get_command_code('pause'))

    def media_stop(self):
        """Send media pause command to media player."""
        self.netia_set(URL_KEY, self.get_command_code('stop'))

    def media_next_track(self):
        """Send next track command."""
        self.netia_set(URL_KEY, self.get_command_code('channel_up'))

    def media_previous_track(self):
        """Send the previous track command."""
        self.netia_set(URL_KEY, self.get_command_code('channel_down'))
