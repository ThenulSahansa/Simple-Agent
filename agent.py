import json
import os
from groq import BadRequestError, Groq, RateLimitError
import dotenv
from tools import Tools
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()

tool_schema = [
    {
        "type": "function",
        "function": {
            "name": "get_files_info",
            "description": (
                "List files and directories. Relative paths use the working "
                "directory; absolute paths can inspect other local folders."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "working_directory": {
                        "type": "string",
                        "description": "The current working directory.",
                    },
                    "directory": {
                        "type": "string",
                        "description": (
                            "A relative or absolute directory path. Defaults "
                            "to the working directory."
                        ),
                    },
                },
                "required": ["working_directory"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_content",
            "description": "Read the contents of a file in the working directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "working_directory": {
                        "type": "string",
                        "description": "The current working directory.",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "The path of the file to read.",
                    },
                },
                "required": ["working_directory", "file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_to_file",
            "description": "Create or overwrite a file with the supplied content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "working_directory": {
                        "type": "string",
                        "description": "The current working directory.",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "The path of the file to write.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The text to write to the file.",
                    },
                },
                "required": ["working_directory", "file_path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "command_excecutor",
            "description": (
                "Execute a command and return its standard output, standard "
                "error, and exit status."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The command to execute.",
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python_files",
            "description": (
                "Run a Python file from the working directory with optional "
                "string arguments."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "working_directory": {
                        "type": "string",
                        "description": "The current working directory.",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "The path of the Python file to run.",
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional arguments to pass to the Python script."
                        ),
                        "default": [],
                    },
                },
                "required": ["working_directory", "file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_tool",
            "description": "Search the internet for a query and return relevant results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_string": {
                        "type": "string",
                        "description": "The terms to search for.",
                    },
                },
                "required": ["search_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "url_reader",
            "description": "Fetch and read the HTML source of a webpage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The HTTP or HTTPS URL to read.",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Open a desktop application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "application": {
                        "type": "string",
                        "description": (
                            "An executable name or full path anywhere on the "
                            "computer; it is not limited to the project folder."
                        ),
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional command-line arguments.",
                        "default": [],
                    },
                },
                "required": ["application"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_application",
            "description": (
                "Find the executable path of an installed desktop application "
                "outside the project directory."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "application": {
                        "type": "string",
                        "description": "Application name, executable, or full path.",
                    },
                },
                "required": ["application"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_application",
            "description": "Close desktop application processes by executable name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "process_name": {
                        "type": "string",
                        "description": "The executable name, such as notepad.exe.",
                    },
                },
                "required": ["process_name"],
            },
        },
    },
]

tools = Tools()
MODEL = "openai/gpt-oss-20b"
MAX_TOOL_ROUNDS = 15
MAX_OUTPUT_TOKENS = 1024

SYSTEM_PROMPT = """
You are an AI coding agent. Inspect relevant files, make focused changes, and
validate them. Use the working directory for file operations and never claim
success unless a tool confirms it.

Available tools:
Use get_files_info with absolute paths when inspecting folders outside the
project. Use find_application before open_application when the executable path
is unknown. Use search_tool for web searches and url_reader for webpage contents.
Use valid JSON tool arguments with escaped strings. Explain errors clearly.
"""

def normalize_tool_name(name):
    return name.split("<|", 1)[0]

def execute_tool_call(tool_call):
    name = normalize_tool_name(tool_call.function.name or "")
    try:
        arguments = json.loads(tool_call.function.arguments or "{}")
    except json.JSONDecodeError as error:
        return f"Error: invalid arguments for tool {name}: {error}"

    if not isinstance(arguments, dict):
        return f"Error: arguments for tool {name} must be a JSON object."

    available_tools = {
        "get_files_info": tools.get_files_info,
        "find_application": tools.find_application,
        "get_file_content": tools.get_file_content,
        "write_to_file": tools.write_to_file,
        "command_excecutor": tools.command_excecutor,
        "run_python_files": tools.run_python_files,
        "search_tool": tools.search_tool,
        "url_reader": tools.url_reader,
        "open_application": tools.open_application,
        "close_application": tools.close_application,
    }

    selected_tool = available_tools.get(name)
    if selected_tool is None:
        return f"Error: Tool {name} not found."

    display_arguments = {
        key: value
        for key, value in arguments.items()
        if key != "content"
    }
    if "content" in arguments:
        display_arguments["content"] = (
            f"<{len(str(arguments['content']))} characters>"
        )
    console.print(
        f"[grey58]Tool: [bold]{name}[/] "
        f"Arguments: {display_arguments}[/]"
    )
    if name == "command_excecutor":
        console.print(
            f"[grey58]Processing command: "
            f"[bold]{arguments.get('command', '')}[/][/]"
        )

    try:
        with console.status(
            f"[grey58]Running tool [bold]{name}[/]...[/]",
            spinner="dots",
        ):
            result = selected_tool(**arguments)
    except TypeError as error:
        return f"Error: invalid arguments for tool {name}: {error}"
    except Exception as error:
        return f"Error while running tool {name}: {error}"

    return str(result)

def assistant_message(response_message):
    message = {
        "role": "assistant",
        "content": response_message.content or "",
    }
    if response_message.tool_calls:
        message["tool_calls"] = [
            {
                "id": tool_call.id,
                "type": "function",
                "function": {
                    "name": normalize_tool_name(tool_call.function.name),
                    "arguments": tool_call.function.arguments or "{}",
                },
            }
            for tool_call in response_message.tool_calls
        ]
    return message

def request_completion(
    client,
    messages,
    model,
    include_tools=True,
    response_format=None,
    status_text="Thinking: preparing a response...",
):
    request = {
        "model": model,
        "messages": messages,
        "max_tokens": MAX_OUTPUT_TOKENS,
    }
    if include_tools:
        request["tools"] = tool_schema
        request["tool_choice"] = "auto"
    if response_format is not None:
        request["response_format"] = response_format
    with console.status(
        f"[grey58]{status_text}[/]",
        spinner="dots",
    ):
        return client.chat.completions.create(**request)

def recover_tool_call(client, messages, model):
    recovery_messages = messages + [
        {
            "role": "user",
            "content": (
                "The previous tool call was malformed. Return exactly one JSON "
                "object with this shape and no markdown: "
                '{"name":"tool_name","arguments":{...}}. '
                "Use one of the available tools and valid JSON string values. "
                "Do not explain anything."
            ),
        }
    ]
    response = request_completion(
        client,
        recovery_messages,
        model,
        include_tools=False,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or ""
    try:
        recovered_call = json.loads(content)
    except json.JSONDecodeError as error:
        return f"Error: recovery response was not valid JSON: {error}"

    if (
        not isinstance(recovered_call, dict)
        or not isinstance(recovered_call.get("name"), str)
        or not isinstance(recovered_call.get("arguments"), dict)
    ):
        return "Error: recovery response did not contain a valid tool action."

    return type(
        "RecoveredToolCall",
        (),
        {
            "id": "recovered-tool-call",
            "function": type(
                "RecoveredFunction",
                (),
                {
                    "name": recovered_call["name"],
                    "arguments": json.dumps(recovered_call["arguments"]),
                },
            )()
        },
    )()

def run_agent(client, user_message, working_directory, model=MODEL):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Working directory: {working_directory}\n\n"
                f"User request: {user_message}"
            ),
        },
    ]

    for round_number in range(MAX_TOOL_ROUNDS):
        try:
            response = request_completion(
                client,
                messages,
                model,
                status_text=(
                    f"Thinking: analyzing request "
                    f"(step {round_number + 1}/{MAX_TOOL_ROUNDS})..."
                ),
            )
        except BadRequestError as error:
            error_text = str(error)
            if "parse tool call arguments" not in error_text:
                raise

            recovered_call = recover_tool_call(client, messages, model)
            if isinstance(recovered_call, str):
                return recovered_call
            messages.append(
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": recovered_call.id,
                            "type": "function",
                            "function": {
                                "name": normalize_tool_name(
                                    recovered_call.function.name
                                ),
                                "arguments": recovered_call.function.arguments,
                            },
                        }
                    ],
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": recovered_call.id,
                    "name": normalize_tool_name(recovered_call.function.name),
                    "content": execute_tool_call(recovered_call),
                }
            )
            continue

        response_message = response.choices[0].message
        messages.append(assistant_message(response_message))

        if not response_message.tool_calls:
            return response_message.content or "The model returned an empty response."

        console.print(
            "[grey58]Thinking: selecting "
            f"{len(response_message.tool_calls)} tool(s)...[/]"
        )

        for tool_call in response_message.tool_calls:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": normalize_tool_name(tool_call.function.name),
                    "content": execute_tool_call(tool_call),
                }
            )

    return "Error: maximum tool-call rounds reached before a final response."

def main():
    dotenv.load_dotenv()
    client = Groq()

    console.print(
        Panel(
            "[bold green]AI coding agent ready[/]\n"
            "Type [bold]exit[/] or [bold]quit[/] to stop.",
            title="Agent",
            border_style="green",
        )
    )
    while True:
        try:
            user_message = console.input("\n[bold blue]You:[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[bold green]Goodbye.[/]")
            break

        if user_message.lower() in {"exit", "quit"}:
            console.print("[bold green]Goodbye.[/]")
            break
        if not user_message:
            continue

        try:
            answer = run_agent(client, user_message, os.getcwd())
            console.print(
                Panel(
                    Markdown(answer),
                    title="Agent",
                    border_style="cyan",
                )
            )
        except RateLimitError as error:
            headers = error.response.headers
            console.print(
                Panel(
                    "Rate limit hit.\n"
                    f"Retry-After: {headers.get('retry-after', 'unknown')}",
                    title="Rate limit",
                    border_style="yellow",
                )
            )
        except Exception as error:
            console.print(
                Panel(
                    f"{error}",
                    title="Agent error",
                    border_style="red",
                )
            )
        
if __name__ == "__main__":
    main()