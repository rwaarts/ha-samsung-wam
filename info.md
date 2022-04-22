# Samsung WAM for Speaker R1

This is a start for support of the WAM Speaker

Tested on a WAM1500/XN Speaker

# Configuration

Edit your configuration.yaml file and reboot HA to enable the component.

```
media_player:
  - platform: samsung_wam
    name: "Speaker 2"
    host: 192.168.62.228
    max_volume: 20
    power_options: false
    # mac: 5c:49:7d:82:29:91
```

## Debuging

```
logger:
  default: info
  logs:
    custom_components.samsung_wam: debug
```
