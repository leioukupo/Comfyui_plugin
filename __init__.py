import os
import json

#check if config file exists
if not os.path.isfile(os.path.join(os.path.realpath(__file__),"config.json")):
    #create config file
    config = {
        "autoUpdate": True,
        "branch": "dev",
        "openAI_API_Key": "sk-#########################################"
    }
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),"config.json"), "w") as f:
        json.dump(config, f, indent=4)
#load config file
with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),"config.json"), "r") as f:
    config = json.load(f)



from .aimusic.gen_lyrics import gen_lyrics
from .aimusic.gen_lyrics import load_openAI
from .aimusic.gen_lyrics import analyze_lyrics
from  .aimusic.WanVideoVACEStartToEndFrame import WanVideoVACEStartToEndFrame

NODE_CLASS_MAPPINGS = {
    "gen_lyrics": gen_lyrics,"load_openAI": load_openAI,"analyze_lyrics": analyze_lyrics,
    "WanVideoVACEStartToEndFrame": WanVideoVACEStartToEndFrame,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "gen_lyrics": "歌词生成","load_openAI": "load_openAI","analyze_lyrics": "分析歌词",
    "WanVideoVACEStartToEndFrame" : "创建首尾帧批次和蒙版"
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']