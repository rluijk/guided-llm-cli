from typing import List, Dict, Callable
from abc import ABC, abstractmethod
import cmd
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.shortcuts import CompleteStyle

class Command:
    def __init__(self, func: Callable, name: str, description: str):
        self.func = func
        self.name = name
        self.description = description

def command(name: str, description: str):
    def decorator(func):
        func.command = Command(func, name, description)
        return func
    return decorator

class CLIState(ABC):
    @abstractmethod
    def validate_command(self, command: str) -> bool:
        pass

class AuthorListState(CLIState):
    def __init__(self):
        self.model_selected = False
        self.authors_added = False

    def validate_command(self, command: str) -> bool:
        if command == "analyze_authors" and not self.authors_added:
            print("Please add authors first using the 'add_author' command.")
            return False
        if command == "analyze_authors" and not self.model_selected:
            print("Please select a model first using the 'select_model' command.")
            return False
        return True

class CommandCompleter(Completer):
    def __init__(self, cli):
        self.cli = cli

    def get_completions(self, document, complete_event):
        word_before_cursor = document.get_word_before_cursor(WORD=True)
        line = document.text

        if ' ' not in line:
            # Complete commands
            for command in self.cli.commands:
                if command.startswith(word_before_cursor):
                    yield Completion(command, start_position=-len(word_before_cursor))
        else:
            # Command-specific completions
            command = line.split()[0]
            if command == 'select_model':
                for model in self.cli.available_models:
                    if model.startswith(word_before_cursor):
                        yield Completion(model, start_position=-len(word_before_cursor))

class GenericCLI(cmd.Cmd):
    def __init__(self, state: CLIState):
        super().__init__()
        self.state = state
        self.commands = self._register_commands()
        self.command_completer = CommandCompleter(self)
        self.session = PromptSession(completer=self.command_completer, complete_style=CompleteStyle.MULTI_COLUMN)

    def _register_commands(self) -> Dict[str, Command]:
        commands = {}
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, 'command'):
                commands[attr.command.name] = attr.command
        return commands

    def cmdloop(self, intro=None):
        """Repeatedly issue a prompt, accept input, parse an initial prefix
        off the received input, and dispatch to action methods, passing them
        the remainder of the line as argument.
        """
        self.preloop()
        if intro is not None:
            self.intro = intro
        if self.intro:
            self.stdout.write(str(self.intro)+"\n")
        stop = None
        while not stop:
            try:
                line = self.session.prompt(self.prompt)
                line = self.precmd(line)
                stop = self.onecmd(line)
                stop = self.postcmd(stop, line)
            except KeyboardInterrupt:
                print("^C")
            except EOFError:
                print("^D")
                break
        self.postloop()

    def onecmd(self, line):
        cmd, arg, line = self.parseline(line)
        if not line:
            return self.emptyline()
        if cmd is None:
            return self.default(line)
        self.lastcmd = line
        if cmd == '':
            return self.default(line)
        else:
            if not self.state.validate_command(cmd):
                return
            try:
                func = getattr(self, 'do_' + cmd)
            except AttributeError:
                return self.default(line)
            return func(arg)

class AuthorListCLI(GenericCLI):
    def __init__(self):
        self.authors: List[str] = []
        self.current_model: str = None
        self.available_models = ["model1", "model2", "model3"]  # Example models
        super().__init__(AuthorListState())

    @command("add_author", "Add an author to the list")
    def do_add_author(self, arg):
        self.authors.append(arg)
        self.state.authors_added = True
        print(f"Added author: {arg}")

    @command("list_authors", "List all added authors")
    def do_list_authors(self, arg):
        for i, author in enumerate(self.authors, 1):
            print(f"{i}. {author}")

    @command("select_model", "Select an LLM model")
    def do_select_model(self, arg):
        if arg in self.available_models:
            self.current_model = arg
            self.state.model_selected = True
            print(f"Selected model: {arg}")
        else:
            print(f"Invalid model. Available models: {', '.join(self.available_models)}")

    @command("analyze_authors", "Analyze the writing style of added authors")
    def do_analyze_authors(self, arg):
        print(f"Analyzing authors using model {self.current_model}...")

    @command("exit", "Exit the program")
    def do_exit(self, arg):
        print("Goodbye!")
        return True

# Usage
if __name__ == "__main__":
    AuthorListCLI().cmdloop()