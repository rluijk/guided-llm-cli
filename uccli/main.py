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

import os

import time
from datetime import datetime

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
        
import json
from typing import Dict, List, Any
from dataclasses import dataclass, field, asdict

from .agent_communication import AgentCommunicator, DummyAgentCommunicator

logging.basicConfig(level=logging.INFO)        

LEGEND_ITEMS = {
    '🔵': 'Input Required',
    '⭕': 'Cancellable',
    'Dashed': 'Cancellable',
    'Red': 'Last Transition'
}

""" DECORATORS """
import inspect

def get_decorators(func):
    decorators = []
    # Get the source code of the function
    source = inspect.getsource(func)
    # Split the source into lines
    lines = source.split('\n')
    # Iterate through lines preceding the function definition
    for line in lines:
        line = line.strip()
        if line.startswith('def '):
            break
        if line.startswith('@'):
            # Extract decorator name (remove '@' and any arguments)
            decorator = line[1:].split('(')[0]
            decorators.append(decorator)
    return decorators


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

def cancellable_command(prompt="Are you sure you want to proceed? (y/n): "):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, arg):
            confirm = input(prompt)
            if confirm.lower() != 'y':
                print("Operation cancelled.")
                return "CANCEL_TRANSITION"
            result = func(self, arg)
            return result if result is not None else "CONTINUE"
        return wrapper
    return decorator

def input_required_command(prompt=None, error_message=None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, arg):
            if prompt and not arg:
                user_input = input(prompt)
                if not user_input:
                    print(error_message or "Input required. Command cancelled.")
                    return "CANCEL_TRANSITION"
                arg = user_input
            result = func(self, arg)
            return result if result is not None else "CONTINUE"
        return wrapper
    return decorator


""" CLASSES """

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
        self.app = None

    def add_state(self, state: State):
        self.states[state.name] = state

    def change_state(self, new_state):
        if new_state in self.states:
            self.current_state = self.states[new_state]
            self.on_state_changed()  # Call this after every state change

    def on_state_changed(self):
        """Automatically save the state after every state change."""
        if self.app and self.app.current_storage:
            # Update the session with the new current state
            self.app.current_storage.update_data("current_state", self.current_state.name)
            
            # Automatically log the command if available
            if self.last_transition:
                self.app.current_storage.add_command_result(self.last_transition, {"state": self.current_state.name})
            
            # Save the current session (no need to pass current_storage)
            self.app.storage_manager.save_current_session()
            
            logging.info(f"State '{self.current_state.name}' and command '{self.last_transition}' saved to session.")


    def transition(self, command: str) -> bool:
        if command in self.current_state.transitions:
            # Update the current state
            self.current_state = self.current_state.transitions[command]
            
            # Record the last transition command
            self.last_transition = command  # Ensure last_transition is updated
            
            # Trigger state save after transition
            self.on_state_changed()  # Save state and command
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

    @property
    def implementation_name(self):
        return self.__class__.__name__

    def __init__(self, state_machine: StateMachine, agent_communicator: AgentCommunicator = None):
        super().__init__()
        self.state_machine = state_machine
        self.agent_communicator = agent_communicator or DummyAgentCommunicator()
        self.commands = self._register_commands()
        self.command_completer = GenericCLICompleter(self)
        self.session = PromptSession(completer=self.command_completer, complete_style=CompleteStyle.MULTI_COLUMN)
        self.refresh_commands()

        self.storage_manager = StorageManager()
        self.current_storage = None

    @command("new_session", "Create a new working session")
    def do_new_session(self, arg):
        """Create a new working session. Usage: new_session <session_name>"""
        if not arg:
            print("Please provide a name for the new session.")
            return
        try:
            self.current_storage = self.storage_manager.create_session(arg)
            print(f"New session '{arg}' created and activated.")
        except ValueError as e:
            print(f"Error: {e}")

    @command("load_session", "Load an existing working session")
    def do_load_session(self, arg):
        """Load an existing working session. Usage: load_session <session_name>"""
        if not arg:
            print("Please provide the name of the session to load.")
            return
        try:
            self.current_storage = self.storage_manager.load_session(arg)
            print(f"Session '{arg}' loaded and activated.")
        except ValueError as e:
            print(f"Error: {e}")

    @command("list_sessions", "List all available sessions")
    def do_list_sessions(self, arg):
        """List all available sessions."""
        sessions = self.storage_manager.list_sessions()
        if sessions:
            print("Available sessions:")
            for session in sessions:
                print(f"  - {session}")
        else:
            print("No sessions found.")

    def save_current_session(self):
        if self.current_storage:
            self.storage_manager.save_current_session(self.current_storage)

    def precmd(self, line):
        # Save the current session before each command (if exists)
        self.save_current_session()
        return line


    @property
    def dynamic_prompt(self):
        base_prompt = self.prompt.strip()[1:-1]  # Remove parentheses and whitespace
        return f"({base_prompt}:{self.state_machine.current_state.name}) "

    def update_agent_clibase(self):
        update = {
            "current_state": self.state_machine.current_state.name,
            "last_transition": self.state_machine.last_transition,
            "available_commands": list(self.get_available_commands()),
            "storage_data": self.current_storage.data if self.current_storage else {},
            "command_history": self.current_storage.command_history if self.current_storage else [],
            "steak": True
        }
        self.agent_communicator.send_update(update)        

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
        always_available = {'help', 'exit','new_session','load_session','list_sessions'}
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
            dot.attr(rankdir='LR', size='12,8')
            
            # Create a separate subgraph for the legend
            with dot.subgraph(name='cluster_legend') as legend:
                legend.attr(label='Legend', labeljust='r', labelloc='b', fontname='Arial-Bold', fontsize='14')
                legend.attr(style='filled', color='lightgrey', fillcolor='#f0f0f0')  # Light background
                legend.attr(penwidth='1')  # Thin border
                
                # Add legend items with improved spacing and icons
                legend.node('legend_input', '🔵 Input Required', shape='plaintext', fontname='Arial')
                legend.node('legend_cancel', '⭕ Cancellable', shape='plaintext', fontname='Arial')
                legend.node('legend_dashed', 'Dashed: Cancellable', shape='plaintext', fontname='Arial')
                legend.node('legend_red', 'Red: Last Transition', shape='plaintext', fontname='Arial')
                
                # Arrange legend items vertically with increased spacing
                legend.edge('legend_input', 'legend_cancel', style='invis')
                legend.edge('legend_cancel', 'legend_dashed', style='invis')
                legend.edge('legend_dashed', 'legend_red', style='invis')
                legend.attr(rankdir='TB', ranksep='0.3')

            # Add implementation name to the top left
            dot.attr(label=f'Implementation: {self.implementation_name}', labelloc='t', labeljust='l', fontname='Arial-Bold')
            
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
                    
                    # Check for additional decorators
                    if hasattr(self, f'do_{command}'):
                        method = getattr(self, f'do_{command}')
                        decorators = get_decorators(method)
                        
                        # Add visual cues based on decorators
                        if 'input_required_command' in decorators:
                            edge_attrs['color'] = 'blue'
                            edge_attrs['label'] += ' 🔵'
                        if 'cancellable_command' in decorators:
                            edge_attrs['style'] = 'dashed'
                            edge_attrs['label'] += ' ⭕'
                    
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

            try:
                func = getattr(self, 'do_' + cmd)
                # result = func(arg, self.current_storage)  # Pass current_storage here
                result = func(arg)
                
                if result == "CANCEL_TRANSITION":
                    return False

                if cmd in self.state_machine.current_state.transitions:
                    self.state_machine.transition(cmd)

                if hasattr(self, 'visualize_state_machine'):
                    self.visualize_state_machine(self.state_machine)

                self.update_agent_clibase()

                return result == "EXIT"  # Only exit if the command explicitly returns "EXIT"
            except AttributeError:
                return self.default(line)

    def postcmd(self, stop, line):
        if not stop:
            print(f"\nCurrent state: {self.state_machine.current_state.name}")
        return stop
    
"""
Overview of the key methods related to storage options in our CLI system, along with their use cases:

Storage Creation and Management:

new_session(name): Create a new working session.
    Use case: Starting a new task or project.

load_session(name): Load an existing session.
    Use case: Resuming work on a previous task.

list_sessions(): List all available sessions.
    Use case: Reviewing existing work or choosing a session to load.


Data Storage and Retrieval:

update_data(key, value): Store or update a piece of data in the current session.
    Use case: Saving the result of an operation or updating the state of the current task.

get_data(key): Retrieve a piece of data from the current session.
    Use case: Accessing previously stored information to use in a command.


Command History:

add_command_result(command, result): Log the execution of a command and its result.
    Use case: Keeping a record of actions performed in a session, useful for auditing or undoing operations.


Session Persistence:

save_current_session(): Save the current session to a file.
    Use case: Ensuring all changes are persisted, typically called automatically before each command.

to_json(): Convert the current session data to a JSON string.
    Use case: Preparing session data for storage or transmission.

from_json(json_str): Create a session from a JSON string.
    Use case: Reconstructing a session from stored data.


Session Information:

session_info(): Display information about the current session.
    Use case: Reviewing the current state of the session, including stored data and command history.


Error Handling and Validation:

Checking for current_storage before operations.
    Use case: Ensuring a session is active before performing operations that require session data.


These methods provide a comprehensive toolkit for managing persistent state in a CLI application. 
They allow for creating separate workspaces (sessions) for different tasks, storing and retrieving data
within those sessions, tracking command history, and persisting all this information between runs of the 
application. This system enables complex, stateful CLI applications that can maintain context across 
multiple uses, supporting workflows that span multiple sittings or even multiple users working on the same
data at different times.

"""
class SharedStorage:
    def __init__(self, version: str = "1.0.0"):
        self.version = version
        self.data: Dict[str, Any] = {}
        self.command_history: List[Dict[str, Any]] = []

    def update_data(self, key: str, value: Any) -> None:
        """
        Update or store a value in the session data associated with the given key.

        This method is central to the CLI's functionality, where users collaborate
        with agents (LLMs) to create and modify structured data, such as assessment 
        categories or other task-specific content. 

        The data stored via this method can be highly structured, depending on the 
        specific CLI use case. For example, in an assessment task, it might store 
        JSON structures representing categories with corresponding 5-point scales 
        or other complex content.

        Parameters:
            key (str): The unique identifier for the data being stored. This could 
                    represent an assessment category, feedback entry, or any 
                    other data relevant to the session.
            value (Any): The data to be stored under the specified key. The value 
                        can be simple (e.g., a string, number) or complex 
                        (e.g., a dictionary representing a JSON structure).

        Note:
            - If a value already exists for the given key, it will be overwritten.
            - The CLI relies on this behavior to allow users to refine and adjust 
            their inputs throughout the session.
            - Each update is also logged in the command history to maintain an 
            audit trail, ensuring transparency and accountability in user actions.
        """
        self.data[key] = value

    def get_data(self, key: str) -> Any:
        return self.data.get(key)

    def add_command_result(self, command: str, result: Any) -> None:
        self.command_history.append({
            "command": command,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })

    def to_json(self) -> str:
        return json.dumps({
            "version": self.version,
            "data": self.data,
            "command_history": self.command_history
        }, default=str, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'SharedStorage':
        data = json.loads(json_str)
        storage = cls(version=data["version"])
        storage.data = data["data"]
        storage.command_history = data["command_history"]
        return storage

    def save_to_file(self, filename: str) -> None:
        with open(filename, 'w') as f:
            f.write(self.to_json())

    @classmethod
    def load_from_file(cls, filename: str) -> 'SharedStorage':
        with open(filename, 'r') as f:
            return cls.from_json(f.read())
        
class StorageManager:
    def __init__(self, base_dir: str = ".uccli_sessions"):
        self.base_dir = os.path.expanduser(base_dir)
        self.current_session = None
        self.shared_storage = None  # This should be set when a session is created or loaded
        self.ensure_base_dir()

    def ensure_base_dir(self):
        os.makedirs(self.base_dir, exist_ok=True)

    def create_session(self, name: str) -> SharedStorage:
        session_path = os.path.join(self.base_dir, f"{name}.json")
        if os.path.exists(session_path):
            raise ValueError(f"Session '{name}' already exists")
        storage = SharedStorage()
        storage.save_to_file(session_path)
        self.current_session = name
        self.shared_storage = storage  # Set shared_storage after creating a session
        return storage

    def load_session(self, name: str) -> SharedStorage:
        session_path = os.path.join(self.base_dir, f"{name}.json")
        if not os.path.exists(session_path):
            raise ValueError(f"Session '{name}' does not exist")
        self.current_session = name
        self.shared_storage = SharedStorage.load_from_file(session_path)  # Set shared_storage after loading a session
        return self.shared_storage

    def save_current_session(self):
        if not self.current_session:
            raise ValueError("No active session")
        session_path = os.path.join(self.base_dir, f"{self.current_session}.json")
        self.shared_storage.save_to_file(session_path)

    def list_sessions(self) -> List[str]:
        return [f.replace('.json', '') for f in os.listdir(self.base_dir) if f.endswith('.json')]

    # update_data method that logs each update as a separate command in command_history
    def update_data(self, key: str, value: Any) -> None:
        if not self.shared_storage:
            raise ValueError("No active session")

        # Update the data in the current session
        self.shared_storage.update_data(key, value)
        
        # Automatically log the data update to the command history
        self.shared_storage.add_command_result(f"update_data: {key}", {"value": value})

        # Save the session after updating
        self.save_current_session()

    def get_data(self, key: str) -> Any:
        if not self.shared_storage:
            raise ValueError("No active session")
        return self.shared_storage.get_data(key)

    def add_command_result(self, command: str, result: Any) -> None:
        if not self.shared_storage:
            raise ValueError("No active session")
        self.shared_storage.add_command_result(command, result)
        self.save_current_session()  # Automatically save after updating

    def get_command_history(self) -> List[Dict[str, Any]]:
        if not self.shared_storage:
            raise ValueError("No active session")
        return self.shared_storage.command_history
