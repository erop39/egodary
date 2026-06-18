"""Converter between model prompt formats."""

from __future__ import annotations


def convert_prompt(prompt: str, source_model: str, target_model: str) -> str:
    if source_model == target_model:
        return prompt
    if target_model == "zimage_turbo":
        tags = [t.strip() for t in prompt.replace("\n", ",").split(",") if t.strip()]
        sentence = ", ".join(tags[:24])
        return (
            f"{sentence}. Keep style coherent, avoid contradictory aesthetics, "
            "and prioritize clear anatomy."
        )
    if target_model == "anima":
        tags = [t.strip() for t in prompt.replace("\n", ",").split(",") if t.strip()]
        blocks = []
        chunks = [tags[i : i + 6] for i in range(0, min(len(tags), 60), 6)]
        for chunk in chunks[:14]:
            blocks.append(", ".join(chunk))
        while len(blocks) < 14:
            blocks.append("anime style")
        return "\n\n".join(blocks)
    # to illustrious tags list
    return ", ".join(t.strip() for t in prompt.replace("\n", ",").split(",") if t.strip())

