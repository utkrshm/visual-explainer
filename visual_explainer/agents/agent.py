import json
from typing import Any, Callable, Dict, List, Optional, Union

import instructor
from groq import AsyncGroq, Groq
from pydantic import BaseModel


class BaseAgent:
    def __init__(
        self,
        llm_client: Union[Groq, AsyncGroq], 
        model: str, 
        system_prompt: str, 
        agent_name: str = "Agent",
        tools_registry: Optional[Dict[str, Callable]] = None, 
        tools_schemas: Optional[List[Dict[str, Any]]] = None, 
        output_schema: Optional[BaseModel] = None, 
        extractor_model: Optional[str] = "llama3-70b-8192"
    ):
        assert isinstance(llm_client, Groq) or isinstance(llm_client, AsyncGroq), "You must provide an LLM client"
        assert isinstance(model, str), "The model must be a string"
        if (tools_registry and not tools_schemas) or (tools_schemas and not tools_registry):
            raise AssertionError("Tools schema and tools registry must both be provided")
            
        self.llm = llm_client
        self.model = model
        self.system_prompt = system_prompt
        self.agent_name = agent_name
        self.tools = tools_registry
        self.tool_schemas = tools_schemas
        self.output_schema = output_schema
        
        # Initialize instructor client for structured extraction fallback
        if isinstance(llm_client, Groq):
            self.output_extractor = instructor.from_groq(llm_client)
        else:
            self.output_extractor = instructor.from_groq(llm_client) # instructor handles async groq too
            
        self.extractor_model = extractor_model
    
    def __repr__(self):
        return f"Agent(name={self.agent_name}, model={self.model})"
    
    def _make_llm_call(self, messages):
        params = {
            "messages": messages,
            "model": self.model,
        }
        if self.tool_schemas:
            params["tools"] = self.tool_schemas
            params["tool_choice"] = "auto"
            
        return self.llm.chat.completions.create(**params)
    
    def _extract_structured_output(self, content: Optional[str]):
        if not self.output_schema:
            return content
            
        if not content:
            # If no content, we can't parse it directly, so we use the extractor
            # to see if it can generate the output from the conversation context (less likely)
            # or we just return an empty/default model if possible.
            # But usually, we expect content if tools are finished.
            return self._run_extractor("No content provided by model.")

        try:
            return self.output_schema.model_validate_json(content)
        except Exception:
            return self._run_extractor(content)

    def _run_extractor(self, content: str):
        return self.output_extractor.chat.completions.create(   # type: ignore
            response_model=self.output_schema,
            messages=[
                {
                    "role": "system",
                    "content": "Extract the following structured data from the provided text."
                },
                {
                    "role": "user",
                    "content": content
                }
            ],
            model=self.extractor_model,
            strict=True,
            
        )
    
    def _handle_tool_call(self, tool_calls):
        messages = []
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            if self.tools and function_name in self.tools:
                try:
                    function_response = self.tools[function_name](**function_args)
                except Exception as e:
                    function_response = f"Error: {str(e)}"
                    
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": str(function_response),
                    }
                )
        return messages
    
    def invoke(self, messages: List[Dict[str, str]]):
        current_messages = messages.copy()
        
        # Check for system prompt, if it's not present, then we need to add it to the chain.
        if self.system_prompt:
             if not any(m.get("role") == "system" for m in current_messages):
                 current_messages.insert(0, {"role": "system", "content": self.system_prompt})
        
        while True:
            response = self._make_llm_call(current_messages)
            response_message = response.choices[0].message
            
            current_messages.append(response_message)
            
            # If a tool call is encountered, then keep looping running
            if response_message.tool_calls:
                tool_messages = self._handle_tool_call(response_message.tool_calls)
                current_messages.extend(tool_messages)
            else:
                response = self._extract_structured_output(response_message.content)
                messages.append({"role": "assistant", "content": str(response)})
                return response
    

if __name__ == "__main__":
    import os

    from dotenv import load_dotenv
    load_dotenv()
    
    client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
    agent = BaseAgent(client, "llama3-8b-8192", "You are a helpful assistant.")
    print(agent)