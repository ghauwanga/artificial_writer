import openai
API = ''

class Writer:
    def __init__(self, text):
        self.text = text
        self.err = ''

    def ai_text(self):
        """Summarize the given text using OpenAI's GPT-3.5."""
        try:
            openai.api_key = API
            openai.base_url = "https://free.v36.cm/v1/"
            openai.default_headers = {"x-foo": "true"}
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "user",
                        "content": f"Please provide a detailed summary of the following text:\n\n{self.text}"
                    },
                ]
            )
            summary = response.choices[0].message.content
            return summary
        except Exception as e:
            self.err = e
            return ""