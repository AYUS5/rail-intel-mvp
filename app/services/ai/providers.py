from abc import ABC, abstractmethod


class ExplanationProvider(ABC):
    @abstractmethod
    async def summarize(self, prompt: str) -> str:
        raise NotImplementedError


class TemplateExplanationProvider(ExplanationProvider):
    async def summarize(self, prompt: str) -> str:
        return prompt


class OpenAIExplanationProvider(ExplanationProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    async def summarize(self, prompt: str) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._api_key)
        response = await client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You explain train availability intelligence in concise, compliant "
                        "language. Never suggest captcha bypassing, login automation, OTP "
                        "bypassing, or ticket purchasing automation."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=180,
        )
        return (response.choices[0].message.content or "").strip()
