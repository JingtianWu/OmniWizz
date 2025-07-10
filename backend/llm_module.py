import torch
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
from config import TEST_MODE

class LLMProcessor:
    def __init__(self, image_path, language="en"):
        self.image_path = image_path
        self.language = language
        self.device = torch.device(
            "mps" if torch.backends.mps.is_available() else
            "cuda" if torch.cuda.is_available() else
            "cpu"
        )

        if not TEST_MODE:
            self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                "Qwen/Qwen2.5-VL-3B-Instruct",
                torch_dtype=torch.bfloat16,
                attn_implementation="eager",
                device_map="auto"
            )
            self.processor = AutoProcessor.from_pretrained("Qwen/Qwen2.5-VL-3B-Instruct")
            self.model.to(self.device)
        else:
            self.model = None
            self.processor = None

    def generate(self):
        if self.model is None or self.processor is None:
            raise RuntimeError("Model not loaded (TEST_MODE enabled)")
        messages = self._build_messages()
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(
            text=[text], images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt"
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        gen_ids = self.model.generate(
            **inputs, max_new_tokens=512, temperature=1.2, top_p=0.95, do_sample=True
        )

        decoded = self.processor.batch_decode(
            [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs["input_ids"], gen_ids)],
            skip_special_tokens=True
        )[0]

        return decoded

    def _build_messages(self):
        if self.language == "en":
            messages = [{
                "role": "user",
                "content": [
                    {"type": "text", "text":
                     "Here is an example of how to describe an image musically and generate lyrics. "
                     "The lyrics should be timestamped in the format [MM:SS.xx], and the timestamps should be chosen "
                     "to match the pacing and emotion of the scene.\n\n"
                     "**Music Prompt:**\nEpic fantasy orchestra, slow build-up, thunderstorm ambience, Celtic flute melody\n\n"
                     "**Lyrics:**\n"
                     "Your shadow dances on the dashboard shrine\n"
                     "Neon ghosts in gasoline rain\n"
                     "I hear your laughter down the midnight train\n\n"
                     "Now, based on the following image, generate a new musical prompt and a complete set of timestamped lyrics in English only. "
                     "The timestamps must be tailored to the pacing, rhythm, and mood inspired by the image. "
                     "The output must include at least 12 lines of lyrics. The entire output must be written in English only. "
                     "Follow the same format as the example."},
                    {"type": "image", "image": self.image_path},
                    {"type": "text", "text":
                     "Start with the **Music Prompt**, then write **Lyrics**. "
                     "Ensure the lyrics are at least 12 lines long, written only in English, and maintain a consistent emotional tone."}
                ],
            }]
        else:
            messages = [{
                "role": "user",
                "content": [
                    {"type": "text", "text":
                     "以下是如何根据图像生成音乐风格和歌词的示例。歌词需要包含时间戳，格式为 [MM:SS.xx]，时间戳应与画面情绪与节奏相符。\n\n"
                     "**音乐风格：**\n伤感氛围电子，慢节奏，钢琴伴奏，雨声背景\n\n"
                     "**歌词：**\n"
                     "雨滴敲打窗前的寂静\n"
                     "街灯映出你的背影\n"
                     "我在梦中等你的回应\n\n"
                     "现在请根据下图生成一个新的音乐风格描述和完整的时间戳歌词。"
                     "歌词必须贴合图像传达的情绪与节奏，并且不少于12行。格式需与上例一致。"},
                    {"type": "image", "image": self.image_path},
                    {"type": "text", "text":
                     "请以 **音乐风格：** 开始，然后生成 **歌词：**。歌词不少于12行。"}
                ],
            }]
        return messages