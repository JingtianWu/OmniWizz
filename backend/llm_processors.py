import torch
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
import re
from diffrhythm_module import extract_prompt_and_lyrics, normalize_lrc
from config import TEST_MODE


class BaseLLMProcessor:
    def __init__(
        self,
        image_path: str,
        language: str = "en",
        max_new_tokens: int = 512,
        temperature: float = 1.0,
        top_p: float = 0.9,
        do_sample: bool = True
    ):
        self.image_path = image_path
        self.language = language
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.do_sample = do_sample

        # Load model and processor
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            "Qwen/Qwen2.5-VL-3B-Instruct",
            torch_dtype=torch.bfloat16,
            attn_implementation="eager",
            device_map="auto"
        )
        self.processor = AutoProcessor.from_pretrained("Qwen/Qwen2.5-VL-3B-Instruct")
        self.device = torch.device(
            "mps" if torch.backends.mps.is_available() else
            "cuda" if torch.cuda.is_available() else
            "cpu"
        )
        self.model.to(self.device)

    def generate(self) -> str:
        if TEST_MODE:
            return self._mock_generate()
        return self._real_generate()

    def _real_generate(self) -> str:
        messages = self._build_messages()
        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(
            text=[text], images=image_inputs, videos=video_inputs,
            padding=True, return_tensors="pt"
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        gen_ids = self.model.generate(
            **inputs,
            max_new_tokens=self.max_new_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
            do_sample=self.do_sample
        )

        decoded = self.processor.batch_decode(
            [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs["input_ids"], gen_ids)],
            skip_special_tokens=True
        )[0]
        return decoded

    def process(self):
        raw = self.generate()
        print("\n=== RAW MODEL OUTPUT ===\n", raw, "\n=== END ===")
        return self._postprocess(raw)

    def _build_messages(self):
        raise NotImplementedError("Subclasses must implement _build_messages().")

    def _postprocess(self, output: str):
        raise NotImplementedError("Subclasses must implement _postprocess().")


class ImageToLyricsProcessor(BaseLLMProcessor):
    def __init__(self, image_path: str, language: str = "en"):
        super().__init__(
            image_path,
            language,
            max_new_tokens=512,
            temperature=1.2,
            top_p=0.95,
            do_sample=True
        )

    def _mock_generate(self):
        return (
            "**Music Prompt:** Calm piano, soft ambient pads, morning breeze, light percussion\n\n"
            "**Lyrics:**\n"
            "[00:10.00]Waves gently touch the shore\n"
            "[00:14.00]Sunrise colors fill the air\n"
            "[00:18.00]Mountains watching from afar\n"
            "[00:22.00]Clouds drift like cotton dreams\n"
            "[00:26.00]Heartbeats match the morning breeze\n"
            "[00:30.00]Footprints mark the golden sand\n"
            "[00:34.00]Melody flows from ocean winds\n"
            "[00:38.00]Distant peaks hum harmonies\n"
            "[00:42.00]Seagulls glide above the waves\n"
            "[00:46.00]Whispers of the coming day\n"
            "[00:50.00]Warmth wraps around my soul\n"
            "[00:54.00]Hope awakens with the light"
        )

    def _build_messages(self):
        if self.language == "en":
            prompt = (
                "Here is an example of how to describe an image musically and generate lyrics. "
                "The lyrics should be timestamped in the format [MM:SS.xx], and the timestamps should be chosen "
                "to match the pacing and emotion of the scene.\n\n"
                "**Music Prompt:**\nEpic fantasy orchestra, slow build-up, thunderstorm ambience, Celtic flute melody\n\n"
                "**Lyrics:**\n"
                "[00:13.20]Your shadow dances on the dashboard shrine\n"
                "[00:16.85]Neon ghosts in gasoline rain\n"
                "[00:20.40]I hear your laughter down the midnight train\n\n"
                "Now, based on the following image, generate a new musical prompt and a complete set of timestamped lyrics in English only. "
                "The timestamps must be tailored to the pacing, rhythm, and mood inspired by the image. "
                "The output must include at least 12 lines of lyrics. The entire output must be written in English only. "
                "Follow the same format as the example.\n\n"
                "Start with the **Music Prompt**, then write **Lyrics** with appropriately spaced timestamps in the format [MM:SS.xx]. "
                "Ensure the lyrics are at least 12 lines long, written only in English, and maintain a consistent emotional tone."
            )
        else:
            prompt = (
                "以下是如何根据图像生成音乐风格和歌词的示例。歌词需要包含时间戳，格式为 [MM:SS.xx]，时间戳应与画面情绪与节奏相符。\n\n"
                "**音乐风格：**\n伤感氛围电子，慢节奏，钢琴伴奏，雨声背景\n\n"
                "**歌词：**\n"
                "[00:13.20]雨滴敲打窗前的寂静\n"
                "[00:16.85]街灯映出你的背影\n"
                "[00:20.40]我在梦中等你的回应\n\n"
                "现在请根据下图生成一个新的音乐风格描述和完整的时间戳歌词。"
                "歌词必须贴合图像传达的情绪与节奏，并且不少于12行。格式需与上例一致。\n\n"
                "请以 **音乐风格：** 开始，然后生成带有时间戳的 **歌词：**，时间戳格式为 [MM:SS.xx]。歌词不少于12行。"
            )

        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image", "image": self.image_path}
            ],
        }]
        
        return messages

    def _postprocess(self, output: str):
        prompt, lyrics = extract_prompt_and_lyrics(output, lang=self.language)
        lyrics_norm = normalize_lrc(lyrics)
        return prompt, lyrics_norm


class ImageToTagsProcessor(BaseLLMProcessor):
    def __init__(self, image_path: str, language: str = "en"):
        super().__init__(
            image_path,
            language,
            max_new_tokens=256,
            temperature=1.0,
            top_p=0.9,
            do_sample=True
        )

    def _mock_generate(self):
        return (
            "**inspirational tags**: [liquid sunrise shimmer, echoing ocean drums, "
            "celestial mountain chords, sun-kissed lullaby, cloud-swept reverie, "
            "surf-string arpeggios, high-tide crescendos, horizon-harp resonance, "
            "crystal dewdrop pulses, twilight breeze vocals, lunar tide harmonics, "
            "prism wave textures, amber dusk motifs, starlight cascade loops, "
            "marshland echo layers, velvet swell undertones, neon reef staccato, "
            "driftwood melody drift, glacier hum ambient, forest canopy reverb, "
            "ember glow motifs, solar flare synth washes, polar night drones, "
            "golden hour fanfare]"
        )

    def _build_messages(self):
        if self.language == "en":
            content = (
                "You are a multimodal creativity assistant for music producers.\n"
                "Given the provided image, analyze its mood, visual features, atmosphere, and possible sonic inspirations.\n"
                "Your task is to generate at least 24 diverse inspirational tags that combine:\n"
                "- Visual elements (colors, scenery, light, motion, emotion)\n"
                "- Textural impressions (surfaces, ambience, energy)\n"
                "- Musical or production ideas (textures, instrumentation, rhythm, structure)\n\n"
                "Do not focus only on existing genres or styles. Instead, combine abstract imagery, mood, and sonic inspiration freely to give the composer new creative directions.\n"
                "Tags may include combinations like: 'crystal sunrise shimmer', 'echo-lag surf textures', 'aurora pad resonance', 'liquid rhythm cascade', 'salt-wind percussion', 'twilight pulse drift', etc.\n\n"
                "Strict formatting rules:\n"
                "1. Output only in the following format:\n"
                "**inspirational tags**: [tag1, tag2, tag3, tag4, tag5, tag6, tag7, tag8]\n"
                "2. Do not add explanations, commentary, or any other text before or after.\n"
                "3. Do not number the tags. Separate them by commas inside the brackets."
            )
        else:
            content = (
                "你是一名面向音乐制作人的多模态灵感助手。\n"
                "根据提供的图像，分析其情绪、视觉特征、氛围以及可能的声音灵感。\n"
                "请生成至少 24 个多样化的灵感标签，结合以下元素：\n"
                "- 视觉元素（颜色、景观、光影、动态、情感）\n"
                "- 质感印象（表面、氛围、能量感）\n"
                "- 音乐或制作灵感（音色、乐器、节奏、结构）\n\n"
                "不要只局限于已有风格或流派。可自由混合抽象意象、氛围和声音概念，给予制作人跳脱框架的新方向。\n"
                "标签可以是如：'水晶晨曦闪烁'、'回声延迟海浪质感'、'极光合成垫'、'液态节奏瀑布'、'盐风打击乐'、'暮色律动漂移' 等。\n\n"
                "严格格式要求：\n"
                "1. 仅以以下格式输出：\n"
                "**灵感标签**: [标签1, 标签2, 标签3, 标签4, 标签5, 标签6, 标签7, 标签8]\n"
                "2. 不要添加任何解释、评论或额外文字。\n"
                "3. 标签之间用英文逗号分隔，不要编号。"
            )

        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": content},
                {"type": "image", "image": self.image_path}
            ],
        }]
        
        return messages

    def _postprocess(self, output: str):

        pattern_en = r"\*\*inspirational tags\*\*:\s*\[(.*?)\]"
        pattern_cn = r"\*\*灵感标签\*\*:\s*\[(.*?)\]"

        match = re.search(pattern_en, output, re.IGNORECASE)
        if not match:
            match = re.search(pattern_cn, output, re.IGNORECASE)

        if not match:
            # Relaxed fallback (without brackets)
            pattern_relaxed_en = r"\*\*inspirational tags\*\*:\s*(.*)"
            pattern_relaxed_cn = r"\*\*灵感标签\*\*:\s*(.*)"

            match = re.search(pattern_relaxed_en, output, re.IGNORECASE)
            if not match:
                match = re.search(pattern_relaxed_cn, output, re.IGNORECASE)

        if match:
            raw = match.group(1)
            raw = raw.strip().strip("[]")  # remove brackets if accidentally present

            # Split by comma
            parts = raw.split(',')

            # Clean each tag: strip whitespace and surrounding * if present
            tags = [re.sub(r'^\*|\*$', '', part.strip()) for part in parts if part.strip()]
            return tags

        return []
    
class ImageToVisualEntitiesProcessor(BaseLLMProcessor):
    """
    Extracts a set of concise visual entities/keywords from the image
    to drive image search.
    """
    def __init__(self, image_path: str, language: str = "en"):
        super().__init__(
            image_path,
            language,
            max_new_tokens=128,
            temperature=0.7,
            top_p=0.9,
            do_sample=False
        )

    def _mock_generate(self):
        return (
            '["dreamlike sunrise", "soft ocean waves", "golden horizon", '
            '"ethereal sky", "mountain silhouettes", "morning haze", '
            '"pastel reflections", "serene shoreline"]'
        )

    def _build_messages(self):
        if self.language == "en":
            prompt = (
                "You are a multimodal creative assistant. Analyze the provided image and extract 5 to 8 concise keywords or short phrases describing abstract, conceptual, stylistic, or mood-related aspects of the scene. "
                "Focus on atmosphere, textures, colors, visual styles, artistic impressions, and emotions that could inspire creative work such as music, art, or design. "
                "Avoid literal object names, real-world person names, celebrities, geographic names, brands, or factual labels. Do not include any names of people or locations.\n\n"
                "If any extracted keyword might imply real people, real faces, real body parts, or real-life objects, you must automatically convert it into a stylized or abstract form by appending descriptors such as 'illustration', 'cartoon', 'animation', 'line art', 'sketch', or 'painting' to ensure full abstraction and safety.\n\n"
                "Your output must strictly follow the exact format below, without any additions, explanations, or comments:\n\n"
                '["keyword1", "keyword2", "keyword3", "keyword4", "keyword5", "keyword6", "keyword7", "keyword8"]\n\n'
                "Example:\n"
                '["dreamlike sunrise", "rolling ocean texture", "soft gradient sky", "ethereal clouds", "serene mountain curves", "warm golden glow", "pastel horizon", "morning breeze mood"]\n\n'
                "Now, based on the provided image, generate a new JSON array following this exact format. "
                "The array must contain between 5 and 8 concise keywords or short phrases reflecting the scene's visual atmosphere, textures, styles, or emotions. "
                "If necessary, apply stylization as instructed above. Output only the JSON array in English, without any extra text."
            )
        else:
            prompt = (
                "你是一名多模态创意助手。请分析所给图像，提取 5 到 8 个简洁的关键词或短语，描述图像的抽象概念、风格特点、氛围、色彩或情感，能够启发音乐、艺术或设计创作。"
                "避免使用具体物体名称、人物姓名、地名、品牌或其他真实世界的标识。不要包含人物姓名或地理位置。\n\n"
                "如果提取出的关键词可能暗示真实人物、面孔、身体部位或现实世界物体，你必须自动将其转换为风格化或抽象形式，例如添加“插画”、“卡通”、“动画”、“简笔画”、“国画”等描述词，以确保抽象性与安全性。\n\n"
                "输出必须严格遵循以下格式，且不得添加任何说明、评论或额外内容：\n\n"
                '["关键词1", "关键词2", "关键词3", "关键词4", "关键词5", "关键词6", "关键词7", "关键词8"]\n\n'
                "示例：\n"
                '["梦幻日出", "翻滚的海浪纹理", "柔和的渐变天空", "空灵的云朵", "宁静的山峦曲线", "温暖的金色光辉", "柔和的地平线", "晨风的氛围"]\n\n'
                "现在请根据所提供的图像，生成新的 JSON 数组，格式与示例完全一致。"
                "数组必须包含 5 到 8 个简洁的关键词或短语，反映画面的视觉氛围、质感、风格或情感。"
                "如有需要，按上述要求自动进行风格化处理。输出仅包含 JSON 数组内容，且全部使用中文，不要添加任何额外文字。"
            )

        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image", "image": self.image_path}
            ],
        }]

        return messages

    def _postprocess(self, output: str):
        # Expect output like: ["tag1", "tag2", ...]
        try:
            import json
            arr = json.loads(output)
            return [str(x).strip() for x in arr if isinstance(x, str)]
        except Exception:
            # Fallback: simple regex
            tags = re.findall(r'"([^"]+)"', output)
            return tags