import os


class Tools():
    def __init__(self):
        pass

    def get_files_info(self, working_directory, directory=None):
        """
        Get the files and their details in a directory
        """
        abs_working_directory = os.path.abspath(working_directory)

        if directory == None:
            directory = "."
        abs_directory = os.path.abspath(directory)

        if not abs_directory.startswith(abs_working_directory):
            return f"Error: {directory} is not directory"

        final_response = ""

        contents = os.listdir(abs_directory)
        for content in contents:
            content_path = os.path.join(abs_directory, content)
            is_dir = os.path.isdir(content_path)
            size = os.path.getsize(content_path)
            final_response += f"{content}: file_size={size}, is_dir={is_dir}, path={content_path}"

        return final_response

    
    def coderunner(self, file):
        """
        Python code excecuter
        """
        pass

    def write_to_file(self, string):
        """
        Write and save python codes in brain
        """
        pass

    def command_excecutor(self, command):
        """
        Excecute commands
        """
        pass

    