"""
This module implements a flexible Command-Line Interface (CLI) with a state machine.
It provides a framework for creating interactive command-line applications with
state-based behavior, command completion, and visualization capabilities.

Key components:
- State and StateMachine: Manage the application's state and transitions
- Command and command decorator: Define and register CLI commands
- GenericCLI: Base class for creating custom CLIs
- CommandCompleter: Provides command completion functionality
- Visualization: Methods to visualize the state machine

The module uses various libraries such as cmd, prompt_toolkit, and graphviz
for enhanced functionality and user experience.
"""

import time
import os

from typing import List, Dict, Callable, Set
from abc import ABC, abstractmethod

import cmd

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.shortcuts import CompleteStyle

import subprocess
from tabulate import tabulate

import functools
import logging
        
logging.basicConfig(level=logging.INFO)        

def visualize_after_command(visualize_func_name: str):
    """
    A decorator that calls a visualization function after executing a command.

    Args:
        visualize_func_name (str): The name of the visualization function to call.

    Returns:
        Callable: A decorated function that executes the original command and then
                  calls the specified visualization function.
    """
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
    """
    Represents a CLI command with its associated function, name, and description.

    Attributes:
        func (Callable): The function to be executed when the command is invoked.
        name (str): The name of the command.
        description (str): A brief description of what the command does.
    """
    def __init__(self, func: Callable, name: str, description: str):
        self.func = func
        self.name = name
        self.description = description

def command(name: str, description: str):
    """
    A decorator for registering CLI commands.

    Args:
        name (str): The name of the command.
        description (str): A brief description of what the command does.

    Returns:
        Callable: A decorator function that registers the command.
    """
    def decorator(func):
        func.command = Command(func, name, description)
        return func
    return decorator

class State:
    """
    Represents a state in the state machine.

    Attributes:
        name (str): The name of the state.
        transitions (Dict[str, State]): A dictionary of possible transitions from this state.
        _cli: The associated CLI instance.
        show (bool): Whether to show this state in visualizations.
    """
    def __init__(self, name: str, cli=None):
        self.name = name
        self.transitions: Dict[str, State] = {}
        self._cli = cli  # Store the CLI instance
        self.show = True
    

    def add_transition(self, command: str, next_state: 'State'):
        self.transitions[command] = next_state

class StateMachine:
    """
    Manages the states and transitions of the application.

    Attributes:
        current_state (State): The current state of the machine.
        states (Dict[str, State]): A dictionary of all states in the machine.
        last_transition: The last transition that occurred.
    """
    def __init__(self, initial_state: State):
        self.current_state = initial_state
        self.states: Dict[str, State] = {initial_state.name: initial_state}
        # self.last_transition = command
        self.last_transition = None

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
    """
    Provides command completion functionality for the CLI.

    This class is responsible for generating completion suggestions
    based on the current input and available commands.
    """
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
    """
    A command completer specifically for the GenericCLI.

    This class extends CommandCompleter to provide completions
    for the generic CLI implementation.
    """
    def get_command_specific_completions(self, line, word_before_cursor):
        # Generic CLI doesn't have any specific completions
        return []

class GenericCLI(cmd.Cmd):
    """
    A generic Command-Line Interface that integrates with a state machine.

    This class provides the base functionality for creating custom CLIs
    with state-based behavior, command completion, and visualization capabilities.

    Attributes:
        state_machine (StateMachine): The associated state machine.
        commands (Dict[str, Command]): A dictionary of available commands.
        command_completer (GenericCLICompleter): The command completer for this CLI.
        session (PromptSession): The prompt session for handling user input.
    """
    intro = "Welcome to the CLI. Type 'help' or '?' to list commands."
    prompt = "(cli) "

    def __init__(self, state_machine: StateMachine):
        super().__init__()
        self.state_machine = state_machine
        self.commands = self._register_commands()
        self.command_completer = GenericCLICompleter(self)
        self.session = PromptSession(completer=self.command_completer, complete_style=CompleteStyle.MULTI_COLUMN)
        self.refresh_commands()

    @property
    def dynamic_prompt(self):
        base_prompt = self.prompt.strip()[1:-1]  # Remove parentheses and whitespace
        return f"({base_prompt}:{self.state_machine.current_state.name}) "


    def _register_commands(self) -> Dict[str, Command]:
        """
        Registers all methods decorated with @command as CLI commands.

        Returns:
            Dict[str, Command]: A dictionary of registered commands.
        """
        commands = {}
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, 'command'):
                commands[attr.command.name] = attr.command
        return commands

    def refresh_commands(self):
        """
        Updates the list of available commands based on the current state.
        """
        self.available_commands = self.get_available_commands()
        logging.debug(f"Available commands: {', '.join(self.available_commands)}")

    def get_available_commands(self) -> Set[str]:
        """
        Retrieves the set of commands available in the current state.

        Returns:
            Set[str]: A set of available command names.
        """
        state_commands = self.state_machine.get_available_commands()
        always_available = {'help', 'exit'}
        return state_commands.union(always_available)
    
    def do_help(self, arg):
        if arg:
            if arg in self.commands:
                print(tabulate([[arg, self.commands[arg].description]], headers=["Command", "Description"]))
            else:
                print(f"No help available for '{arg}'")
        else:
            print("Available commands:")
            table_data = [[cmd_name, cmd.description] for cmd_name, cmd in self.commands.items() if cmd_name in self.available_commands]
            print(tabulate(table_data, headers=["Command", "Description"]))

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
            # print(f"Graph has been saved as '{file_path}.png'")
        
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

    def cmdloop(self, intro=None):
        """
        Repeatedly issues a prompt, accepts input, and dispatches to action methods.

        This method overrides the default cmd.Cmd.cmdloop to integrate with
        the state machine and provide enhanced functionality.

        Args:
            intro: The introduction message to display (optional).
        """
        self.preloop()
        if intro is not None:
            self.intro = intro
        if self.intro:
            self.stdout.write(str(self.intro)+"\n")
        stop = None
        while not stop:
            try:
                self.refresh_commands()  # Refresh commands before each prompt
                # line = self.session.prompt(self.prompt)
                #line = self.session.prompt(self.get_prompt())
                line = self.session.prompt(self.dynamic_prompt)
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
        """
        Interpret the argument as though it had been typed in response to the prompt.

        This method overrides the default cmd.Cmd.onecmd to integrate with
        the state machine and handle state transitions.

        Args:
            line (str): The command line to interpret.

        Returns:
            bool: A flag indicating whether the interpretation should stop.
        """
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
