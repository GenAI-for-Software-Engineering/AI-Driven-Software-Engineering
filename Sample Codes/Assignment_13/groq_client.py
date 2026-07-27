"""
Groq API client wrapper.
Uses llama-3.3-70b-versatile with low temperature to reduce hallucination.
"""

from groq import Groq


class GroqClient:
    """
    Thin wrapper around the Groq SDK.
    Always uses llama-3.3-70b-versatile.
    temperature=0.1 → conservative, grounded outputs (less hallucination).
    """

    MODEL = "llama-3.3-70b-versatile"

    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)

    def chat(self, system_prompt: str, user_prompt: str, max_tokens: int = 4096) -> str:
        """
        Single-turn chat call.
        Returns the model's text response, stripped of whitespace.
        """
        response = self.client.chat.completions.create(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.1,   # low = deterministic, less hallucination
            top_p=0.9,
        )
        return response.choices[0].message.content.strip()
