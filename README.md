# cherenkov
FTL compatible server (https://github.com/mixer/ftl-sdk)

# How to use 

Start the Server

```
./cherenkov.py 

```

Start streaming using OBS-studio for example* 

Start the media player
```
./cherenkov_media.py
```


* OBS-studio doesn't support custom FTL server, but you can add it by
editing `$HOME/.config/obs-studio/plugin_config/rtmp-services/services.json`
Insert a new server in the server list for FTL
```
    "name": "Mixer.com - FTL",
            "common": true,
            "servers": [
                {
                    "name": "HOME: Localhost",
                    "url": "localhost"  
                },

```