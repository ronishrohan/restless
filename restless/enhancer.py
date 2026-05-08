import os
from openai import OpenAI
from restless.parser import EndpointSpec

SYSTEM_PROMPT = """You are improving tool descriptions for an MCP server used by AI agents.
Rewrite the description to be clearer about:
- What the tool does (action + object)
- What key parameters mean
- What it returns
Keep it under 2 sentences. Be direct and specific."""


def enhance_descriptions(endpoints: list[EndpointSpec]) -> list[EndpointSpec]:
    client = OpenAI(
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com",
    )

    enhanced = []
    for ep in endpoints:
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Tool: {ep.name}\nEndpoint: {ep.method.upper()} {ep.path}\nCurrent description: {ep.description}"},
                ],
                max_tokens=100,
            )
            new_desc = response.choices[0].message.content.strip()
            enhanced.append(EndpointSpec(
                **{**ep.__dict__, "description": new_desc}
            ))
        except Exception:
            enhanced.append(ep)

    return enhanced
