import json
import os
from typing import Dict, Any, List, Optional
import comfy.samplers
import comfy.sd
import comfy.utils
import re
import importlib
# 名词定义
# “悲伤的”、“情绪的”、“愤怒的”、“快乐的”、“令人振奋的”、“强烈的”、“浪漫的”、“忧郁的”
EMOTIONS = [
    "sad", "emotional", "angry", "happy", 
    "uplifting", "intense", "romantic", "melancholic"
]

SINGER_GENDERS = ["male", "female"]

# “自动”、“中国传统”、“金属”、“雷鬼”、“中国戏曲”、“流行”、“电子”、“嘻哈”、“摇滚”、
# “爵士”、“蓝调”、“古典”、“说唱”、“乡村”、“经典摇滚”、“硬摇滚”、“民谣”、“灵魂乐”、
# “舞曲电子”、“乡村摇滚”、“舞曲、舞曲流行、浩室、流行”、“雷鬼”、“实验”、“舞曲、
# 流行”、“舞曲、深浩室、电子”、“韩国流行音乐”、“实验流行”、“流行朋克”、“摇滚乐”、
# “节奏布鲁斯”、“多样”、“流行摇滚”
GENRES = [
    'Auto', 'Chinese Tradition', 'Metal', 'Reggae', 'Chinese Opera',
    "pop", "electronic", "hip hop", "rock", "jazz", "blues", "classical",
    "rap", "country", "classic rock", "hard rock", "folk", "soul",
    "dance, electronic", "rockabilly", "dance, dancepop, house, pop",
    "reggae", "experimental", "dance, pop", "dance, deephouse, electronic",
    "k-pop", "experimental pop", "pop punk", "rock and roll", "R&B",
    "varies", "pop rock",
]

# “合成器与钢琴”，“钢琴与鼓”，“钢琴与合成器”，
# “合成器与鼓”，“钢琴与弦乐”，“吉他与鼓”，
# “吉他与钢琴”，“钢琴与低音提琴”，“钢琴与吉他”，
# “原声吉他与钢琴”，“原声吉他与合成器”，
# “合成器与吉他”，“钢琴与萨克斯风”，“萨克斯风与钢琴”，
# “钢琴与小提琴”，“电吉他与鼓”，“原声吉他与鼓”，
# “合成器”，“吉他与小提琴”，“吉他与口琴”，
# “合成器与原声吉他”，“节拍”，“钢琴”，
# “原声吉他与小提琴”，“铜管与钢琴”，“贝斯与鼓”，
# “小提琴”，“原声吉他与口琴”，“钢琴与大提琴”，
# “萨克斯风与小号”，“吉他与班卓琴”，“吉他与合成器”，
# “萨克斯风”，“小提琴与钢琴”，“合成器与贝斯”，
# “合成器与电吉他”，“电吉他与钢琴”，
# “节拍与钢琴”，“合成器与吉他”
INSTRUMENTATIONS = [
    "synthesizer and piano", "piano and drums", "piano and synthesizer",
    "synthesizer and drums", "piano and strings", "guitar and drums",
    "guitar and piano", "piano and double bass", "piano and guitar",
    "acoustic guitar and piano", "acoustic guitar and synthesizer",
    "synthesizer and guitar", "piano and saxophone", "saxophone and piano",
    "piano and violin", "electric guitar and drums", "acoustic guitar and drums",
    "synthesizer", "guitar and fiddle", "guitar and harmonica",
    "synthesizer and acoustic guitar", "beats", "piano",
    "acoustic guitar and fiddle", "brass and piano", "bass and drums",
    "violin", "acoustic guitar and harmonica", "piano and cello",
    "saxophone and trumpet", "guitar and banjo", "guitar and synthesizer",
    "saxophone", "violin and piano", "synthesizer and bass",
    "synthesizer and electric guitar", "electric guitar and piano",
    "beats and piano", "synthesizer and guitar"
]

# 音色：“黑暗的”、“明亮的”、“温暖的”、“岩石”、“变化的”、“柔和的”、“嗓音”
TIMBRES = ["dark", "bright", "warm", "rock", "varies", "soft", "vocal"]

AUTO_PROMPT_TYPES = ['Pop', 'R&B', 'Dance', 'Jazz', 'Folk', 'Rock', 
                    'Chinese Style', 'Chinese Tradition', 'Metal', 
                    'Reggae', 'Chinese Opera', 'Auto']


# 在常量定义部分添加音乐段落时长配置
MUSIC_SECTION_TEMPLATES = {
    # 纯器乐段落
    "intro-short": {
        "description": "前奏超短版(0-10秒)",
        "duration": "5-10秒",
        "duration_avg": 7,  # (5+10)/2 ≈ 7.5 取整
        "lyric_required": False
    },
    "intro-medium": {
        "description": "前奏中等版(10-20秒)",
        "duration": "15-20秒",
        "duration_avg": 17,  # (15+20)/2 = 17.5 取整
        "lyric_required": False
    },
    "intro-long": {
        "description": "前奏完整版(20-30秒)",
        "duration": "20-30秒",
        "duration_avg": 25,  # (20+30)/2 = 25
        "lyric_required": False
    },
    "outro-short": {
        "description": "尾奏超短版(0-10秒)", 
        "duration": "5-10秒",
        "duration_avg": 7,
        "lyric_required": False
    },
    "outro-medium": {
        "description": "尾奏中等版(10-20秒)",
        "duration": "15-20秒",
        "duration_avg": 17,
        "lyric_required": False
    },
    "outro-long": {
        "description": "尾奏完整版(20-30秒)",
        "duration": "20-30秒",
        "duration_avg": 25,
        "lyric_required": False
    },
    "inst-short": {
        "description": "间奏短版(5-10秒)",
        "duration": "5-10秒",
        "duration_avg": 7,
        "lyric_required": False
    },
    "inst-medium": {
        "description": "间奏中等版(10-20秒)",
        "duration": "15-20秒",
        "duration_avg": 17,
        "lyric_required": False
    },
    "inst-long": {
        "description": "间奏完整版(20-30秒)",
        "duration": "20-30秒",
        "duration_avg": 25,
        "lyric_required": False
    },
    "silence": {
        "description": "空白停顿(1-3秒)",
        "duration": "1-3秒",
        "duration_avg": 2,  # 取中间值
        "lyric_required": False
    },
    
    # 人声段落
    "verse": {
        "description": "主歌段落(20-30秒)",
        "duration": "20-30秒",
        "duration_avg": 25,
        "lyric_required": True,
        "lines": "4-8行"
    },
    "chorus": {
        "description": "副歌(高潮段落)", 
        "duration": "20-30秒",
        "duration_avg": 25,
        "lyric_required": True,
        "lines": "4-8行"
    },
    "bridge": {
        "description": "过渡桥段",
        "duration": "15-25秒",
        "duration_avg": 20,  # (15+25)/2 = 20
        "lyric_required": True,
        "lines": "2-4行"
    }
}


# - '[verse]'
# - '[chorus]'
# - '[bridge]'
# - '[intro-short]'
# - '[intro-medium]'
# - '[intro-long]'
# - '[outro-short]'
# - '[outro-medium]'
# - '[outro-long]'
# - '[inst-short]'
# - '[inst-medium]'
# - '[inst-long]'
# - '[silence]'

# 典型结构模板
# 音乐结构模板库 (36种)
STRUCTURE_TEMPLATES = {
    # 基础流行结构 (5种)
    "pop_basic": {
        "name": "流行基础结构",
        "sections": ["intro-medium", "verse", "chorus", "verse", "chorus", "outro-medium"]
    },
    "pop_with_bridge": {
        "name": "流行带桥段结构", 
        "sections": ["intro-medium", "verse", "chorus", "verse", "chorus", "bridge", "chorus", "outro-medium"]
    },
    "pop_with_prechorus": {
        "name": "流行带预副歌结构",
        "sections": ["intro-short", "verse", "verse", "chorus", "verse", "verse", "chorus", "outro-short"]
    },
    "pop_doublechorus": {
        "name": "流行双副歌结构",
        "sections": ["intro-short", "verse", "chorus", "chorus", "verse", "chorus", "chorus", "outro-short"]
    },
    "pop_postchorus": {
        "name": "流行带后副歌结构",
        "sections": ["intro-medium", "verse", "verse", "chorus", "inst-short", "verse", "verse", "chorus", "inst-short", "outro-medium"]
    },
    
    # 摇滚/金属结构 (8种)
    "rock_classic": {
        "name": "经典摇滚结构",
        "sections": ["intro-long", "verse", "chorus", "verse", "chorus", "inst-long", "chorus", "outro-long"]
    },
    "metal_progressive": {
        "name": "前卫金属结构",
        "sections": ["intro-long", "verse", "bridge", "chorus", "inst-long", "verse", "bridge", "chorus", "inst-long", "outro-long"]
    },
    "punk": {
        "name": "朋克结构",
        "sections": ["intro-short", "verse", "chorus", "verse", "chorus", "bridge", "chorus", "outro-short"]
    },
    "hardrock": {
        "name": "硬摇滚结构",
        "sections": ["intro-long", "verse", "chorus", "verse", "chorus", "inst-long", "inst-long", "chorus", "outro-long"]
    },
    "rock_ballad": {
        "name": "摇滚抒情曲结构",
        "sections": ["intro-long", "verse", "verse", "chorus", "inst-long", "verse", "chorus", "outro-long"]
    },
    "metalcore": {
        "name": "金属核结构",
        "sections": ["intro-short", "verse", "chorus", "verse", "chorus", "inst-short", "chorus", "outro-short"]
    },
    "blues_rock": {
        "name": "蓝调摇滚结构",
        "sections": ["intro-medium", "verse", "verse", "chorus", "inst-medium", "verse", "chorus", "outro-medium"]
    },
    "rock_instrumental": {
        "name": "摇滚器乐曲结构",
        "sections": ["intro-long", "inst-long", "inst-medium", "inst-long", "inst-medium", "inst-long", "inst-long", "outro-long"]
    },
    
    # 电子音乐结构 (7种)
    "edm_builddrop": {
        "name": "EDM构建-高潮结构",
        "sections": ["intro-long", "inst-medium", "inst-short", "inst-medium", "inst-medium", "inst-short", "outro-medium"]
    },
    "house": {
        "name": "浩室结构",
        "sections": ["intro-long", "inst-long", "inst-medium", "inst-long", "inst-medium", "inst-short", "outro-long"]
    },
    "trance": {
        "name": "迷幻结构",
        "sections": ["intro-long", "inst-long", "inst-medium", "inst-short", "inst-medium", "inst-medium", "inst-short", "outro-long"]
    },
    "dubstep": {
        "name": "回响贝斯结构",
        "sections": ["intro-medium", "verse", "inst-short", "inst-medium", "verse", "inst-short", "outro-short"]
    },
    "techno": {
        "name": "科技结构",
        "sections": ["intro-long", "inst-long", "inst-medium", "inst-long", "inst-short", "inst-long", "outro-long"]
    },
    "drum_bass": {
        "name": "鼓打贝斯结构",
        "sections": ["intro-medium", "inst-short", "verse", "inst-short", "inst-medium", "inst-short", "outro-medium"]
    },
    "ambient": {
        "name": "氛围结构",
        "sections": ["intro-long", "inst-long", "inst-medium", "inst-short", "inst-medium", "outro-long"]
    },
    
    # 嘻哈/说唱结构 (5种)
    "hiphop_classic": {
        "name": "经典嘻哈结构",
        "sections": ["intro-short", "verse", "chorus", "verse", "chorus", "bridge", "verse", "chorus", "outro-short"]
    },
    "trap": {
        "name": "陷阱结构",
        "sections": ["intro-short", "verse", "chorus", "verse", "chorus", "inst-short", "chorus", "outro-short"]
    },
    "rap_storytelling": {
        "name": "叙事说唱结构",
        "sections": ["intro-medium", "verse", "chorus", "verse", "chorus", "verse", "chorus", "outro-medium"]
    },
    "hiphop_jazzy": {
        "name": "爵士嘻哈结构",
        "sections": ["intro-medium", "verse", "chorus", "verse", "chorus", "inst-medium", "chorus", "outro-medium"]
    },
    "rap_battle": {
        "name": "对战说唱结构",
        "sections": ["intro-short", "verse", "verse", "verse", "verse", "outro-short"]
    },
    
    # 中国传统/民族结构 (6种)
    "chinese_folk": {
        "name": "中国民谣结构",
        "sections": ["intro-long", "verse", "inst-medium", "verse", "inst-medium", "outro-long"]
    },
    "chinese_opera": {
        "name": "戏曲结构",
        "sections": ["intro-long", "verse", "inst-short", "verse", "inst-medium", "inst-short", "verse", "outro-long"]
    },
    "guqin": {
        "name": "古琴曲结构",
        "sections": ["intro-long", "inst-long", "inst-medium", "inst-long", "inst-medium", "outro-long"]
    },
    "ethnic_fusion": {
        "name": "民族融合结构",
        "sections": ["intro-long", "verse", "chorus", "verse", "chorus", "inst-long", "outro-long"]
    },
    "chinese_pop": {
        "name": "中国流行结构",
        "sections": ["intro-medium", "verse", "verse", "chorus", "inst-medium", "verse", "verse", "chorus", "outro-medium"]
    },
    "mongolian_throat": {
        "name": "蒙古呼麦结构",
        "sections": ["intro-long", "verse", "inst-long", "inst-short", "verse", "inst-short", "outro-long"]
    },
    
    # 爵士/蓝调结构 (5种)
    "jazz_standard": {
        "name": "爵士标准结构",
        "sections": ["intro-medium", "inst-medium", "inst-long", "inst-medium", "inst-medium", "outro-medium"]
    },
    "blues_12bar": {
        "name": "12小节蓝调结构",
        "sections": ["intro-short", "verse", "verse", "verse", "inst-medium", "verse", "outro-short"]
    },
    "jazz_fusion": {
        "name": "爵士融合结构",
        "sections": ["intro-long", "inst-medium", "inst-long", "inst-medium", "inst-short", "inst-medium", "outro-long"]
    },
    "bebop": {
        "name": "比博普结构",
        "sections": ["intro-short", "inst-short", "inst-medium", "inst-long", "inst-medium", "inst-short", "outro-short"]
    },
    "jazz_ballad": {
        "name": "爵士抒情曲结构",
        "sections": ["intro-long", "inst-long", "inst-medium", "inst-long", "outro-long"]
    }
}

# 特殊段落说明
SECTION_DEFINITIONS = {
    "skank": "雷鬼特有的反拍节奏段落",
    "guitar-solo": "吉他独奏部分",
    "post-chorus": "副歌后的记忆点段落",
    "drop": "电子舞曲的高潮部分",
    "head": "爵士乐主题段落",
    "ad-lib": "即兴演唱部分",
    "12bar": "12小节蓝调进行",
    "build-up": "电子乐中的情绪构建段落",
    "breakdown": "电子乐中的分解段落",
    "call-response": "非洲音乐中的呼应段落",
    "copla": "弗拉门戈中的歌唱段落",
    "falseta": "弗拉门戈吉他独奏段落"
}
openAI_gpt_models = ['gpt-4o', 'gpt-4.1',"deepseek-r1-0528"]
def get_api_key():
    # Helper function to get the API key from the file
    try:
        # open config file
        configPath = os.path.join("./", "config.json")
        with open(configPath, 'r') as f:  # Open the file and read the API key
            config = json.load(f)
        api_key = config["openAI_API_Key"]
    except:
        print("Error: OpenAI API key file not found OpenAI features wont work for you")
        return ""
    return api_key  # Return the API key
def get_openAI_models():
    global openAI_models
    if (openAI_models != None):
        return openAI_models

    install_openai()
    from openai import OpenAI
    # Get the API key from the file
    api_key = get_api_key()
    client = OpenAI(
                # This is the default and can be omitted
                api_key=api_key,
            )

    try:
        models = client.models.list()  # Get the list of models
        print("all models:",models)
    except:
        print("Error: OpenAI API key is invalid OpenAI features wont work for you")
        return []

    openAI_models = []  # Create a list for the chat models
    for model in getattr(models, "data"):  # Loop through the models
        openAI_models.append(getattr(model, "id"))  # Add the model to the list

    return openAI_gpt_models  # Return the list of chat models
def parse_duration_to_seconds(duration_str: str) -> int:
    """将中文时长字符串转换为秒数"""
    try:
        # 处理"X分Y秒"格式
        if "分" in duration_str and "秒" in duration_str:
            minutes = int(re.search(r"(\d+)分", duration_str).group(1))
            seconds = int(re.search(r"(\d+)秒", duration_str).group(1))
            return minutes * 60 + seconds
        
        # 处理只有分钟的格式
        if "分" in duration_str:
            return int(duration_str.replace("分", "")) * 60
        
        # 处理纯秒数格式
        if "秒" in duration_str:
            return int(duration_str.replace("秒", ""))
        
        # 默认处理纯数字
        return int(duration_str)
    except Exception as e:
        raise ValueError(f"无效的时长格式: '{duration_str}'") from e
def calculate_section_timings(sections: List[str], total_seconds: int) -> Dict[str, int]:
    """计算每个段落的时长分配"""
    # 1. 验证所有段落是否定义
    for section in sections:
        if section not in MUSIC_SECTION_TEMPLATES:
            raise ValueError(f"未定义的段落类型: {section}")
    
    # 2. 计算总基准时长
    total_baseline = sum(
        MUSIC_SECTION_TEMPLATES[sec]["duration_avg"] 
        for sec in sections
    )
    
    # 3. 检查是否包含bridge段落
    has_bridge = "bridge" in sections
    
    # 4. 分配时长
    section_timings = {}
    remaining_seconds = total_seconds
    
    # 先分配verse和chorus段落
    for section in [sec for sec in sections if sec in ["verse", "chorus"]]:
        allocated = int(MUSIC_SECTION_TEMPLATES[section]["duration_avg"] * total_seconds / total_baseline)
        allocated = max(15, min(45, allocated))  # 限制15-45秒
        section_timings[section] = allocated
        remaining_seconds -= allocated
    
    # 如果有bridge段落，分配时长
    if has_bridge:
        bridge_seconds = int(MUSIC_SECTION_TEMPLATES["bridge"]["duration_avg"] * total_seconds / total_baseline)
        bridge_seconds = max(10, min(30, bridge_seconds))  # 限制10-30秒
        section_timings["bridge"] = bridge_seconds
        remaining_seconds -= bridge_seconds
    
    # 分配器乐段落
    instrumental_sections = [sec for sec in sections if sec not in ["verse", "chorus", "bridge"]]
    for section in instrumental_sections:
        allocated = int(MUSIC_SECTION_TEMPLATES[section]["duration_avg"] * total_seconds / total_baseline)
        allocated = max(5, min(30, allocated))  # 限制5-30秒
        section_timings[section] = allocated
        remaining_seconds -= allocated
    
    # 处理剩余时间（加到最后一个段落）
    if remaining_seconds > 0:
        last_section = sections[-1]
        section_timings[last_section] += remaining_seconds
    
    return section_timings
def calc_lines_from_seconds(seconds: int) -> str:
    """根据秒数计算建议行数"""
    min_lines = max(2, seconds // 5)  # 每行最多5秒
    max_lines = max(4, seconds // 3)  # 每行最少3秒
    return f"{min_lines}-{max_lines}行"


def generate_lyrics_with_duration(
        lyric_prompt: str,
        template: Dict[str, Any],
        song_length: str
) -> Optional[str]:
    """生成带时长控制的歌词"""
    try:
        # 解析总时长
        total_seconds = parse_duration_to_seconds(song_length)

        # 计算段落时长
        section_timings = calculate_section_timings(template["sections"], total_seconds)

        # 构建提示词
        prompt_lines = [
            f"请根据以下要求生成一首中文歌曲的完整歌词：\n"
            f"主题：{lyric_prompt}",
            f"""歌曲结构：
            {", ".join([f"[{section}]" for section in template["sections"]])}
            具体要求：
            1. 严格按照给定的结构标签分段
            2. 器乐段落([intro-*]/[outro-*])不需要填歌词
            3. 人声段落([verse]/[chorus]/[bridge])必须包含歌词
            4. 主歌([verse])每段4-8行
            5. 副歌([chorus])要突出高潮部分
            6. 桥段([bridge])2-4行
            7. 整体要有押韵和节奏感
            8. 不要包含歌曲标题
            9. 不要包含韵脚分析等额外说明
            返回格式示例：
            [intro-medium]
            [verse]
            第一行歌词
            第二行歌词
            ...
            [chorus]
            副歌第一行
            副歌第二行
            ...""",
            f"总时长：{song_length} ({total_seconds}秒)",
            "段落时长分配："
        ]

        # 添加各段落信息
        for section in template["sections"]:
            desc = MUSIC_SECTION_TEMPLATES[section]["description"]
            prompt_lines.append(f"- [{section}]: {section_timings[section]}秒 ({desc})")

        # 添加歌词行数要求
        prompt_lines.append("\n歌词要求：")
        prompt_lines.append(f"1. 主歌([verse]): 每段{calc_lines_from_seconds(section_timings['verse'])}行")
        prompt_lines.append(f"2. 副歌([chorus]): 每段{calc_lines_from_seconds(section_timings['chorus'])}行")

        # 只有模板包含bridge时才添加bridge要求
        if "bridge" in template["sections"]:
            prompt_lines.append(f"3. 桥段([bridge]): {calc_lines_from_seconds(section_timings['bridge'])}行")
        prompt_lines.append("4. 器乐段落不需要歌词")
        prompt_lines.append("5. 注意押韵和节奏")

        prompt = "\n".join(prompt_lines)
        return prompt
    except Exception as e:
        print("error")
        return None
def install_openai():
    # Helper function to install the OpenAI module if not already installed
    try:
        importlib.import_module('openai')
    except ImportError:
        import pip
        pip.main(['install', 'openai'])
def get_gpt_models():
    global openAI_gpt_models
    if (openAI_gpt_models is not None):
        return openAI_gpt_models
    models = get_openAI_models()
    openAI_gpt_models = ["gpt-3.5-turbo"]  # Create a list for the chat models
    for model in models:  # Loop through the models
        openAI_gpt_models.append(model)
    return openAI_gpt_models  # Return the list of chat models
def clean_generated_lyrics(raw_lyrics: str) -> str:
    """
    Format raw lyrics into a single-line string with strict section formatting:
    - Sections separated by ' ; '
    - Each line in vocal sections ends with a period
    - No spaces around periods
    - Instrumental sections without content

    Args:
        raw_lyrics: Raw lyrics text with section markers

    Returns:
        A single-line formatted string
    """
    sections = []
    current_section = None
    current_lines = []

    for line in raw_lyrics.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Detect section headers like [verse]
        section_match = re.match(r'^\[([a-z\-]+)\]$', line)
        if section_match:
            # Save previous section if exists
            if current_section is not None:
                if current_lines:
                    # 处理每行结尾加句号，且无空格
                    formatted_lines = [l.rstrip('.') + '.' for l in current_lines]
                    section_text = ' '.join(formatted_lines)
                else:
                    section_text = ''
                sections.append(f"[{current_section}]{section_text}")
            current_section = section_match.group(1)
            current_lines = []
        elif current_section is not None:
            # Clean lyric line and add to current section
            cleaned_line = line.replace(' ', '.').replace('，', '.').replace('。', '.').strip('. ')
            if cleaned_line:
                current_lines.append(cleaned_line)
    # 处理最后一个段落
    if current_section is not None:
        if current_lines:
            formatted_lines = [l.rstrip('.') + '.' for l in current_lines]
            section_text = ' '.join(formatted_lines)
        else:
            section_text = ''
        sections.append(f"[{current_section}]{section_text}")
    # 用 ' ; ' 连接所有段落，返回单行字符串
    return ' ; '.join(sections)



class gen_lyrics:
    @classmethod
    def INPUT_TYPES(s):# 固定格式，输入参数种类
        # 返回一个包含所需输入类型的字典
        return {
            "required": {
                "client": ("CLIENT",),
                "model": (get_gpt_models(), {"default": "gpt-3.5-turbo"}),
                "Lyric_theme": ("STRING", {
                    "default": "歌词主题",
                    "multiline": True}),
                "Lyric_structure": (["None"] + ["流行基础结构","流行带桥段结构", "流行带预副歌结构", "流行双副歌结构", "流行带后副歌结构", 
                            "中国民谣结构","戏曲结构","古琴曲结构","民族融合结构","中国流行结构","蒙古呼麦结构",
                            "经典摇滚结构", "前卫金属结构", "朋克结构", "硬摇滚结构", "摇滚抒情曲结构", "金属核结构", 
                            "蓝调摇滚结构","摇滚器乐曲结构",
                            "EDM构建-高潮结构","浩室结构","回响贝斯结构","科技结构","鼓打贝斯结构","氛围结构",
                            "经典嘻哈结构","陷阱结构","叙事说唱结构","爵士嘻哈结构","对战说唱结构",
                            "爵士标准结构","12小节蓝调结构","爵士融合结构","比博普结构","爵士抒情曲结构","12小节蓝调结构"],),
                "time_m": ("INT", {
                    "default": 1.0,
                    "min": 0,
                    "max": 2,
                    "step": 1,
                    "round": 0.001,  # 精度
                    "display": "slider"}),  # 滑动调整  
                "time_s": ("INT", {
                    "default": 30,
                    "min": 0,
                    "max": 59,
                    "step": 1,
                    "round": 0.001,  # 精度
                    "display": "slider"}),  # 滑动调整           
            },
        }

    OUTPUT_NODE = True
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("lyric",)  # 定义该节点返回的是歌词 字符串
    FUNCTION = "gen_lyrics"  # 定义节点的函数名字
    CATEGORY = "aimusic/gen-lyrics"  # 定义节点类别
    def gen_lyrics(self, client,model, Lyric_theme, Lyric_structure, time_m, time_s):
        song_length = f"{time_m}分{time_s}秒"
        # 中文结构名到英文键的映射
        structure_name_map = {
            "流行基础结构": "pop_basic",
            "流行带桥段结构": "pop_with_bridge",
            "流行带预副歌结构": "pop_with_prechorus",
            "流行双副歌结构": "pop_doublechorus",
            "流行带后副歌结构": "pop_postchorus",
            "中国民谣结构": "chinese_folk",
            "戏曲结构": "chinese_opera",
            "古琴曲结构": "guqin",
            "民族融合结构": "ethnic_fusion",
            "中国流行结构": "chinese_pop",
            "蒙古呼麦结构": "mongolian_throat",
            "经典摇滚结构": "rock_classic",
            "前卫金属结构": "metal_progressive",
            "朋克结构": "punk",
            "硬摇滚结构": "hardrock",
            "摇滚抒情曲结构": "rock_ballad",
            "金属核结构": "metalcore",
            "蓝调摇滚结构": "blues_rock",
            "摇滚器乐曲结构": "rock_instrumental",
            "EDM构建-高潮结构": "edm_builddrop",
            "浩室结构": "house",
            "回响贝斯结构": "dubstep",
            "科技结构": "techno",
            "鼓打贝斯结构": "drum_bass",
            "氛围结构": "ambient",
            "经典嘻哈结构": "hiphop_classic",
            "陷阱结构": "trap",
            "叙事说唱结构": "rap_storytelling",
            "爵士嘻哈结构": "hiphop_jazzy",
            "对战说唱结构": "rap_battle",
            "爵士标准结构": "jazz_standard",
            "12小节蓝调结构": "blues_12bar",
            "爵士融合结构": "jazz_fusion",
            "比博普结构": "bebop",
            "爵士抒情曲结构": "jazz_ballad",
        }
        key = structure_name_map.get(Lyric_structure)
        if key is None:
            raise ValueError(f"未知的歌词结构: {Lyric_structure}")
        template = STRUCTURE_TEMPLATES[key]
        """生成带时长控制的歌词"""
        try:
            # 解析总时长
            total_seconds = parse_duration_to_seconds(song_length)

            # 计算段落时长
            section_timings = calculate_section_timings(template["sections"], total_seconds)

            # 构建提示词
            prompt_lines = [
                f"请根据以下要求生成一首中文歌曲的完整歌词：\n"
                f"主题：{Lyric_theme}",
                f"""歌曲结构：
                    {", ".join([f"[{section}]" for section in template["sections"]])}
                    具体要求：
                    1. 严格按照给定的结构标签分段
                    2. 器乐段落([intro-*]/[outro-*])不需要填歌词
                    3. 人声段落([verse]/[chorus]/[bridge])必须包含歌词
                    4. 主歌([verse])每段4-8行
                    5. 副歌([chorus])要突出高潮部分
                    6. 桥段([bridge])2-4行
                    7. 整体要有押韵和节奏感
                    8. 不要包含歌曲标题
                    9. 不要包含韵脚分析等额外说明
                    返回格式示例：
                    [intro-medium]
                    [verse]
                    第一行歌词
                    第二行歌词
                    ...
                    [chorus]
                    副歌第一行
                    副歌第二行
                    ...""",
                f"总时长：{song_length} ({total_seconds}秒)",
                "段落时长分配："
            ]

            # 添加各段落信息
            for section in template["sections"]:
                desc = MUSIC_SECTION_TEMPLATES[section]["description"]
                prompt_lines.append(f"- [{section}]: {section_timings[section]}秒 ({desc})")
            # 添加歌词行数要求
            prompt_lines.append("\n歌词要求：")
            prompt_lines.append(f"1. 主歌([verse]): 每段{calc_lines_from_seconds(section_timings['verse'])}行")
            prompt_lines.append(f"2. 副歌([chorus]): 每段{calc_lines_from_seconds(section_timings['chorus'])}行")
            # 只有模板包含bridge时才添加bridge要求
            if "bridge" in template["sections"]:
                prompt_lines.append(f"3. 桥段([bridge]): {calc_lines_from_seconds(section_timings['bridge'])}行")

            prompt_lines.append("4. 器乐段落不需要歌词")
            prompt_lines.append("5. 注意押韵和节奏")
            prompt = "\n".join(prompt_lines)
            client = client["client"]
            try:
                completion = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}]
                )
            except:  # sometimes it fails first time to connect to server
                completion = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}]
                )
            # Get the answer from the chat completion
            lyrics = completion.choices[0].message.content
            if lyrics:
                lyrics = clean_generated_lyrics(lyrics)
                return lyrics
        except Exception as e:
            print(f"歌词生成失败: {str(e)}")
            return None

class load_openAI:
    """
    this node will load  openAI model
    """
    # Define the input types for the node
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_url": ("STRING", {"multiline": False, "default": "https://openai-cf.realnow.workers.dev/v1"}),
                "api_key": ("STRING", {"multiline": False, "default": ""}),
            }
        }

    OUTPUT_NODE = True
    RETURN_TYPES = ("CLIENT",)  # Define the return type of the node
    FUNCTION = "fun"  # Define the function name for the node
    CATEGORY = "aimusic/openai"  # Define the category for the node

    def fun(self,base_url,api_key):
        install_openai()  # Install the OpenAI module if not already installed
        from openai import OpenAI
        # Get the API key from the file
        # api_key = api_key#get_api_key()
        client = OpenAI(
                    # This is the default and can be omitted
                    api_key=api_key,
                    base_url=base_url
                )
        
        return (
            {
                "client": client,  # Return openAI model
            },
        )

class analyze_lyrics:
    """
    分析歌词风格情绪等
    """
    # Define the input types for the node
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "client": ("CLIENT",),
                "model": (get_gpt_models(), {"default": "gpt-3.5-turbo"}),
                "lyrics": ("STRING", {"multiline": True, "default": "你好"}),
            }
        }
    # Define the return type of the node
    OUTPUT_NODE = True
    RETURN_TYPES = ("STRING",)
    FUNCTION = "fun"  # Define the function name for the node
    # Define the category for the node
    CATEGORY = "aimusic/openai"
    def fun(self,client, model, lyrics):
        prompt = f"""请严格按以下JSON格式分析歌词特征：
        {lyrics}
        返回格式必须为：
        {{
            "emotion": "从{sorted(EMOTIONS)}中选择",
            "genre": "从{sorted(GENRES)}中选择1-2种",
            "instrumentation": "从{sorted(INSTRUMENTATIONS)}中选择",
            "timbre": "从{sorted(TIMBRES)}中选择",
            "gender_suggestion": "从{sorted(SINGER_GENDERS)}中选择"
        }}
        注意：
        1. 必须返回合法JSON
        2. 所有值必须来自给定选项
        3. 不要包含任何额外文字"""
        # Create a chat completion using the OpenAI module
        client = client["client"]

        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )
        except:  # sometimes it fails first time to connect to server
            completion = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )
        # Get the answer from the chat completion
        content = completion.choices[0].message.content
        # 预处理API响应
        cleaned_result = content.strip()

        # 处理可能的代码块标记
        if cleaned_result.startswith("```json"):
            cleaned_result = cleaned_result[7:].strip()
        if cleaned_result.endswith("```"):
            cleaned_result = cleaned_result[:-3].strip()

        # 解析JSON
        analysis = json.loads(cleaned_result)

        # 验证结果
        required_keys = ["emotion", "genre", "instrumentation",
                         "timbre", "gender_suggestion"]
        if not all(key in analysis for key in required_keys):
            print(f"缺少必要字段，应有: {required_keys}")

        # 验证字段值有效性
        if analysis["emotion"] not in EMOTIONS:
            print(f"无效情绪: {analysis['emotion']}，应为: {EMOTIONS}")

        if not any(g in analysis["genre"] for g in GENRES):
            print(f"无效类型: {analysis['genre']}，应为: {GENRES}")

        if analysis["instrumentation"] not in INSTRUMENTATIONS:
            print(f"无效乐器组合: {analysis['instrumentation']}，应为: {INSTRUMENTATIONS}")

        if analysis["timbre"] not in TIMBRES:
            print(f"无效音色: {analysis['timbre']}，应为: {TIMBRES}")

        if analysis["gender_suggestion"] not in SINGER_GENDERS:
            print(f"无效性别建议: {analysis['gender_suggestion']}，应为: {SINGER_GENDERS}")

        # 返回验证通过的结果
        return ", ".join([analysis["emotion"], analysis["genre"], analysis["instrumentation"], analysis["timbre"],
                   analysis["gender_suggestion"]])



