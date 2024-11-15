from kag.interface import PromptABC


def init_prompt_with_fallback(prompt_name, biz_scene):
    try:
        return PromptABC.from_config({"type": f"{biz_scene}_{prompt_name}"})
    except Exception as e:
        print(
            f"fail to initialize prompts with biz scene {biz_scene}, fallback to default biz scene"
        )

        return PromptABC.from_config({"type": f"default_{prompt_name}"})
