import sys
import os
from typing import List
import time
import logging
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completion
from prompt_toolkit.shortcuts import CompleteStyle

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from uccli import GenericCLI, GenericCLICompleter, StateMachine, State, CommandCompleter, Command,  command, visualize_after_command 

logging.basicConfig(level=logging.DEBUG)        


class AuthorListCLICompleter(CommandCompleter):
    def get_command_specific_completions(self, line, word_before_cursor):
        command = line.split()[0]
        if command == 'select_model':
            for model in self.cli.available_models:
                if model.startswith(word_before_cursor):
                    yield Completion(model, start_position=-len(word_before_cursor))

class AuthorListCLI(GenericCLI):

    intro = "Welcome to the Authors. Type 'help' or '?' to list commands."
    prompt = "(Authors) "

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
        time.sleep(1)
        self.visualize_state_machine(state_machine)

        self.authors: List[str] = []
        self.current_model: str = None
        self.available_models = ["model1", "model2", "model3"]
        self.output_file = None

        self.command_completer = AuthorListCLICompleter(self)
        self.session = PromptSession(completer=self.command_completer, complete_style=CompleteStyle.MULTI_COLUMN)

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