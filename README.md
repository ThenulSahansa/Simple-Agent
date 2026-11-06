# Simple Agent

Simple Agent is a terminal-based AI coding assistant powered by the Groq API. It can inspect and edit files in the current working directory, run Python files and shell commands, search the web, read web pages, and manage desktop applications.

## Features

- Interactive Rich-powered terminal interface
- Groq tool calling with automatic recovery for malformed tool arguments
- File listing, file reading, and file writing
- Shell command execution and Python script execution
- DuckDuckGo search and HTTP/HTTPS page reading
- Application discovery, launching, and Windows-only process closing
- Configurable tool-call and response-token limits in `agent.py`
- Reusable specialist subagents through `subagent_creator.py`
- Pre-execution plans saved under a request-specific `Brain` folder

## Requirements

- Python 3.9 or newer
- A [Groq API key](https://console.groq.com/keys)

## Installation

Clone the repository, create a virtual environment, and install the dependencies:

```bash
git clone https://github.com/ThenulSahansa/Simple-Agent.git
cd Simple-Agent
python -m venv .venv
source .venv/bin/activate
pip install groq python-dotenv rich certifi
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## Configuration

Create a `.env` file in the project root and add your API key:

```dotenv
GROQ_API_KEY=your_groq_api_key
```

The application loads this file automatically with `python-dotenv`. Do not commit `.env` or share your API key.

## Creating a subagent

Use `SubagentCreator` to configure a specialist with its own instructions while
reusing the Groq client:

```python
from subagent_creator import SubagentCreator

creator = SubagentCreator()
reviewer = creator.create(
    "code reviewer",
    "Review code for correctness, maintainability, and security.",
)
answer = reviewer.run(client, "Review the latest changes.", context=diff)
```

Pass the existing `tool_schema` to `SubagentCreator(tools=tool_schema)` when a
subagent should be allowed to call the agent's tools.

## Usage

Start the agent from the project directory:

```bash
python agent.py
```

Enter requests at the prompt. Type `exit` or `quit` to end the session.

The agent receives the current working directory as context, so file paths in requests should normally be relative to the directory where `agent.py` is started.

Before executing tools, the agent creates a Markdown plan based on the
`MAX_TOOL_ROUNDS` budget, available tools, and recommended subagent count. The
plan is saved as `Brain/<request>/Plan.MD` (with a timestamp suffix if the
same request has already been run), then supplied to the execution agent.

## Available tools

| Tool | Purpose |
| --- | --- |
| `get_files_info` | List files and directories |
| `get_file_content` | Read a file |
| `write_to_file` | Create or overwrite a file |
| `command_excecutor` | Run a shell command |
| `run_python_files` | Run a Python file with optional arguments |
| `search_tool` | Search DuckDuckGo |
| `url_reader` | Read an HTTP or HTTPS page |
| `find_application` | Locate an installed executable |
| `open_application` | Launch an application |
| `close_application` | Request process closure on Windows |
| `create_subagent` | Create and store a specialist subagent configuration |

## Safety notes

The agent can write files, execute commands, and launch applications. Review tool requests and generated changes before relying on them, and run the agent only in a workspace where those capabilities are appropriate. The `.env` file is ignored by Git and should remain private.

## Project layout

```text
.
├── agent.py   # CLI, Groq client, prompts, and tool-call loop
└── tools.py   # Local file, command, web, and application tools
```
