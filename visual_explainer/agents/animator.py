import os

from dotenv import load_dotenv

load_dotenv()

from pydantic import BaseModel, Field

from .agent import BaseAgent
from .prompts.animator import ANIMATOR_PROMPT

"""
PLANNED TOOLS FOR THIS AGENT:
- First iteration:
    - Only a code execution tool
    - Validate the code by checking for a construct function, a class with Scene parent and manim imports
- Second iteration:
    - Use an AST parser to validate the errors in Python code
    - Add a RAG Agent, that has already queried many many existing Manim codes
"""

class AnimatorOutput(BaseModel):
    manim_code: str = Field(description="Pythonic code, written for Manim CE library to render the scene animation")

class Animator(BaseAgent):
    def __init__(self, llm_client):
        super().__init__(
            llm_client=llm_client,
            model=os.getenv("ANIMATOR_LLM", ""),
            system_prompt=ANIMATOR_PROMPT,
            tools_registry={},
            tools_schemas=[],
            output_schema=AnimatorOutput
        )

if __name__ == "__main__":
    import json

    from dotenv import load_dotenv
    from groq import Groq

    from visual_explainer.state import AgentState, merge_scenes

    from .planner import Planner, PlannerOutput
    from .storyboarder import Storyboarder, StoryboarderOutput
    load_dotenv()

    client = Groq()
    planner = Planner(client)
    storyboarder = Storyboarder(client)
    animator = Animator(client)

    planner_output: PlannerOutput = planner.invoke([
        {"role": "user", "content": "Explain the concept of 'Pythagoras theorem'"}
    ])
    print("Planner has generated the script")

    agent_state = AgentState(thread_id="test-thread", topic="Pythagoras theorem", scenes=planner_output.scenes)

    # Storyboarder step
    for scene in agent_state.scenes:
        print(f"Starting storyboarding for scene {scene.id}")
        scene_input = [
            {"role": "user", "content": f"Storyboard this scene: {json.dumps(scene.model_dump())}"}
        ]
        storyboarder_output: StoryboarderOutput = storyboarder.invoke(scene_input)
        updated_scene = scene.model_copy(update={
            "storyboard": storyboarder_output.storyboard,
            "animation_instructions": storyboarder_output.animation_instruction
        })
        agent_state.scenes = merge_scenes(agent_state.scenes, [updated_scene])

    # Animator step
    for scene in agent_state.scenes:
        print(f"Starting animation for scene {scene.id}")
        scene_input = [
            {"role": "user", "content": f"Write manim code for this scene: {json.dumps(scene.model_dump())}"}
        ]
        animator_output: AnimatorOutput = animator.invoke(scene_input)
        updated_scene = scene.model_copy(update={
            "manim_code": animator_output.manim_code
        })
        agent_state.scenes = merge_scenes(agent_state.scenes, [updated_scene])

    print("Final AgentState output:")
    print(json.dumps([scene.model_dump() for scene in agent_state.scenes], indent=4))