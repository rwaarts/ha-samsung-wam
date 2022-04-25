import urllib.parse
import async_timeout
import aiohttp
import asyncio
import re
import logging
import voluptuous as vol
import homeassistant.util as util

from datetime import timedelta
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

VERSION = '1.0.1'

DOMAIN = "samsung_wam"

# moveing timers from 3+3 sec to 6+10 sec because it does not get any statuses at the moment
MIN_TIME_BETWEEN_SCANS = timedelta(seconds=6)
MIN_TIME_BETWEEN_FORCED_SCANS = timedelta(seconds=10)

from homeassistant.helpers import config_validation as cv
from homeassistant.components import media_source
from homeassistant.components.media_player.browse_media import (
    async_process_play_media_url,
)

from homeassistant.components.media_player import (
  SUPPORT_PLAY,
  SUPPORT_PLAY_MEDIA,
  SUPPORT_STOP,
  SUPPORT_TURN_ON,
  SUPPORT_TURN_OFF,
  SUPPORT_VOLUME_MUTE,
  SUPPORT_VOLUME_SET,
  SUPPORT_SELECT_SOURCE,
  SUPPORT_BROWSE_MEDIA,
  BrowseMedia,
  MediaPlayerEntity,
  PLATFORM_SCHEMA,
)

from homeassistant.components.media_player.const import (
  MEDIA_TYPE_CHANNEL,
  MEDIA_TYPE_MUSIC,
  MEDIA_TYPE_CHANNEL,
  MEDIA_TYPE_MUSIC,
  MEDIA_TYPE_URL,
)

from homeassistant.const import (
  CONF_NAME,
  CONF_HOST,
  STATE_ON,
  STATE_OFF,
  STATE_UNAVAILABLE,
  STATE_PAUSED,
  STATE_PLAYING,
  STATE_IDLE,
  STATE_UNKNOWN,
)

MULTI_ROOM_SOURCE_TYPE = [
  'optical',
  'soundshare',
  'hdmi',
  'wifi',
  'aux',
  'bt',
  'wifi - TuneIn'
  #wifi - submode: dlna, cp
]

DEFAULT_NAME = 'Samsung WAM'
DEFAULT_PORT = '55001'
DEFAULT_POWER_OPTIONS = False
DEFAULT_MAX_VOLUME = '10'
BOOL_OFF = 'off'
BOOL_ON = 'on'
TIMEOUT = 10
SUPPORT_SAMSUNG_MULTI_ROOM = SUPPORT_VOLUME_SET | SUPPORT_VOLUME_MUTE | SUPPORT_SELECT_SOURCE | SUPPORT_PLAY | SUPPORT_PLAY_MEDIA | SUPPORT_STOP | SUPPORT_BROWSE_MEDIA 

CONF_MAX_VOLUME = 'max_volume'
CONF_PORT = 'port'
CONF_POWER_OPTIONS = 'power_options'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
  vol.Required(CONF_HOST, default='127.0.0.1'): cv.string,
  vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
  vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.string,
  vol.Optional(CONF_MAX_VOLUME, default=DEFAULT_MAX_VOLUME): cv.string,
  vol.Optional(CONF_POWER_OPTIONS, default=DEFAULT_POWER_OPTIONS): cv.boolean
})

class WAMApi():
  def __init__(self, ip, port, session, hass):
    self.session = session
    self.hass = hass
    self.ip = ip
    self.port = port
    self.endpoint = 'http://{0}:{1}'.format(ip, port)

  async def _exec_cmd(self, mode ,cmd, key_to_extract):
    import xmltodict
    query = urllib.parse.urlencode({ "cmd": cmd }, quote_via=urllib.parse.quote)
    url = '{0}/{1}?{2}'.format(self.endpoint, mode, query)

    try:
      with async_timeout.timeout(TIMEOUT):
        _LOGGER.debug("Executing: {} with cmd: {}".format(url, cmd))
        response = await self.session.get(url)
        data = await response.text()
        _LOGGER.debug(data)
        if data and key_to_extract:
          return re.findall(key_to_extract,data)
        return None
    except:
      _LOGGER.debug("exception")
      return None

  async def _exec_get(self, mode, action, key_to_extract):
    return await self._exec_cmd(mode, '<name>{0}</name>'.format(action), key_to_extract)

  async def _exec_set(self, mode, action, property_name, value):
    if type(value) is str:
      value_type = 'str'
    else:
      value_type = 'dec'
    cmd = '<name>{0}</name><p type="{3}" name="{1}" val="{2}"/>'.format(action, property_name, value, value_type)
    return await self._exec_cmd(mode, cmd, property_name)

  async def _exec_play(self, mode, action, property_name, value, p2, v2):
    if type(value) is str:
      value_type = 'str'
    else:
      value_type = 'dec'
    cmd = '<name>{0}</name><p type="{3}" name="{1}" val="{2}"/><p type="{3}" name="{4}" val="{5}"/>'.format(action, property_name, value, value_type, p2, v2)
    return await self._exec_cmd(mode, cmd, property_name)

  async def _exec_play_url(self, media, property_name):
    #cmd = '<name>{0}</name><p type="{3}" name="{1}" val="{2}"/><p type="{3}" name="{4}" val="{5}"/>'.format(action, property_name, value, value_type, p2, v2)
    cmd = '<name>SetUrlPlayback</name><p type="cdata" name="url" val="empty"><![CDATA[{0}]]></p><p type="dec" name="buffersize" val="0"/><p type="dec" name="seektime" val="0"/><p type="dec" name="resume" val="1"/>'.format(media)
    return await self._exec_cmd('UIC', cmd, property_name)

  async def _exec_pause_url(self,action):
    # http://192.168.62.228:55001/UIC?cmd=%3Cname%3ESetPlaybackControl%3C/name%3E%3Cp%20type=%22str%22%20name=%22playbackcontrol%22%20val=%22play%22/%3E
    cmd = '<name>SetPlaybackControl</name><p type="str" name="playbackcontrol" val="{0}"/>'.format(action)
    return await self._exec_cmd('UIC', cmd, 'playstatus')

  async def get_state(self):
    result = await self._exec_get('UIC','GetPowerStatus', '<powerStatus>(.*?)</powerStatus>')
    if result:
      return result[0]
    return 0

  async def set_state(self, key):
    await self._exec_set('UIC','SetPowerStatus', 'powerStatus', int(key))

  async def get_main_info(self):
    return await self._exec_get('UIC','GetMainInfo')

  async def get_volume(self):
    return await self._exec_get('UIC','GetVolume', '<volume>(.*?)</volume')

  async def set_volume(self, volume):
    await self._exec_set('UIC','SetVolume', 'volume', int(volume))

  async def get_speaker_name(self):
    return await self._exec_get('UIC','GetSpkName', '<spkname>(.*?)</spkname>')

  async def get_radio_info(self):
    return await self._exec_get('CPM','GetRadioInfo', '<title>(.*?)</title>')

  async def get_radio_image(self):
    return await self._exec_get('CPM','GetRadioInfo', '<thumbnail>(.*?)</thumbnail>')

  async def get_muted(self):
    return await self._exec_get('UIC','GetMute', '<mute>(.*?)</mute>') == BOOL_ON

  async def play_url(self, media):
    return await self._exec_play_url(media, 'response')

  async def pause_url(self, media):
    return await self._exec_pause_url(media)

  async def set_muted(self, mute):
    if mute:
      await self._exec_set('UIC','SetMute', 'mute', BOOL_ON)
    else:
      await self._exec_set('UIC','SetMute', 'mute', BOOL_OFF)

  async def get_source(self):
    "res[0] = source ; res[1] = mode"
    res = []
    result = await self._exec_get('UIC','GetFunc', '<response result="ok">(.*?)</response>')
    if result:
      function = re.findall('<function>(.*?)</function>',result[0])[0]
      res.append(function)
      if function == 'bt':
        res.append(False)
      else:
        mode = re.findall('<submode>(.*?)</submode>',result[0])
        if mode and mode[0] == 'cp':
          res.append('TuneIn')
        else:
          res.append(False)
      return res
    return None

  async def set_source(self, source):
    SEPARATOR = ' - '
    if SEPARATOR in source:
      r = source.split(SEPARATOR)
      await self._exec_play('CPM','PlayById', 'cpname', r[1], 'mediaid', 's137149')
    else:
      await self._exec_set('UIC','SetFunc', 'function', source)

  async def get_apinfo(self):
    res = []
    result = await self._exec_get('UIC','GetApInfo', '<response result="ok">(.*?)</response>')
    if result:
      ssid = re.findall('<ssid>(.*?)</ssid>',result[0])[0]
      mac  = re.findall('<mac>(.*?)</mac>',result[0])[0]
      rssi  = re.findall('<rssi>(.*?)</rssi>',result[0])[0]
      ch  = re.findall('<ch>(.*?)</ch>',result[0])[0]
      contype  = re.findall('<connectiontype>(.*?)</connectiontype>',result[0])[0]
      wifidirectssid  = re.findall('<wifidirectssid>(.*?)</wifidirectssid>',result[0])[0]
      res.append(ssid)
      res.append(mac)
      res.append(ch)
      return res
    return None

  async def get_softwareinfo(self):
    res = []
    result = await self._exec_get('UIC','GetSoftwareVersion', '<response result="ok">(.*?)</response>')
    if result:
      version = re.findall('<version>(.*?)</version>',result[0])[0]
      display  = re.findall('<displayversion>(.*?)</displayversion>',result[0])[0]
      res.append('Version: {0}'.format(version))
      res.append('Display: {0}'.format(display))
      return res
    return None

class WAMDevice(MediaPlayerEntity):
  """Representation of a Samsung MultiRoom device."""
  def __init__(self, name, max_volume, power_options ,api):
    _LOGGER.info('Initializing WAMDevice')
    self._name = name
    self.api = api
    self._state = STATE_OFF
    self._current_source = None
    self._media_title = ''
    self._image_url = ''
    self._volume = 0
    self._mode = ''
    self._muted = False
    self._max_volume = max_volume
    self._power_options = power_options

  @property
  def supported_features(self):
    """Flag media player features that are supported."""
    if self._power_options:
      return SUPPORT_SAMSUNG_MULTI_ROOM | SUPPORT_TURN_OFF | SUPPORT_TURN_ON
    return SUPPORT_SAMSUNG_MULTI_ROOM

  @property
  def name(self):
    """Return the name of the device."""
    return self._name

  @property
  def media_title(self):
    """Title of current playing media."""
    return self._media_title

  @property
  def media_image_url(self):
    """Url for image of current playing media."""
    return self._image_url

  @property
  def state(self):
    """Return the state of the device."""
    return self._state

  @property
  def mode(self):
    """Return the sub mode of the device."""
    return self._mode

  @property
  def volume_level(self):
    """Return the volume level."""
    return self._volume

  async def async_set_volume_level(self, volume):
    """Sets the volume level."""
    newVolume = volume * self._max_volume
    await self.api.set_volume(newVolume)
    self._volume = volume

  @property
  def is_volume_muted(self):
    """Boolean if volume is currently muted."""
    return self._muted

  async def async_mute_volume(self, mute):
    """Sets volume mute to true."""
    await self.api.set_muted(mute)
    self._muted = mute

  async def async_media_stop(self):
    """Send media_stop command to media player."""
    #_LOGGER.info('Stop playing  TODO...')
    await self.api.pause_url('pause')
    return 0

  async def async_play_media(self, media_type, media_id, **kwargs):
    """Send the play_media command to the media player."""
    _LOGGER.info('Start playing media..')
    _LOGGER.info(media_type)
    _LOGGER.info(media_id)
    if media_source.is_media_source_id(media_id):
        media_type = MEDIA_TYPE_URL
        play_item = await media_source.async_resolve_media(self.hass, media_id)
        media_id = play_item.url
    if media_type in (MEDIA_TYPE_URL, MEDIA_TYPE_MUSIC):
        media_id = async_process_play_media_url(self.hass, media_id)
    _LOGGER.info(media_id)
    await self.api.play_url(media_id)

# return 0
#  async def async_play_media(self, media_type, media_id, **kwargs):
#    """Send the play_media command to the media player."""
#    _LOGGER.info('Start playing media..')
#    _LOGGER.info(media_type)
#    _LOGGER.info(media_id)
#    await self.api.play_url(media_id)
#    return 0

  async def async_browse_media(self, media_content_type=None, media_content_id=None):
    """Implement the websocket media browsing helper."""
    return await media_source.async_browse_media(
        self.hass,
        media_content_id,
        content_filter=lambda item: item.media_content_type.startswith("audio/"),
    )

  @property
  def source(self):
    """Return the current source."""
    return self._current_source

  @property
  def source_list(self):
    """List of available input sources."""
    return sorted(MULTI_ROOM_SOURCE_TYPE)

  async def async_select_source(self, source):
    """Select input source."""
    if source not in MULTI_ROOM_SOURCE_TYPE:
      _LOGGER.error("Unsupported source")
      return

    await self.api.set_source(source)
    self._current_source = source

  async def async_turn_off(self):
      """Turn the media player off."""
      await self.api.set_state(0)

  async def async_turn_on(self):
      """Turn the media player on."""
      await self.api.set_state(1)

  @util.Throttle(MIN_TIME_BETWEEN_SCANS, MIN_TIME_BETWEEN_FORCED_SCANS)
  async def async_update(self):
    """Update the media player State."""
    _LOGGER.debug('Refreshing state...')
    "Update with power options"
    if self._power_options:
      "Get Power State"
      state = await self.api.get_state()
      _LOGGER.debug(state)
      if state and int(state) == 1:
        "If Power is ON, update other values"
        self._state = STATE_ON
        "Get Current Source"
        source = await self.api.get_source()
        if source is not None:
          "Source 0 is type on input"
          if source[0]:
            self._current_source = source[0]
          "Source 1 is input mode"
          if source[1]:
            self._mode = source[1]
          else:
            self._mode = ''
        else:
            self._mode = ''
        try:
          "Get Volume"
          volume = await self.api.get_volume()
          if volume[0]:
            self._volume = int(volume[0]) / self._max_volume
        except:
          _LOGGER.error("Failed to get volume")
        "Get Mute State"
        muted = await self.api.get_muted()
        if muted:
          self._muted = muted
        if self._mode == 'TuneIn':
          title = await self.api.get_radio_info()
          if title:
            self._media_title = str(title[0])
          image = await self.api.get_radio_image()
          if image:
            self._image_url = str(image[0])
        else:
          self._media_title = ''
          self._image_url = None
      else:
        self._state = STATE_OFF
        self._media_title = ''
        self._image_url = None
    else:
      "Update without power options"
      self._media_title = ''
      self._image_url = None
      "Get Current Source"
      source = await self.api.get_source()
      if source:
        self._current_source = source[0]
        self._state = STATE_PLAYING
      else:
        self._state = STATE_OFF
      "Get Volume"
      volume = await self.api.get_volume()
      if volume:
        self._volume = int(volume[0]) / self._max_volume
      "Get Mute State"
      muted = await self.api.get_muted()
      if muted:
        self._muted = muted

def setup_platform(hass, config, add_devices, discovery_info=None):
  """Set up the Samsung WAM platform."""
  ip = config.get(CONF_HOST)
  port = config.get(CONF_PORT)
  name = config.get(CONF_NAME)
  max_volume = int(config.get(CONF_MAX_VOLUME))
  power_options = config.get(CONF_POWER_OPTIONS)
  session = async_get_clientsession(hass)
  api = WAMApi(ip, port, session, hass)
  add_devices([WAMDevice(name, max_volume, power_options ,api)], True)

