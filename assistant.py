import os, json, math
from openai import OpenAI, BadRequestError

client = OpenAI(api_key=os.environ["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1")
MODEL = "openai/gpt-oss-120b"

# ---- 1. The actual Python functions -----------------------------------------
MATH_NAMES = {n: getattr(math, n) for n in
              ["sqrt", "sin", "cos", "tan", "atan2", "radians", "degrees", "pi", "log", "exp"]}

def calculate(expression):
    try:
        # Learning-only: eval is NOT safe for untrusted input in a real product.
        return str(eval(expression, {"__builtins__": {}}, MATH_NAMES))
    except Exception as e:
        return f"Error: {e}"

# Each supported conversion = (from, to) -> multiply by this factor
CONVERSIONS = {
    ("m/s", "km/h"): 3.6,
    ("km/h", "m/s"): 1 / 3.6,
    ("rad", "deg"): 180 / math.pi,
    ("deg", "rad"): math.pi / 180,
    ("rad/s", "deg/s"): 180 / math.pi,
    ("deg/s", "rad/s"): math.pi / 180,
}
UNITS = ["m/s", "km/h", "rad", "deg", "rad/s", "deg/s"]

def convert_units(value, from_unit, to_unit):
    factor = CONVERSIONS.get((from_unit, to_unit))
    if factor is None:
        return f"Error: cannot convert {from_unit} to {to_unit}"
    return str(value * factor)          # tool results must be strings

# Name the model uses -> the Python function to run
available = {"calculate": calculate, "convert_units": convert_units}

# ---- 2. The descriptions the model sees -------------------------------------
tools = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a math expression exactly. Use for ANY arithmetic. "
                           "Supports + - * / **, sqrt, sin, cos, tan, atan2, radians, degrees, pi.",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string", "description": "e.g. '2 * (3 + 4)'"}},
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "convert_units",
            "description": "Convert a value from one unit to another. Supported pairs: "
                           "m/s <-> km/h, rad <-> deg, rad/s <-> deg/s.",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "number", "description": "The number to convert"},
                    "from_unit": {"type": "string", "enum": UNITS},
                    "to_unit": {"type": "string", "enum": UNITS},
                },
                "required": ["value", "from_unit", "to_unit"],
            },
        },
    },
]


messages = [{"role": "system", "content": "You are a robotics assistant. Use tools for all arithmetic "
                                          "and unit conversions. Reply in plain text; no LaTeX or markdown."}]

while True:
    user_input = input("You: ")
    if user_input.lower() in ("quit", "exit"):
        break
    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(model=MODEL, messages=messages, tools=tools)
    msg = response.choices[0].message

    steps = 0
    while msg.tool_calls and steps < 5:
        steps += 1
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ],
        })
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            print(f"  [step {steps}] {tc.function.name}({args})")
            result = available[tc.function.name](**args)
            print(f"  [step {steps}] -> {result}")
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
        response = client.chat.completions.create(model=MODEL, messages=messages, tools=tools)
        msg = response.choices[0].message

    print("Bot:", msg.content)
    messages.append({"role": "assistant", "content": msg.content or ""})
