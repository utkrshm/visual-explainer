import os
from typing import Dict, List, Optional, Union

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from visual_explainer.tools.manim_execute import execute_manim_code

from .agent import BaseAgent
from .prompts.animator import ANIMATOR_PROMPT

load_dotenv()

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
    manim_code: str = Field(description="Pythonic code, written for Manim CE library to render the scene animation. Should include the import, the class name should be VideoScene, inheriting the Scene class from manim and should contain a construct() function")
    video_path: str = Field(default="", description="Path to which you need to store the video for this scene. IF YOU ARE AN AI AGENT, DO NOT UPDATE THIS FIELD")

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

    def invoke(self, messages: List[Dict[str, str]], scene_id: int, video_path: Optional[Union[str, os.PathLike]], n_retries: int = 3, ):
            
        for retry in range(n_retries):            
            # Code generation
            code_dict: AnimatorOutput = super().invoke(messages)

            # Try to execute the extract manim script
            execution_bool, status_str = execute_manim_code(code_dict.manim_code, scene_id=scene_id, video_path=video_path)
            
            if execution_bool:
                code_dict.video_path = status_str
                return code_dict
            else:
                print(f"[Scene {scene_id}] Attempt {retry + 1}/{n_retries} failed.")
                
                messages.extend([
                    {"role": "assistant", "content": json.dumps(code_dict.model_dump())},
                    {"role": "user", "content": f"The code you generated failed to execute with this error:\n\n{status_str}"}
                ])

        print(f"Animator failed after {n_retries} attempts, returning last output")
        return code_dict

if __name__ == "__main__":
    import json
    import time

    from dotenv import load_dotenv
    from groq import Groq

    from visual_explainer.state import AgentState, merge_scenes

    from .planner import Planner, PlannerOutput
    from .storyboarder import Storyboarder, StoryboarderOutput
    load_dotenv()

    def save_state(agent_state: AgentState, output_dir: str, checkpoint_name: str) -> None:
        """Save the current state to a checkpoint file."""
        os.makedirs(output_dir, exist_ok=True)
        checkpoint_path = os.path.join(output_dir, f"{checkpoint_name}.json")
        with open(checkpoint_path, "w") as f:
            json.dump([scene.model_dump() for scene in agent_state.scenes], f, indent=4)
        print(f"State saved: {checkpoint_path}")

    client = Groq()
    planner = Planner(client)
    storyboarder = Storyboarder(client)
    animator = Animator(client)

    planner_output: PlannerOutput = planner.invoke([
        {"role": "user", "content": "Explain the concept of 'Pythagoras theorem'"}
    ])
    print("Planner has generated the script")

    agent_state = AgentState(thread_id="test-thread", topic="Pythagoras theorem", scenes=planner_output.scenes)
    VIDEO_OUTPUT_DIR = os.path.join(os.path.abspath(os.path.curdir), "outputs", "videos", agent_state.thread_id)

    save_state(agent_state, VIDEO_OUTPUT_DIR, "state")

    for scene in agent_state.scenes:
        # ===============================
        #       Storyboarder step
        # ===============================
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
        save_state(agent_state, VIDEO_OUTPUT_DIR, "state")

        # ===============================
        #         Animator step
        # ===============================
        print(f"Starting animation for scene {scene.id}. Sleeping for 15 seconds first")
        time.sleep(15)
        
        scene_input = [
            {"role": "user", "content": f"Write manim code for this scene: {json.dumps(scene.model_dump())}"}
        ]
        animator_output: AnimatorOutput = animator.invoke(scene_input, scene.id, os.path.join(VIDEO_OUTPUT_DIR, f"scene_{scene.id}.mp4"))
        updated_scene = scene.model_copy(update={
            "manim_code": animator_output.manim_code
        })

        agent_state.scenes = merge_scenes(agent_state.scenes, [updated_scene])        
        save_state(agent_state, VIDEO_OUTPUT_DIR, "state")
    
    # Final state save
    save_state(agent_state, VIDEO_OUTPUT_DIR, "state")