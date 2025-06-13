from pathlib import Path
from llm_module import LLMProcessor
from diffrhythm_module import run_inference

def generate_from_image(image_file_path, language="en"):
    # image_file_path: e.g. "/abs/path/to/foo.jpg"
    image_uri = f"file://{image_file_path}"
    llm = LLMProcessor(image_uri, language=language)
    assistant_reply = llm.generate()
    audio_path = run_inference(assistant_reply)
    return audio_path