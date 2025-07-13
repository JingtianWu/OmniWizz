import requests
import re
import ast
from udio_module import extract_prompt_and_lyrics
from config import TEST_MODE, OPENAI_API_KEY
import base64
import mimetypes

def _to_data_url(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:{mime or 'application/octet-stream'};base64,{b64}"

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

        # in production we use the hosted GPT model; no local weights loaded

    def generate(self) -> str:
        if TEST_MODE:
            return self._mock_generate()
        return self._real_generate()

    def _real_generate(self) -> str:
        messages = self._build_messages()

        # Convert Qwen-style message format to OpenAI format
        oa_msgs = []
        for m in messages:
            content_items = []
            for c in m.get("content", []):
                if c.get("type") == "text":
                    content_items.append({"type": "text", "text": c.get("text", "")})
                elif c.get("type") == "image":
                    url = c.get("image")
                    if url.startswith("file://"):
                        url = _to_data_url(url[7:])  # remove "file://" and convert to data URL
                    content_items.append({"type": "image_url", "image_url": {"url": url}})
            oa_msgs.append({"role": m.get("role", "user"), "content": content_items})

        payload = {
            "model": "gpt-4.1-mini",
            "messages": oa_msgs,
            "max_tokens": self.max_new_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
        }
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }

        res = requests.post(
            "https://api.openai.com/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=60,
        )
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]

    def process(self):
        raw = self.generate()
        print("\n=== RAW MODEL OUTPUT ===\n", raw, "\n=== END ===")
        return self._postprocess(raw)

    def _build_messages(self):
        raise NotImplementedError("Subclasses must implement _build_messages().")

    def _postprocess(self, output: str):
        raise NotImplementedError("Subclasses must implement _postprocess().")


class ImageToLyricsProcessor(BaseLLMProcessor):
    def __init__(self, image_path: str, language: str = "en", chords: dict | None = None):
        super().__init__(
            image_path,
            language,
            max_new_tokens=512,
            temperature=1.2,
            top_p=0.95,
            do_sample=True
        )
        self.chords = chords or {}

    def _mock_generate(self):
        return (
            "**Music Prompt:** Calm piano, soft ambient pads, morning breeze, light percussion\n\n"
            "**Lyrics:**\n"
            "Waves gently touch the shore\n"
            "Sunrise colors fill the air\n"
            "Mountains watching from afar\n"
            "Clouds drift like cotton dreams\n"
            "Heartbeats match the morning breeze\n"
            "Footprints mark the golden sand\n"
            "Melody flows from ocean winds\n"
            "Distant peaks hum harmonies\n"
            "Seagulls glide above the waves\n"
            "Whispers of the coming day\n"
            "Warmth wraps around my soul\n"
            "Hope awakens with the light"
        )

    def _build_messages(self):
        if self.language == "en":
            chord_text = ""
            if self.chords.get("chords"):
                prog = " - ".join(self.chords["chords"])
                key = self.chords.get("key", "")
                chord_text = f"The user's audio is in the key of {key} with the chord progression: {prog}. Use this as inspiration.\n\n"
            prompt = (
                "Here is an example of how to describe an image musically and generate lyrics.\n\n"
                "**Music Prompt:**\nEpic fantasy orchestra, slow build-up, thunderstorm ambience, Celtic flute melody\n\n"
                "**Lyrics:**\n"
                "Your shadow dances on the dashboard shrine\n"
                "Neon ghosts in gasoline rain\n"
                "I hear your laughter down the midnight train\n\n"
                "Now, based on the following image, generate a new musical prompt and a complete set of lyrics in English only. "
                "The output must include at least 12 lines of lyrics written entirely in English. "
                "Follow the same format as the example, but no timestamps are needed.\n\n"
                f"{chord_text}Start with the **Music Prompt**, then write **Lyrics**. "
                "Ensure the lyrics are at least 12 lines long and maintain a consistent emotional tone."
            )
        else:
            chord_text = ""
            if self.chords.get("chords"):
                prog = " - ".join(self.chords["chords"])
                key = self.chords.get("key", "")
                chord_text = f"用户上传的音频被分析为{key}调，和弦进行: {prog}。请结合这些信息。\n\n"
            prompt = (
                "以下是如何根据图像生成音乐风格和歌词的示例。\n\n"
                "**音乐风格：**\n伤感氛围电子，慢节奏，钢琴伴奏，雨声背景\n\n"
                "**歌词：**\n"
                "雨滴敲打窗前的寂静\n"
                "街灯映出你的背影\n"
                "我在梦中等你的回应\n\n"
                "现在请根据下图生成新的音乐风格描述和完整歌词。"
                "歌词必须贴合图像传达的情绪与节奏，并且不少于12行。格式需与上例一致。\n\n"
                f"{chord_text}请以 **音乐风格：** 开始，然后生成 **歌词：**，无需时间戳，歌词不少于12行。"
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
        return prompt, lyrics


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
            "**inspirational tags**: [cathedral blaze shimmer, gilded vault echoes, stained glass resonance, "
            "emberfall choir drift, marble dusk pulse, arcane reverb bloom, lightfall crescendo, sacred hush texture, "
            "vaulted halo drift, chandelier thrum, gold-draped silence, catacomb bass undertow, divine delay shimmer, "
            "twilight liturgy pads, solemn flare pulse, celestial chamber bloom, lightbeam swell, echo altar mist, "
            "granite choir ghost, ritual flame rhythm, midnight votive haze, gothic cadence glint, glory dusk rise, "
            "archlight ritual drone]"
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
                "Tags may include combinations like: [\"crystal sunrise shimmer\", \"echo-lag surf textures\", \"aurora pad resonance\", \"liquid rhythm cascade\", \"heartbeat echo\", \"post-rain moss\", \"liquid dusk glow\", \"mossy forest hush\"]\n\n"
                "Strict formatting rules:\n"
                "1. Output only in the following format:\n"
                "**inspirational tags**: [\"tag1\", \"tag2\", \"tag3\", \"tag4\", \"tag5\", \"tag6\", \"tag7\", \"tag8\"]\n"
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
                "标签可以是如：[\"雨后青苔\", \"石径水声节拍\", \"心跳回声\", \"液态节奏瀑布\", \"湖面晚风拨弦\", \"极光\", \"暮色微光\", \"苔原低语\"]\n\n"
                "严格格式要求：\n"
                "1. 仅以以下格式输出：\n"
                "**灵感标签**: [\"标签1\", \"标签2\", \"标签3\", \"标签4\", \"标签5\", \"标签6\", \"标签7\", \"标签8\"]\n"
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
        tags = []

        # Normalize the string to avoid invisible BOM, smart quotes, etc.
        output = output.strip().replace('\uFEFF', '').replace('“','"').replace('”','"').replace("‘","'").replace("’","'")

        # Step 1: Attempt to parse as raw list literal directly
        try:
            parsed = ast.literal_eval(output)
            if isinstance(parsed, list):
                tags = [str(item).strip() for item in parsed]
                return tags
        except (SyntaxError, ValueError):
            pass  # Continue if not a list literal

        # Step 2: Define multiple patterns
        patterns = [
            r"\*\*inspirational tags\*\*:\s*\[(.*?)\]",
            r"\*\*灵感标签\*\*:\s*\[(.*?)\]",
            r"\*\*inspirational tags\*\*:\s*(.*)",
            r"\*\*灵感标签\*\*:\s*(.*)",
        ]

        match = None
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE | re.DOTALL)
            if match:
                raw = match.group(1).strip()
                break

        # Step 3: Try to parse matched content as list literal (bracketed or not)
        if match:
            # Clean stray brackets if present accidentally
            raw_cleaned = raw.strip("[]").strip()

            # Try parsing as list literal again
            try:
                parsed = ast.literal_eval(f'[{raw_cleaned}]') if not raw.startswith('[') else ast.literal_eval(raw)
                if isinstance(parsed, list):
                    tags = [str(item).strip() for item in parsed]
                    return tags
            except (SyntaxError, ValueError):
                pass  # Fallback to manual splitting

            # Manual fallback parsing
            parts = re.split(r',(?![^\[\]]*\])', raw_cleaned)
            for part in parts:
                clean = part.strip()
                # Remove multiple surrounding asterisks (handles *tag*, **tag**, ***tag*** etc.)
                clean = re.sub(r'^\*+|\*+$', '', clean)
                # Remove redundant surrounding quotes
                clean = clean.strip('"').strip("'")
                if clean:
                    tags.append(clean)

        else:
            # Step 4: As ultimate fallback, search for any list-like content inside text
            list_match = re.search(r"\[([^\[\]]+)\]", output)
            if list_match:
                list_content = list_match.group(1)
                parts = list_content.split(',')
                for part in parts:
                    clean = part.strip()
                    clean = re.sub(r'^\*+|\*+$', '', clean)
                    clean = clean.strip('"').strip("'")
                    if clean:
                        tags.append(clean)

        return tags
    
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
                "You are a multimodal creative assistant. Analyze the provided image and extract at least 24 concise keywords or short phrases describing abstract, conceptual, stylistic, or mood-related aspects of the scene. "
                "Focus on atmosphere, textures, colors, visual styles, artistic impressions, and emotions that could inspire creative work such as music, art, or design. "
                "Avoid literal object names, real-world person names, celebrities, geographic names, brands, or factual labels. Do not include any names of people or locations.\n\n"
                "If any extracted keyword might imply real people, real faces, real body parts, or real-life objects, you must automatically convert it into a stylized or abstract form by appending descriptors such as 'illustration', 'cartoon', 'animation', 'line art', 'sketch', or 'painting' to ensure full abstraction and safety.\n\n"
                "Your output must strictly follow the exact format below, without any additions, explanations, or comments:\n\n"
                '["keyword1", "keyword2", "keyword3", "keyword4", "keyword5", "keyword6", "keyword7", "keyword8"]\n\n'
                "Example:\n"
                '["dreamlike sunrise", "rolling ocean texture", "soft gradient sky", "ethereal clouds", "serene mountain curves", "warm golden glow", "pastel horizon", "morning breeze mood"]\n\n'
                "Now, based on the provided image, generate a new JSON array following this exact format. "
                "The array must contain  at least 24 concise keywords or short phrases reflecting the scene's visual atmosphere, textures, styles, or emotions. "
                "If necessary, apply stylization as instructed above. Output only the JSON array in English, without any extra text."
            )
        else:
            prompt = (
                "你是一名多模态创意助手。请分析所给图像，提取至少 24 个简洁的关键词或短语，描述图像的抽象概念、风格特点、氛围、色彩或情感，能够启发音乐、艺术或设计创作。"
                "避免使用具体物体名称、人物姓名、地名、品牌或其他真实世界的标识。不要包含人物姓名或地理位置。\n\n"
                "如果提取出的关键词可能暗示真实人物、面孔、身体部位或现实世界物体，你必须自动将其转换为风格化或抽象形式，例如添加“插画”、“卡通”、“动画”、“简笔画”、“国画”等描述词，以确保抽象性与安全性。\n\n"
                "输出必须严格遵循以下格式，且不得添加任何说明、评论或额外内容：\n\n"
                '["关键词1", "关键词2", "关键词3", "关键词4", "关键词5", "关键词6", "关键词7", "关键词8"]\n\n'
                "示例：\n"
                '["梦幻日出", "翻滚的海浪纹理", "柔和的渐变天空", "空灵的云朵", "宁静的山峦曲线", "温暖的金色光辉", "柔和的地平线", "晨风的氛围"]\n\n'
                "现在请根据所提供的图像，生成新的 JSON 数组，格式与示例完全一致。"
                "数组必须包含至少 24 个简洁的关键词或短语，反映画面的视觉氛围、质感、风格或情感。"
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
            return [f"{str(x).strip()} abstract art" for x in arr if isinstance(x, str)]
        except Exception:
            import re
            # Fallback: simple regex
            tags = re.findall(r'"([^"]+)"', output)
            return [f"{tag.strip()} abstract art" for tag in tags]
