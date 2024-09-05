from typing import List, Dict, Callable, Set
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

class State:
    def __init__(self, name: str):
        self.name = name
        self.transitions: Dict[str, State] = {}

    def add_transition(self, command: str, next_state: 'State'):
        self.transitions[command] = next_state

class StateMachine:
    def __init__(self, initial_state: State):
        self.current_state = initial_state
        self.states: Dict[str, State] = {initial_state.name: initial_state}

    def add_state(self, state: State):
        self.states[state.name] = state

    def transition(self, command: str) -> bool:
        if command in self.current_state.transitions:
            self.current_state = self.current_state.transitions[command]
            return True
        return False

    def get_available_commands(self) -> Set[str]:
        return set(self.current_state.transitions.keys())

class CommandCompleter(Completer):
    def __init__(self, cli):
        self.cli = cli

    def get_completions(self, document, complete_event):
        word_before_cursor = document.get_word_before_cursor(WORD=True)
        line = document.text

        if ' ' not in line:
            # Complete commands
            for command in self.cli.get_available_commands():
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
    intro = "Welcome to the CLI. Type 'help' or '?' to list commands."
    prompt = "(cli) "

    def __init__(self, state_machine: StateMachine):
        super().__init__()
        self.state_machine = state_machine
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

    def get_available_commands(self) -> Set[str]:
        return self.state_machine.get_available_commands()

    def cmdloop(self, intro=None):
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
            if not self.state_machine.transition(cmd):
                print(f"Command '{cmd}' not available in current state.")
                return
            try:
                func = getattr(self, 'do_' + cmd)
            except AttributeError:
                return self.default(line)
            return func(arg)

class AuthorListCLI(GenericCLI):
    def __init__(self):
        # Define states
        initial_state = State("initial")
        authors_added_state = State("authors_added")
        model_selected_state = State("model_selected")
        ready_state = State("ready")

        # Define transitions
        initial_state.add_transition("add_author", authors_added_state)
        initial_state.add_transition("select_model", model_selected_state)
        authors_added_state.add_transition("add_author", authors_added_state)
        authors_added_state.add_transition("select_model", ready_state)
        model_selected_state.add_transition("add_author", ready_state)
        model_selected_state.add_transition("select_model", model_selected_state)
        ready_state.add_transition("add_author", ready_state)
        ready_state.add_transition("select_model", ready_state)
        ready_state.add_transition("analyze_authors", ready_state)

        # Create state machine
        state_machine = StateMachine(initial_state)
        state_machine.add_state(authors_added_state)
        state_machine.add_state(model_selected_state)
        state_machine.add_state(ready_state)

        super().__init__(state_machine)
        self.authors: List[str] = []
        self.current_model: str = None
        self.available_models = ["model1", "model2", "model3"]  # Example models

    @command("add_author", "Add an author to the list")
    def do_add_author(self, arg):
        self.authors.append(arg)
        print(f"Added author: {arg}")

    @command("list_authors", "List all added authors")
    def do_list_authors(self, arg):
        for i, author in enumerate(self.authors, 1):
            print(f"{i}. {author}")

    @command("select_model", "Select an LLM model")
    def do_select_model(self, arg):
        if arg in self.available_models:
            self.current_model = arg
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