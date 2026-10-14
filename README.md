# Robotics Assistant: a tool-using LLM agent from scratch

A command-line chatbot that remembers the conversation and calls Python tools to do exact maths and unit conversions. It's built directly on the OpenAI-compatible Chat Completions API, with no agent framework, so every step of the agent loop is visible in about 100 lines of code.

## What it does

- **Remembers the conversation.** The full message history is resent with every request, so follow-up questions like "what's that in deg/s?" work.
- **Uses tools instead of guessing.** LLMs are unreliable at precise arithmetic, so the model calls real Python functions:
  - `calculate`: evaluates a math expression (`+ - * / **`, `sqrt`, trig, `degrees`, `radians`, `pi`)
  - `convert_units`: converts m/s ↔ km/h, rad ↔ deg, rad/s ↔ deg/s
- **Chains several tool calls.** The model decides which tools to call and in what order, and the loop keeps running them until it has an answer (capped at 5 steps per turn).

## Example

```
You: My gyro reads 0.35 rad/s
  [step 1] convert_units({'from_unit': 'rad/s', 'to_unit': 'deg/s', 'value': 0.35})
  [step 1] -> 20.05352282957881
Bot: The gyro is reading about 20.05 degrees per second.
You: How far does it turn in 12.5 s, in degrees?
  [step 1] calculate({'expression': '20.05352282957881 * 12.5'})
  [step 1] -> 250.66903536973513
Bot: It will rotate about 250.67 degrees in 12.5 seconds.
You: What reading did I give you?
Bot: You originally gave a gyro reading of 0.35 radians per second.
```

The `[step]` lines show each tool the model requested and what it returned.

## How it works

```
while True:                         # chat loop: one pass per user message
    append user message to history
    call the model (with tool schemas)
    while the reply contains tool calls (max 5):   # agent loop
        run each requested Python function
        append the request and result to history
        call the model again
    print the final answer and add it to history
```

Each tool is described to the model with a JSON Schema. The `enum` lists of valid unit names stop the model from inventing unsupported units.

## Setup

Requires Python 3.9+ and a free [Groq](https://console.groq.com) API key.

```bash
python -m venv venv
source venv/bin/activate          # Windows: .\venv\Scripts\Activate.ps1
pip install openai
```

Set your API key as an environment variable (don't put it in the code):

```bash
export GROQ_API_KEY="your-key-here"        # Windows PowerShell: $env:GROQ_API_KEY="your-key-here"
```

## Run

```bash
python assistant.py
```

Type `quit` or `exit` to stop.

## Notes

- **Model:** uses `openai/gpt-oss-120b` on Groq. Free providers rotate their models, so if you get a "model not found" error, list the available ones with `client.models.list()` and update `MODEL`.
- **Other providers:** any OpenAI-compatible API works; change `base_url`, `MODEL` and the API key.
- **Adding a tool:** write the Python function, add its JSON Schema to `tools`, and register it in the `available` dict.
- **Security:** `calculate` uses `eval` with builtins disabled. That's acceptable for a local learning project but not safe for untrusted input; use a proper expression parser before exposing this to other people.
