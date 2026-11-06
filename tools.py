import os
import shutil
import ssl
import subprocess
from html import unescape
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlencode, urlparse
from urllib.request import Request, urlopen

from subagent_creator import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    Subagent,
    SubagentCreator,
)

try:
    import certifi
except ImportError:
    certifi = None

MAX_CHARS = 10000
MAX_SEARCH_RESULTS = 5
MAX_SEARCH_OUTPUT_CHARS = 3500

class Tools():
    def __init__(self):
        """
        Initialize the Tools class.

        Inputs:
            None
        Output:
            A Tools instance ready to use the available file and command tools.
        """
        self.subagent_creator = SubagentCreator()
        self.subagents = {}

    def create_subagent(
        self,
        name,
        instructions,
        model=DEFAULT_MODEL,
        max_tokens=DEFAULT_MAX_TOKENS,
    ):
        """
        Create and store a specialist subagent configuration.

        Inputs:
            name: A non-empty name for the subagent.
            instructions: The specialist instructions for the subagent.
            model: The model used when the subagent is run.
            max_tokens: The maximum response tokens.
        Output:
            The created Subagent instance. Returns an error message when the
            configuration is invalid or a name is already registered.
        """
        if not isinstance(name, str) or not name.strip():
            return "Error: name must be a non-empty string"
        if name.strip() in self.subagents:
            return f"Error: subagent already exists: {name.strip()}"

        try:
            subagent = self.subagent_creator.create(
                name,
                instructions,
                model=model,
                max_tokens=max_tokens,
            )
        except ValueError as error:
            return f"Error creating subagent: {error}"

        self.subagents[subagent.name] = subagent
        return subagent

    def get_files_info(self, working_directory, directory=None):
        """
        Get the files and their details in a directory.

        Inputs:
            working_directory: The current working directory.
            directory: A relative directory inside the working directory or
                an absolute directory path (default: working_directory).
        Output:
            A list containing each item's name, size, directory status, and path.
            Returns an error message if the directory is outside the working
            directory.
        """
        if directory is None:
            directory = working_directory
        if os.path.isabs(directory):
            abs_directory = os.path.abspath(directory)
        else:
            abs_directory = os.path.abspath(os.path.join(working_directory, directory))

        if not os.path.isdir(abs_directory):
            return f"Error: directory not found: {directory}"

        final_response = ""

        try:
            contents = os.listdir(abs_directory)
        except OSError as error:
            return f"Error listing directory {directory}: {error}"
        for content in contents:
            content_path = os.path.join(abs_directory, content)
            is_dir = os.path.isdir(content_path)
            try:
                size = os.path.getsize(content_path)
            except OSError:
                size = 0
            final_response += f"- {content}: file_size={size}, is_dir={is_dir}, path={content_path}\n"

        return final_response

    def get_file_content(self, working_directory, file_path):
        """
        Read the contents of a file.

        Inputs:
            working_directory: The current working directory.
            file_path: The path of the file to read.
        Output:
            The file contents, truncated at MAX_CHARS(=10000) when necessary.
            Returns an error message if the path is outside the working
            directory or does not identify a file.
        """
        abs_working_directory = os.path.abspath(working_directory)
        abs_file_path = os.path.abspath(os.path.join(working_directory, file_path))
        if not abs_file_path.startswith(abs_working_directory):
            return f"Error: {file_path} not in the working directory"

        if not os.path.isfile(abs_file_path):
            return f"Error: {file_path} not an a file"

        try:
            with open(abs_file_path, "r") as file:
                content = file.read(MAX_CHARS)
                if len(content) >= MAX_CHARS:
                    content += f"\n...File: {file_path} truncated at {str(MAX_CHARS)} charactors"
            return content

        except Exception as e:
            return "Exception reading this file: {e}"

    def write_to_file(self, working_directory, file_path, content):
        """
        Write content to a file.

        Inputs:
            working_directory: The current working directory.
            file_path: The path of the file to write.
            content: The text to write to the file.
        Output:
            A success message containing the file path and character count.
            Returns an error message if the path is outside the working
            directory or the file cannot be written.
        """
        abs_working_directory = os.path.abspath(working_directory)
        abs_file_path = os.path.abspath(os.path.join(working_directory, file_path))
        if not abs_file_path.startswith(abs_working_directory):
            return f"Error: {file_path} not in the working directory"

        if not os.path.isfile(abs_file_path):
            parent_dir = os.path.dirname(abs_file_path)
            if not os.path.isdir(parent_dir):
                try:
                    os.makedirs(parent_dir)
                except Exception as e:
                    return f"Could not create the {parent_dir}: {e}"

        try:    
            with open(abs_file_path, "w") as file:
                file.write(content)
                return f"Successfully wrote to {file_path} ({len(content)}) characters."
        except Exception as e:
                return f"Exception while writing {file_path}: {e}"


    def command_excecutor(self, command):
        """
        Execute a shell command and collect its output.

        Inputs:
            command: The command and its arguments as a space-separated string.
        Output:
            STDOUT: Standard output from the command execution.
            STDERR: Standard error from the command execution.
            Process exited with code: Included when the command fails.
            No output produced: Returned when the command produces no output.
            Returns an exception message if command execution fails.
        """
        try:
            response = subprocess.run(command.split(), text=True, capture_output=True)

            output_string =  f"STDOUT:{response.stdout}\nSTDERR:{response.stderr}"
            if response.returncode != 0:
                output_string += f"Process exited with code: {response.returncode}"
            if response.stdout == "" and response.stderr == "":
                output_string = "No output produced"
            return output_string
        except Exception as e:
            return f"Exception occured while processing {command}"

    def run_python_files(self, working_directory:str, file_path:str, args=[]):
        """
        Run a Python file.

        Inputs:
            working_directory: The current working directory.
            file_path: The path of the Python file to run.
            args: Any arguments to pass to the Python script (default=[]).
        Output:
            STDOUT: Standard output from the file execution.
            STDERR: Standard error from the file execution.
            No output produced: Returned when the file produces no output.
            Process exited with code: Included when execution fails.
            Returns an error message when the file is invalid or execution
            fails.
        """
        
        abs_working_directory = os.path.abspath(working_directory)
        abs_file_path = os.path.abspath(os.path.join(working_directory, file_path))
        if not abs_file_path.startswith(abs_working_directory):
            return f"Error: {file_path} not in the working directory"
        if not os.path.isfile(abs_file_path):
            return f"Error: {file_path} is not a file"
        if not file_path.endswith(".py"):
            return f"Error: {file_path} is not a python file"

        try:
            if args == []:
                response = subprocess.run(
            ["python", abs_file_path], text=True, capture_output=True, timeout=30, cwd=abs_working_directory
        )
            else:
                response = subprocess.run(
                            ["python", abs_file_path] + args, text=True, capture_output=True, timeout=30, cwd=abs_working_directory
                        )

            output_string =  f"STDOUT:{response.stdout}\nSTDERR:{response.stderr}"

            if response.returncode != 0:
                output_string += f"Process exited with code: {response.returncode}"
            if response.stdout == "" and response.stderr == "":
                output_string = "No output produced"
            return output_string
        except Exception as e:
            return f"Error excecuting {file_path}, {e}"

    def search_tool(self, search_string):
        """
        Search the internet for a string using DuckDuckGo.

        Inputs:
            search_string: The terms to search for.
        Output:
            A formatted list of search results containing each result's title,
            URL, and description. Returns an error message if the query is
            empty or the search request fails.
        """
        if not isinstance(search_string, str) or not search_string.strip():
            return "Error: search_string must be a non-empty string"

        class SearchResultsParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.results = []
                self._current_result = None
                self._capture_title = False
                self._capture_snippet = False

            def handle_starttag(self, tag, attrs):
                attributes = dict(attrs)
                classes = attributes.get("class", "").split()

                if tag == "a" and "result-link" in classes:
                    self._current_result = {
                        "title": "",
                        "url": attributes.get("href", ""),
                        "snippet": "",
                    }
                    self._capture_title = True
                elif "result-snippet" in classes:
                    self._capture_snippet = True

            def handle_data(self, data):
                if self._current_result is None:
                    return
                if self._capture_title:
                    self._current_result["title"] += data
                elif self._capture_snippet:
                    self._current_result["snippet"] += data

            def handle_endtag(self, tag):
                if self._capture_title and tag == "a":
                    self._capture_title = False
                elif self._capture_snippet and tag == "td":
                    self.results.append(self._current_result)
                    self._current_result = None
                    self._capture_snippet = False

        query = urlencode({"q": search_string.strip()})
        request = Request(
            f"https://lite.duckduckgo.com/lite/?{query}",
            headers={"User-Agent": "Mozilla/5.0"},
        )

        try:
            with urlopen(request, timeout=15) as response:
                html = response.read().decode("utf-8", errors="replace")
        except Exception as error:
            return f"Error searching the internet: {error}"

        parser = SearchResultsParser()
        parser.feed(html)
        if not parser.results:
            return f"No search results found for: {search_string.strip()}"

        output = []
        for index, result in enumerate(
            parser.results[:MAX_SEARCH_RESULTS], start=1
        ):
            url = result["url"]
            parsed_url = urlparse(url)
            if parsed_url.netloc.endswith("duckduckgo.com"):
                redirect_url = parse_qs(parsed_url.query).get("uddg", [])
                if redirect_url:
                    url = unescape(unquote(redirect_url[0]))

            output.append(
                f"{index}. {result['title'].strip()}\n"
                f"   URL: {url}\n"
                f"   {result['snippet'].strip()}"
            )
        return "\n".join(output)[:MAX_SEARCH_OUTPUT_CHARS]

    def url_reader(self, url):
        """
        Read the HTML source of a website.

        Inputs:
            url: An HTTP or HTTPS URL to fetch.
        Output:
            The webpage's HTML source, truncated at MAX_CHARS when necessary.
            Returns an error message for invalid URLs or failed requests.
        """
        if not isinstance(url, str) or not url.strip():
            return "Error: url must be a non-empty string"

        parsed_url = urlparse(url.strip())
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            return "Error: url must be a valid HTTP or HTTPS URL"

        request = Request(
            url.strip(),
            headers={"User-Agent": "Mozilla/5.0 (compatible; CodingAgent/1.0)"},
        )

        try:
            ssl_context = ssl.create_default_context(
                cafile=certifi.where() if certifi else None
            )
            with urlopen(request, timeout=15, context=ssl_context) as response:
                content = response.read(MAX_CHARS + 1).decode(
                    response.headers.get_content_charset() or "utf-8",
                    errors="replace",
                )
        except Exception as error:
            return f"Error reading URL {url.strip()}: {error}"

        if len(content) > MAX_CHARS:
            return (
                content[:MAX_CHARS]
                + f"\n...URL content truncated at {MAX_CHARS} characters"
            )
        return content

    def open_application(self, application, args=None):
        """
        Open a desktop application from any local filesystem location.

        Inputs:
            application: An executable name or absolute path to an application.
            args: Optional command-line arguments for the application.
        Output:
            A success message containing the process ID, or an error message
            when the application cannot be started.
        """
        if not isinstance(application, str) or not application.strip():
            return "Error: application must be a non-empty string"
        if args is None:
            args = []
        if not isinstance(args, list) or not all(
            isinstance(argument, str) for argument in args
        ):
            return "Error: args must be a list of strings"

        application = application.strip().strip('"')
        executable = self.find_application(application, return_error=False)

        if executable is None:
            return (
                f"Error: application not found: {application}. "
                "Provide its executable name or full path."
            )

        try:
            process = subprocess.Popen(
                [executable, *args],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as error:
            return f"Error opening application {application}: {error}"
        return f"Successfully opened {application} (process_id={process.pid})"

    def find_application(self, application, return_error=True):
        """
        Find an installed application executable.

        Inputs:
            application: An executable name, application name, or full path.
            return_error: Whether to return a formatted error instead of None.
        Output:
            The absolute executable path, or an error message/None when not
            found.
        """
        if not isinstance(application, str) or not application.strip():
            return "Error: application must be a non-empty string" if return_error else None

        application = application.strip().strip('"')
        executable = shutil.which(application)
        if executable is None and os.path.isfile(application):
            executable = os.path.abspath(application)

        if executable is None and os.name == "nt":
            executable_names = [
                application if application.lower().endswith(".exe")
                else f"{application}.exe"
            ]
            if application.lower() in {"android studio", "studio"}:
                executable_names = ["studio64.exe", "studio.exe"]

            roots = [
                os.environ.get("ProgramFiles"),
                os.environ.get("ProgramFiles(x86)"),
                os.environ.get("LOCALAPPDATA"),
            ]
            scanned_directories = 0
            for root in filter(None, roots):
                root_depth = root.rstrip(os.sep).count(os.sep)
                for current_root, directories, files in os.walk(root):
                    scanned_directories += 1
                    if (
                        scanned_directories > 5000
                        or current_root.rstrip(os.sep).count(os.sep) - root_depth >= 5
                    ):
                        directories[:] = []
                    if scanned_directories > 5000:
                        break
                    for executable_name in executable_names:
                        if executable_name.lower() in {
                            file.lower() for file in files
                        }:
                            executable = os.path.join(current_root, executable_name)
                            break
                    if executable is not None:
                        break
                if executable is not None:
                    break

        if executable is None and return_error:
            return f"Error: application not found: {application}"
        return executable

    def close_application(self, process_name):
        """
        Close desktop application processes by executable name.

        Inputs:
            process_name: The executable name, such as notepad.exe.
        Output:
            A success message when the process-close request is accepted, or
            an error message when the process name is invalid or unavailable.
        """
        if not isinstance(process_name, str) or not process_name.strip():
            return "Error: process_name must be a non-empty string"
        if os.name != "nt":
            return "Error: close_application is supported on Windows only"

        process_name = process_name.strip()
        if any(character in process_name for character in ('"', "/", "\\", ";")):
            return "Error: process_name must be an executable name"

        try:
            response = subprocess.run(
                ["taskkill", "/IM", process_name, "/T"],
                text=True,
                capture_output=True,
                timeout=15,
            )
        except OSError as error:
            return f"Error closing application {process_name}: {error}"

        output = (response.stdout + response.stderr).strip()
        if response.returncode != 0:
            return f"Error closing application {process_name}: {output}"
        return f"Successfully requested closure of {process_name}: {output}"