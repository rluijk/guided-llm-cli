from typing import List, Dict, Callable, Set
from abc import ABC, abstractmethod
import time
import os
import logging
import cmd
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.shortcuts import CompleteStyle
from graphviz import Digraph
import subprocess

import functools

def visualize_after_command(visualize_func_name: str):
    def decorator(cmd_func: Callable):
        @functools.wraps(cmd_func)
        def wrapper(self, *args, **kwargs):
            result = cmd_func(self, *args, **kwargs)
            visualize_func = getattr(self, visualize_func_name)
            visualize_func(self.state_machine)
            return result
        return wrapper
    return decorator



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
    def __init__(self, name: str, cli=None):
        self.name = name
        self.transitions: Dict[str, State] = {}
        self._cli = cli  # Store the CLI instance

    def add_transition(self, command: str, next_state: 'State'):
        self.transitions[command] = next_state

class StateMachine:
    def __init__(self, initial_state: State):
        self.current_state = initial_state
        self.states: Dict[str, State] = {initial_state.name: initial_state}
        self.last_transition: Optional[str] = None
        
    def add_state(self, state: State):
        self.states[state.name] = state

    def transition(self, command: str) -> bool:
        if command in self.current_state.transitions:
            self.current_state = self.current_state.transitions[command]
            self.last_transition = command
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
            # print("Completing commands...")  # DEBUG
            for command in self.cli.get_available_commands():
                # print(f"Checking command: {command}")  # DEBUG
                if command.startswith(word_before_cursor):
                    # print(f"Yielding completion for: {command}")  # DEBUG
                    yield Completion(command, start_position=-len(word_before_cursor))
        else:
            # Command-specific completions
            yield from self.get_command_specific_completions(line, word_before_cursor)

    def get_command_specific_completions(self, line, word_before_cursor):
        # This method should be overridden by subclasses to provide command-specific completions
        return []

class GenericCLICompleter(CommandCompleter):
    def get_command_specific_completions(self, line, word_before_cursor):
        # Generic CLI doesn't have any specific completions
        return []

class AuthorListCLICompleter(CommandCompleter):
    def get_command_specific_completions(self, line, word_before_cursor):
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
        self.command_completer = GenericCLICompleter(self)
        self.session = PromptSession(completer=self.command_completer, complete_style=CompleteStyle.MULTI_COLUMN)
        self.refresh_commands()

    def _register_commands(self) -> Dict[str, Command]:
        commands = {}
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, 'command'):
                commands[attr.command.name] = attr.command
        return commands

    def refresh_commands(self):
        self.available_commands = self.get_available_commands()
        logging.debug(f"Available commands: {', '.join(self.available_commands)}")

    def get_available_commands(self) -> Set[str]:
        state_commands = self.state_machine.get_available_commands()
        always_available = {'help', 'exit'}
        return state_commands.union(always_available)


    def cmdloop(self, intro=None):
        self.preloop()
        if intro is not None:
            self.intro = intro
        if self.intro:
            self.stdout.write(str(self.intro)+"\n")
        stop = None
        while not stop:
            try:
                self.refresh_commands()  # Refresh commands before each prompt
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
            available_commands = self.get_available_commands()
            if cmd not in available_commands:
                print(f"Command '{cmd}' not available in current state.")
                return False
            
            # Check if the command is a transition
            if cmd in self.state_machine.current_state.transitions:
                self.state_machine.transition(cmd)
            
            # Execute the command
            try:
                func = getattr(self, 'do_' + cmd)
                return func(arg)
            except AttributeError:
                return self.default(line)

        
logging.basicConfig(level=logging.DEBUG)        
class AuthorListCLI(GenericCLI):
    def __init__(self):
        # Define states
        initial_state = State("initial", self)
        authors_added_state = State("authors_added", self)
        model_selected_state = State("model_selected", self)
        ready_state = State("ready", self)

        # Define transitions
        initial_state.add_transition("set_output_file", initial_state)
        initial_state.add_transition("list_authors", initial_state) 
        initial_state.add_transition("add_author", authors_added_state)
        initial_state.add_transition("select_model", model_selected_state)
        initial_state.add_transition("show_settings", initial_state)


        authors_added_state.add_transition("set_output_file", authors_added_state)
        authors_added_state.add_transition("list_authors", authors_added_state)
        authors_added_state.add_transition("show_settings", authors_added_state)
        authors_added_state.add_transition("add_author", authors_added_state)
        authors_added_state.add_transition("select_model", ready_state)


        ready_state.add_transition("set_output_file", ready_state)
        ready_state.add_transition("show_settings", ready_state)
        ready_state.add_transition("list_authors", ready_state)
        ready_state.add_transition("add_author", ready_state)
        ready_state.add_transition("select_model", ready_state)
        ready_state.add_transition("analyze_authors", ready_state)


        model_selected_state.add_transition("show_settings", model_selected_state)
        model_selected_state.add_transition("list_authors", model_selected_state)
        model_selected_state.add_transition("set_output_file", model_selected_state)
        model_selected_state.add_transition("add_author", ready_state)
        model_selected_state.add_transition("select_model", model_selected_state)
        
        # Create state machine
        state_machine = StateMachine(initial_state)
        state_machine.add_state(authors_added_state)
        state_machine.add_state(model_selected_state)
        state_machine.add_state(ready_state)

        super().__init__(state_machine)
        self.visualize_state_machine(state_machine)

        self.authors: List[str] = []
        self.current_model: str = None
        self.available_models = ["model1", "model2", "model3"]
        self.output_file = None

        self.command_completer = AuthorListCLICompleter(self)
        self.session = PromptSession(completer=self.command_completer, complete_style=CompleteStyle.MULTI_COLUMN)

    def visualize_state_machine(self, state_machine: StateMachine):
        output_folder = "state_machine_visualizations"
        os.makedirs(output_folder, exist_ok=True)

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"state_machine_{timestamp}"
        file_path = os.path.join(output_folder, filename)

        try:
            from graphviz import Digraph
            
            dot = Digraph(comment='State Machine')
            dot.attr(rankdir='LR', size='12,8')  # Increased size for better readability
            
            # Global graph attributes
            dot.attr('node', shape='ellipse', style='filled', fillcolor='white', fontname='Arial', fontsize='12')
            dot.attr('edge', fontname='Arial', fontsize='10', labelangle='45', labeldistance='2.0')

            # Add nodes (states)
            for state_name, state in state_machine.states.items():
                if state == state_machine.current_state:
                    dot.node(state_name, state_name, fillcolor='lightblue')
                else:
                    dot.node(state_name, state_name)

            # Add edges (transitions)
            for state_name, state in state_machine.states.items():
                for command, target_state in state.transitions.items():
                    edge_attrs = {
                        'label': command,
                        'fontsize': '10',
                        'fontcolor': 'darkgreen',
                    }
                    if (state == state_machine.current_state and 
                        command == state_machine.last_transition):
                        edge_attrs.update({
                            'color': 'red',
                            'penwidth': '2',
                            'fontcolor': 'red',
                        })
                    dot.edge(state_name, target_state.name, **edge_attrs)

            # Render the graph
            dot.render(file_path, format='png', cleanup=True)
            print(f"Graph has been saved as '{file_path}.png'")
        
        except (ImportError, subprocess.CalledProcessError):
            print("Graphviz not available. Falling back to text representation.")
            text_file_path = f"{file_path}.txt"
            with open(text_file_path, 'w') as f:
                f.write(self.get_text_representation(state_machine))
            print(f"Text representation has been saved as '{text_file_path}'")

    def get_text_representation(self,state_machine: StateMachine) -> str:
        output = "State Machine Representation:\n"
        output += "-----------------------------\n"
        for state_name, state in state_machine.states.items():
            output += f"State: {state_name}\n"
            if state == state_machine.current_state:
                output += "  (Current State)\n"
            output += "  Transitions:\n"
            for command, target_state in state.transitions.items():
                if command == state_machine.last_transition:
                    output += f"    - {command} -> {target_state.name} (Last Transition)\n"
                else:
                    output += f"    - {command} -> {target_state.name}\n"
            output += "\n"
        return output

    @visualize_after_command('visualize_state_machine')
    @command("set_output_file", "Set the output file for analysis results")
    def do_set_output_file(self, arg):
        self.output_file = arg
        print(f"Output file set to: {arg}")

    @visualize_after_command('visualize_state_machine') 
    @command("show_settings", "Show current settings")
    def do_show_settings(self, arg):
        print("Current settings:")
        print(f"  Authors: {self.authors}")
        print(f"  Model: {self.current_model}")
        print(f"  Output file: {self.output_file}")

    @command("add_author", "Add an author to the list")
    @visualize_after_command('visualize_state_machine')
    def do_add_author(self, arg):
        self.authors.append(arg)
        print(f"Added author: {arg}")

    @command("list_authors", "List all added authors")
    @visualize_after_command('visualize_state_machine')
    def do_list_authors(self, arg):
        if not self.authors:
            print("No authors added yet.")
        else:
            for i, author in enumerate(self.authors, 1):
                print(f"{i}. {author}")

    @command("select_model", "Select an LLM model")
    @visualize_after_command('visualize_state_machine')
    def do_select_model(self, arg):
        if arg in self.available_models:
            self.current_model = arg
            print(f"Selected model: {arg}")
        else:
            print(f"Invalid model. Available models: {', '.join(self.available_models)}")

    @command("analyze_authors", "Analyze the writing style of added authors")
    @visualize_after_command('visualize_state_machine')
    def do_analyze_authors(self, arg):
        print(f"Analyzing authors using model {self.current_model}...")

    @command("exit", "Exit the program")
    def do_exit(self, arg):
        print("Goodbye!")
        return True



if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    cli = AuthorListCLI()
    cli.cmdloop()