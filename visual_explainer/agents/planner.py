import os
from typing import List

from pydantic import BaseModel, Field

from visual_explainer.state import Scene

from .agent import BaseAgent
from .prompts.planner import PLANNER_PROMPT


class PlannerOutput(BaseModel):
    scenes: List[Scene] = Field(description="The chronological list of scenes for the video.")

class Planner(BaseAgent):
    def __init__(self, client):
        super().__init__(
            llm_client=client,
            model=os.getenv("PLANNER_LLM", ""),
            system_prompt=PLANNER_PROMPT,
            agent_name="Planner",
            output_schema=PlannerOutput
        )
        
if __name__ == "__main__":
    from dotenv import load_dotenv
    from groq import Groq
    load_dotenv()
    
    client = Groq()
    planner = Planner(client)
    output: PlannerOutput = planner.invoke([
        {"role": "user", "content": "Explain the concept of 'Pythagoras theorem'"}
    ])
    
    print(output.model_dump_json(indent=4))