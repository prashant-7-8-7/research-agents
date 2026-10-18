import ollama

MODEL = "qwen2.5:7b"

def ask(system: str, user: str, max_tokens: int = 1500) -> str:
    r = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        options={"num_predict": max_tokens, "temperature": 0.3, "num_ctx": 8192},
    )
    return r["message"]["content"]
