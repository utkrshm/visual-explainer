from unittest.mock import MagicMock

from groq import Groq
from pydantic import BaseModel

from visual_explainer.agents.agent import BaseAgent

# Mock Client
mock_client = MagicMock(spec=Groq)
mock_client.chat.completions.create = MagicMock()

# Mock Response for LLM
def create_mock_response(content=None, tool_calls=None):
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls
    message.role = "assistant"
    
    choice = MagicMock()
    choice.message = message
    
    response = MagicMock()
    response.choices = [choice]
    return response


# Tools
def add(a: int, b: int):
    return a + b

tools_registry = {"add": add}
tools_schemas = [{"type": "function", "function": {"name": "add", "parameters": {}}}]

# Output Schema
class Result(BaseModel):
    answer: str

# Instantiate Agent
agent = BaseAgent(
    llm_client=mock_client,
    model="test-model",
    system_prompt="System Prompt",
    tools_registry=tools_registry,
    tools_schemas=tools_schemas,
    output_schema=Result
)

# Test 1: Direct Structured Output
print("Test 1: Direct Structured Output")
mock_client.chat.completions.create.return_value = create_mock_response(content='{"answer": "42"}')
result = agent.invoke([{"role": "user", "content": "What is the answer?"}])
print(f"Result: {result}")
assert isinstance(result, Result)
assert result.answer == "42"

# Test 2: Tool Call then Output
print("\nTest 2: Tool Call then Output")
# Mock tool call response
tool_call = MagicMock()
tool_call.id = "call_1"
tool_call.function.name = "add"
tool_call.function.arguments = '{"a": 1, "b": 2}'

# Sequence of responses: Tool Call -> Final Answer
mock_client.chat.completions.create.side_effect = [
    create_mock_response(tool_calls=[tool_call]), # First call returns tool
    create_mock_response(content='{"answer": "3"}') # Second call returns answer after tool result
]

result = agent.invoke([{"role": "user", "content": "Add 1 and 2"}])
print(f"Result: {result}")
assert isinstance(result, Result)
assert result.answer == "3"

print("\nAll tests passed!")
