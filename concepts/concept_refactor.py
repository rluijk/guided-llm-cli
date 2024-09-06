import logging
from typing import List, Optional

from underdogcowboy import LLMConfigManager
from underdogcowboy import AgentDialogManager, test_agent

from generalized import GenericCLI,StateMachine, State, CommandCompleter, Completion, visualize_after_command, command

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.shortcuts import CompleteStyle
import os
import time

logging.basicConfig(level=logging.DEBUG)   


STATIC_PROMPT = "small message back please, we testing if we can reach you"

class LLMPokeCompleter(CommandCompleter):
    def get_command_specific_completions(self, line, word_before_cursor):
        command = line.split()[0]
        if command == 'select_model':
            for model in self.cli.available_models:
                if model.startswith(word_before_cursor):
                    yield Completion(model, start_position=-len(word_before_cursor))

class LLMPokeCLI(GenericCLI):
    intro = "Welcome to the LLM Poke Tool. Type 'help' or '?' to list commands."

    def __init__(self):
        # Define states
        initial_state = State("initial", self)
        model_selected_state = State("model_selected", self)

        # Define transitions
        initial_state.add_transition("list_models", initial_state)
        initial_state.add_transition("select_model", model_selected_state)
        initial_state.add_transition("poke_all", initial_state)

        model_selected_state.add_transition("list_models", model_selected_state)
        model_selected_state.add_transition("select_model", model_selected_state)
        model_selected_state.add_transition("poke", model_selected_state)
        model_selected_state.add_transition("poke_all", model_selected_state)

        # Create state machine
        state_machine = StateMachine(initial_state)
        state_machine.add_state(model_selected_state)

        super().__init__(state_machine)
        self.visualize_state_machine(state_machine)

        self.config_manager = LLMConfigManager()
        self.current_model: Optional[str] = None
        self.available_models: List[str] = self.config_manager.get_available_models()

        self.command_completer = LLMPokeCompleter(self)
        self.session = PromptSession(completer=self.command_completer, complete_style=CompleteStyle.MULTI_COLUMN)

    @command("list_models", "List all available LLM models")
    @visualize_after_command('visualize_state_machine')
    def do_list_models(self, arg):
        logging.info("Available models:")
        for i, model in enumerate(self.available_models, 1):
            logging.info(f"  {i}. {model}")
        logging.info("\nTo select a model, type the number or use 'select_model <number>' or 'select_model <name>'")

    @command("select_model", "Select a model to poke")
    @visualize_after_command('visualize_state_machine')
    def do_select_model(self, arg):
        if not arg:
            logging.error("Please provide a model number or name. Use 'list_models' to see available options.")
            return

        try:
            if arg.isdigit():
                index = int(arg) - 1
                if 0 <= index < len(self.available_models):
                    self.current_model = self.available_models[index]
                else:
                    raise ValueError(f"Invalid model number. Please choose between 1 and {len(self.available_models)}.")
            else:
                if arg in self.available_models:
                    self.current_model = arg
                else:
                    raise ValueError(f"Model '{arg}' not found. Use 'list_models' to see available options.")

            logging.info(f"Selected model: {self.current_model}")
            self.prompt = f"(llm_poke:{self.current_model}) "
        except ValueError as e:
            logging.error(str(e))

    @command("poke", "Send a static prompt to the selected model")
    @visualize_after_command('visualize_state_machine')
    def do_poke(self, arg):
        if not self.current_model:
            logging.error("No model selected. Please use 'select_model' first.")
            return

        try:
            provider, model = self.current_model.split(":")
            adm = AgentDialogManager([test_agent], model_name=model)
            logging.info(f"Sending message to: {self.current_model}")
            response = test_agent >> STATIC_PROMPT
            logging.info(f"Response from {self.current_model}: {response}")
        except Exception as e:
            logging.error(f"An error occurred while poking the model: {str(e)}")

    @command("poke_all", "Send a static prompt to all available LLM models")
    @visualize_after_command('visualize_state_machine')
    def do_poke_all(self, arg):
        for model in self.available_models:
            try:
                provider, model_name = model.split(":")
                adm = AgentDialogManager([test_agent], model_name=model_name)
                logging.info(f"Sending message to: {model}")
                response = test_agent >> STATIC_PROMPT
                logging.info(f"Response from {model}: {response}\n")
            except Exception as e:
                logging.error(f"An error occurred while poking model {model}: {str(e)}")

    @command("exit", "Exit the LLM Poke Tool")
    def do_exit(self, arg):
        logging.info("Exiting LLM Poke Tool. Goodbye!")
        return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    cli = LLMPokeCLI()
    cli.cmdloop()