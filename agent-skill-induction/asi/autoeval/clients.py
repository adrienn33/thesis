import os
import base64
import anthropic
import numpy as np
from PIL import Image
from typing import Union, Optional
import io

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


class LM_Client:
    def __init__(self, model_name: str = "claude-haiku-4-5") -> None:
        self.model_name = model_name

    def chat(self, messages, json_mode: bool = False):
        """
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "hi"},
        ])
        """
        system_msg = next((msg["content"] for msg in messages if msg["role"] == "system"), "")
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        
        import time
        import random
        
        max_retries = 5
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = client.messages.create(
                    model=self.model_name,
                    max_tokens=4096,
                    temperature=0,
                    system=system_msg,
                    messages=user_messages,
                )
                break
            except Exception as e:
                if "529" in str(e) or "overloaded" in str(e).lower() or "rate" in str(e).lower():
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        print(f"Rate limited, waiting {delay:.1f}s before retry {attempt + 1}/{max_retries}")
                        time.sleep(delay)
                        continue
                raise e
        content = response.content[0].text
        return content, response

    def one_step_chat(
        self, text, system_msg: str = None, json_mode=False
    ):
        messages = []
        if system_msg is not None:
            messages.append({"role": "system", "content": system_msg})
        messages.append({"role": "user", "content": text})
        return self.chat(messages, json_mode=json_mode)


class Claude_Vision_Client:
    def __init__(self, model_name: str = "claude-3-5-sonnet-20241022", max_tokens: int = 512):
        # Use Haiku 4.5 for evaluation to avoid model availability issues
        if model_name == "claude-3-5-sonnet-20241022":
            model_name = "claude-haiku-4-5"
        self.model_name = model_name
        self.max_tokens = max_tokens

    def encode_image(self, image_input):
        """Convert image to base64 for Claude."""
        if isinstance(image_input, str):
            # File path
            with open(image_input, 'rb') as f:
                image_data = f.read()
            # Detect media type based on file extension
            if image_input.lower().endswith(('.png')):
                media_type = "image/png"
            else:
                media_type = "image/jpeg"
        elif isinstance(image_input, (Image.Image, np.ndarray)):
            # Convert PIL Image or numpy array to bytes
            if isinstance(image_input, np.ndarray):
                image_input = Image.fromarray(image_input.astype('uint8'))
            buffer = io.BytesIO()
            image_input.save(buffer, format='PNG')  # Use PNG for better compatibility
            image_data = buffer.getvalue()
            media_type = "image/png"
        else:
            raise ValueError("Unsupported image type")
            
        return base64.b64encode(image_data).decode('utf-8'), media_type
                         
    def one_step_chat(
        self, text, image: Union[Image.Image, np.ndarray, str], 
        system_msg: Optional[str] = None,
    ):
        image_base64, media_type = self.encode_image(image)
        
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_base64,
                    },
                },
            ],
        }]
        
        import time
        import random
        
        max_retries = 5
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = client.messages.create(
                    model=self.model_name,
                    max_tokens=self.max_tokens,
                    temperature=0,
                    system=system_msg or "",
                    messages=messages,
                )
                break
            except Exception as e:
                if "529" in str(e) or "overloaded" in str(e).lower() or "rate" in str(e).lower():
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        print(f"Rate limited, waiting {delay:.1f}s before retry {attempt + 1}/{max_retries}")
                        time.sleep(delay)
                        continue
                raise e
        return response.content[0].text, response


CLIENT_DICT = {
    "claude-haiku-4-5": LM_Client,
    "claude-3-5-sonnet-20241022": Claude_Vision_Client,
    "gpt-3.5-turbo": LM_Client,
    "gpt-4": LM_Client,
    "gpt-4o": Claude_Vision_Client,  # Using Claude vision for GPT-4o requests
    "gpt-4o-2024-05-13": Claude_Vision_Client,  # Using Claude vision for GPT-4o requests
}