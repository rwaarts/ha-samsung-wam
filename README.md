# ha-samsung-wam
Home Assistant Samsung WAM - speaker R1

This is first try in getting the R1 speaker to work.


Config option
```
media_player:
  - platform: samsung_wam
    name: "Speaker 2"
    host: 192.168.62.228
    max_volume: 20
    power_options: false
    # mac: 5c:49:7d:82:29:91
```

### Debug

```
logger:
  default: info
  logs:
    custom_components.samsung_wam: info
```
