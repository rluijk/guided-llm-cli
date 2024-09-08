from generalized import GenericCLICompleter, GenericCLI, StateMachine, State, visualize_after_command, command
import cmd
import os
import re
import json
from pathlib import Path
from prompt_toolkit import prompt, PromptSession
from prompt_toolkit.completion import WordCompleter, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.shortcuts import CompleteStyle

from underdogcowboy.core.config_manager import LLMConfigManager
from underdogcowboy import AgentDialogManager, agentclarity, Timeline, adm, AnthropicModel

class AgentClarityProcessor(GenericCLI):
    intro = "Welcome to the Agent Clarity Tool. Type 'help' or '?' to list commands."
    prompt = "(agent_clarity) "

    def __init__(self):
        # Define states
        setup_state = State("setup")
        ready_state = State("ready")
        agent_editing_state = State("agent_editing")
        analysis_state = State("analysis")
        results_state = State("results")
        # error_state = State("error")
        # help_state = State("help")
        config_state = State("config")

        # Define transitions
        setup_state.add_transition("select_model", ready_state)
        setup_state.add_transition("load_agent", ready_state)
        setup_state.add_transition("create_agent", agent_editing_state)
        # setup_state.add_transition("help", help_state)
        setup_state.add_transition("config", config_state)

        ready_state.add_transition("select_model", ready_state)
        ready_state.add_transition("load_agent", ready_state)
        ready_state.add_transition("create_agent", agent_editing_state)
        ready_state.add_transition("analyze", analysis_state)
        ready_state.add_transition("edit_agent", agent_editing_state)
        # ready_state.add_transition("help", help_state)
        ready_state.add_transition("config", config_state)

        agent_editing_state.add_transition("save", ready_state)
        agent_editing_state.add_transition("cancel", ready_state)
        # agent_editing_state.add_transition("help", help_state)

        analysis_state.add_transition("complete", results_state)
        analysis_state.add_transition("cancel", ready_state)
        # analysis_state.add_transition("help", help_state)

        results_state.add_transition("export", results_state)
        results_state.add_transition("analyze", analysis_state)
        results_state.add_transition("load_agent", ready_state)
        results_state.add_transition("select_model", ready_state)
        # results_state.add_transition("help", help_state)

        # error_state.add_transition("acknowledge", setup_state)
        # error_state.add_transition("help", help_state)

        #help_state.add_transition("back", lambda: self.state_machine.previous_state)

        config_state.add_transition("save", setup_state)
        config_state.add_transition("cancel", setup_state)
        #config_state.add_transition("help", help_state)

        # Create state machine
        state_machine = StateMachine(setup_state)
        for state in [ready_state, agent_editing_state, analysis_state, results_state, config_state]:
            state_machine.add_state(state)

        super().__init__(state_machine)
        self.visualize_state_machine(state_machine)

        self.command_completer = GenericCLICompleter(self)
        self.config_manager = LLMConfigManager()
        self.current_model = None
        self.available_models = self.config_manager.get_available_models()
        self.current_agent_file = None
        self.agent_data = None
        self.agents_dir = os.path.expanduser("~/.underdogcowboy/agents")
        self.timeline = Timeline()
        self.last_analysis = None
        self.message_export_path = ''
        self.dialog_save_path = ''         
        self.session = PromptSession(completer=self.command_completer, complete_style=CompleteStyle.MULTI_COLUMN)

    @visualize_after_command('visualize_state_machine')
    @command("select_model", "Select a model to use")
    def do_select_model(self, arg):
        if not arg:
            print("Please provide a model number or name. Use 'list_models' to see available options.")
            return

        available_models = self.config_manager.get_available_models()
        selected_model = self._select_model_logic(arg, available_models)

        if selected_model:
            provider, model_id = selected_model.split(':')
            self.config_manager.update_model_property(provider, 'selected_model', model_id)
            self.current_model = selected_model
            print(f"Selected model: {selected_model}")
            return True  # Indicate successful execution
        return False  # Indicate failed execution

    @visualize_after_command('visualize_state_machine')
    @command("load_agent", "Load an agent definition from a JSON file")
    def do_load_agent(self, arg):
        available_agents = self.get_available_agents()
        if not available_agents:
            print("No agent files found in the agents directory.")
            return False

        selected_agent = self._select_agent_logic(available_agents)
        if selected_agent:
            agent_path = os.path.join(self.agents_dir, selected_agent)
            if self._load_agent_from_file(agent_path):
                return True  # Indicate successful execution
        return False  # Indicate failed execution

    @visualize_after_command('visualize_state_machine')
    @command("create_agent", "Create a new agent definition")
    def do_create_agent(self, arg):
        agent_name = input("Enter a name for the new agent: ")
        if not self._validate_agent_name(agent_name):
            return False

        agent_description = input("Enter a description for the new agent: ")
        agent_system_message = input("Enter the system message for the new agent: ")

        if self._create_agent_file(agent_name, agent_description, agent_system_message):
            print(f"New agent '{agent_name}' created successfully.")
            return True
        return False

    @visualize_after_command('visualize_state_machine')
    @command("edit_agent", "Edit the current agent definition")
    def do_edit_agent(self, arg):
        if not self.agent_data:
            print("No agent loaded. Please load an agent first.")
            return False

        print("Current agent data:")
        print(json.dumps(self.agent_data, indent=2))
        
        # Implement editing logic here
        # For example:
        edit_field = input("Enter the field to edit (e.g., 'name', 'description', 'system_message'): ")
        new_value = input(f"Enter the new value for {edit_field}: ")
        
        if edit_field in self.agent_data:
            self.agent_data[edit_field] = new_value
            print(f"Updated {edit_field} to: {new_value}")
            return True
        else:
            print(f"Field {edit_field} not found in agent data.")
            return False

    @visualize_after_command('visualize_state_machine')
    @command("analyze", "Perform an analysis of the loaded agent definition")
    def do_analyze(self, arg):
        if not self.agent_data or not self.current_model:
            print("Please ensure both an agent and a model are selected before analysis.")
            return False

        print(f"Analyzing agent using model: {self.current_model}")
        # Implement analysis logic here
        self.last_analysis = f"Analysis results for agent {self.agent_data.get('name', 'Unknown')}"
        print("Analysis complete.")
        self.state_machine.trigger("complete")
        return True

    @visualize_after_command('visualize_state_machine')
    @command("export", "Export the last analysis results")
    def do_export(self, arg):
        if not self.last_analysis:
            print("No analysis results to export. Please perform an analysis first.")
            return False

        filename = input("Enter filename for export (default: analysis_results.txt): ") or "analysis_results.txt"
        with open(filename, 'w') as f:
            f.write(self.last_analysis)
        print(f"Analysis results exported to {filename}")
        return True

    @visualize_after_command('visualize_state_machine')
    @command("config", "Configure tool settings")
    def do_config(self, arg):
        print("Current configuration:")
        print(f"Message export path: {self.message_export_path}")
        print(f"Dialog save path: {self.dialog_save_path}")
        
        self.message_export_path = input("Enter new message export path (or press Enter to keep current): ") or self.message_export_path
        self.dialog_save_path = input("Enter new dialog save path (or press Enter to keep current): ") or self.dialog_save_path
        
        print("Configuration updated.")
        return True

    @visualize_after_command('visualize_state_machine')
    @command("save", "save settings")
    def do_save(self, arg):
        print("Save")
        return False

    @visualize_after_command('visualize_state_machine')
    @command("cancel", "save settings")
    def do_cancel(self, arg):
        print("cancel")
        return False

    @command("help", "Get help on available commands")
    def do_help(self, arg):
        print("Available commands:")
        for cmd, desc in self.get_commands().items():
            print(f"  {cmd}: {desc}")
        return True

    @command("exit", "Exit the Agent Clarity Tool")
    def do_exit(self, arg):
        print("Exiting Agent Clarity Tool. Goodbye!")
        return True

    # Helper methods
    def _select_model_logic(self, arg, available_models):
        # Implement model selection logic
        pass

    def get_available_agents(self):
        # Implement logic to get available agents
        pass

    def _select_agent_logic(self, available_agents):
        # Implement agent selection logic
        pass

    def _load_agent_from_file(self, agent_path):
        # Implement agent loading logic
        pass

    def _validate_agent_name(self, agent_name):
        # Implement agent name validation logic
        pass

    def _create_agent_file(self, agent_name, agent_description, agent_system_message):
        # Implement agent file creation logic
        pass

    # ... (other methods remain the same)

def main():
    AgentClarityProcessor().cmdloop()

if __name__ == "__main__":
    main()