"""
Netia Player
By Jakub Orasiński
KudlatyWORKSHOP.com

Changelog:
- v.0.1 initial release

"""

import time
import json
import logging
import requests

TIMEOUT = 10 # timeout in seconds

URL_STATE = "Main/State/get"
URL_VOLUME = "RemoteControl/Volume/get"
URL_KEY = "RemoteControl/KeyHandling/sendKey?key="

URL_CHANNEL_LIST = "Live/Channels/getList"
URL_CHANNEL_CURRENT = "Live/Channels/getCurrent"
URL_CHANNEL_DETAILS = "EPG/Programs/getRange?channelId="
URL_CHANNEL_IMAGE = "EPG/Programs/getImage?channelId="

URL_APPLICATION_LIST = "Applications/State/get"
URL_APPLICATION_OPEN = "Applications/Lifecycle/open?appId="

AVALIABLE_KEYS = ['on_off', 'mute', 'volume_up', 'volume_down', 'channel_up', 'channel_down', 'back', 'fullscreen',
                 'menu', 'up', 'down', 'left', 'right', 'ok', 'play', 'stop', 'prev', 'next', 'rec', 'guide', 'delete',
                 'red', 'green', 'yellow', 'blue']

_LOGGER = logging.getLogger(__name__)

class Netia(object):

    def __init__(self, host, port):  # mac address is optional but necessary if we want to turn on the TV
        """Initialize the Netia Player class."""

        self._host = host
        self._port = port
        self._commands = AVALIABLE_KEYS
        self._content_mapping = []

    def netia_set_key(self, key, log_errors=True):
        """Send key command via HTTP to Netia Player."""
        if key is None:
            return False

        try:
            response = requests.post('http://' + self._host + ':' + self._port + '/' + URL_KEY + key,
                                     timeout=TIMEOUT)

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
            content = response.content
            return content

    def netia_req_json(self, url, log_errors=True):
        """ Send request via HTTP json to Netia Player."""
        try:
            response = requests.post('http://' + self._host + ':' + self._port + '/' + url,
                                     timeout=TIMEOUT)

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
            response = json.loads(response.content.decode('utf-8'))
            if response is None and log_errors:
                _LOGGER.error(
                    "Invalid response: %s\n  request path: %s" % (
                        response, url))

            return response

    def send_command(self, command):
        """Sends a command to the TV."""
        self.netia_set_key(self.get_command_code(command))

    def get_playing_info(self):
        """Get information on program that is shown on TV."""
        return_value = {}
        resp = self.netia_req_json(URL_CHANNEL_CURRENT, False)
        if resp is not None:
            return_value = resp

            if resp.get('epg') is True:
                return_value = resp

            else:
                if resp.get('id') == "giganagrywarka":
                    gig = {}
                    gig['channelZap'] = 0
                    gig['channelName'] = "Giganagrywarka"
                    gig['name'] = 'Netia'
                    gig['subcategory'] = ""
                    gig['episodeInfo'] = "Nieznany program"
                    gig['image'] = '/' + URL_CHANNEL_IMAGE + "giganagrywarka"
                    gig['startTime'] = int(time.time())
                    gig['endTime'] = int(time.time()) + 3600
                    return_value = gig

                else:
                    timestamp = int(time.time())
                    detail_req_url = URL_CHANNEL_DETAILS + resp.get('id') + "&startTime=" + str(
                        timestamp) + "&endTime=" + str(timestamp)
                    detail_resp = self.netia_req_json(detail_req_url, False)

                    if detail_resp is not None:
                        return_value = detail_resp[0]

        return return_value


    def get_standby_status(self):
        """Get standby status: on, off"""
        return_value = 'on' # by default the Netia Player is in standby mode
        try:
            resp = self.netia_req_json(URL_STATE, False)
            if resp.get('standby') == False:
                return_value = 'off'
            else:
                return_value = 'on'

        except:   # pylint: disable=broad-except
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

    def volume_up(self):
        """Volume up the media player."""
        self.netia_set_key(self.get_command_code('volume_up'))

    def volume_down(self):
        """Volume down media player."""
        self.netia_set_key(self.get_command_code('volume_down'))

    def mute_volume(self):
        """Send mute command."""
        self.netia_set_key(self.get_command_code('mute'))

    def turn_on(self):
        """Turn the media player on."""
        self.netia_set_key(self.get_command_code('on_off'))

    def turn_off(self):
        """Turn the media player off."""
        self.netia_set_key(self.get_command_code('on_off'))

    def media_play(self):
        """Send play command."""
        self.netia_set_key(self.get_command_code('play'))

    def media_pause(self):
        """Send media pause command to media player."""
        self.netia_set_key(self.get_command_code('pause'))

    def media_stop(self):
        """Send media pause command to media player."""
        self.netia_set_key(self.get_command_code('stop'))

    def media_next_track(self):
        """Send next track command."""
        self.netia_set_key(self.get_command_code('channel_up'))

    def media_previous_track(self):
        """Send the previous track command."""
        self.netia_set_key(self.get_command_code('channel_down'))