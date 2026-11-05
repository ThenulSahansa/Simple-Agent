# Simple Agent

Simple Agent is an interactive Python coding assistant powered by the Groq API. It can inspect and edit files, run Python programs and shell commands, search the web, read web pages, and manage desktop applications.

## Features

- Interactive terminal chat with Rich-formatted output
- File and directory inspection
- File creation and editing
- Python script execution
- Shell command execution
- DuckDuckGo web search and URL reading
- Application discovery and launching
- Windows application closing support
- Automatic recovery from malformed tool-call arguments

## Requirements

- Python 3.9 or newer
- A [Groq API key](https://console.groq.com/keys)

## Installation

Clone the repository and install the dependencies:

```bash
git clone https://github.com/ThenulSahansa/Simple-Agent.git
cd Simple-Agent
python -m venv .venv
```

Activate the virtual environment:

```bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install the required packages:

```bash
python -m pip install groq python-dotenv rich certifi
```

## Configuration

Create a `.env` file in the project directory and add your API key:

```dotenv
GROQ_API_KEY=your_groq_api_key
```

The application uses the `openai/gpt-oss-20b` model by default.

## Usage

Start the agent with:

```bash
python agent.py
```

Enter requests at the prompt, such as:

```text
List the Python files in this project.
Read agent.py and explain how tool calls work.
Create a test script and run it.
```

Type `exit` or `quit` to stop the agent.

The agent passes the current working directory to its tools. Start it from the project directory when working on this repository.

## Project structure

```text
.
├── agent.py   # CLI loop, model interaction, and tool-call orchestration
├── tools.py   # File, command, web, and application tools
└── .env       # Local API configuration; do not commit
```

## Security notes

The agent can execute shell commands and launch applications. Only run it in a trusted environment and review requests before allowing destructive or sensitive operations.

Keep `.env` private and never commit API keys or other credentials.
