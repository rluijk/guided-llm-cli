from generalized import GenericCLI,StateMachine, State, CommandCompleter, Completion, visualize_after_command, command
from underdogcowboy import LLMConfigManager

class RefactoredTracingConfigProcessor(GenericCLI):
    intro = "Welcome to the Tracing Configuration Manager. Type 'help' or '?' to list commands."
    prompt = "(tracing_config) "

    def __init__(self):
        # Define states
        initial_state = State("initial")
        config_displayed_state = State("config_displayed")
        config_updated_state = State("config_updated")
        langsmith_toggled_state = State("langsmith_toggled")

        # Define transitions
        initial_state.add_transition("show", config_displayed_state)
        initial_state.add_transition("update", config_updated_state)
        initial_state.add_transition("toggle_langsmith", langsmith_toggled_state)

        config_displayed_state.add_transition("update", config_updated_state)
        config_displayed_state.add_transition("toggle_langsmith", langsmith_toggled_state)

        config_updated_state.add_transition("show", config_displayed_state)
        config_updated_state.add_transition("toggle_langsmith", langsmith_toggled_state)

        langsmith_toggled_state.add_transition("show", config_displayed_state)
        langsmith_toggled_state.add_transition("update", config_updated_state)

        # Create state machine
        state_machine = StateMachine(initial_state)
        for state in [config_displayed_state, config_updated_state, langsmith_toggled_state]:
            state_machine.add_state(state)

        super().__init__(state_machine)
        self.visualize_state_machine(state_machine)

        self.config_manager = LLMConfigManager()

    @command("show", "Display current tracing configuration.")
    @visualize_after_command('visualize_state_machine')
    def do_show(self, arg):
        config = self.config_manager.get_tracing_config()
        print("Tracing Configuration:")
        for key, value in config.items():
            if key == 'langsmith_api_key':
                print(f"  {key}: ****")
            else:
                print(f"  {key}: {value}")

    @command("update", "Update tracing configuration settings.")
    @visualize_after_command('visualize_state_machine')
    def do_update(self, arg):
        self.config_manager.update_tracing_config()
        print("Tracing configuration updated.")

    @command("toggle_langsmith", "Toggle LangSmith tracing on or off.")
    @visualize_after_command('visualize_state_machine')
    def do_toggle_langsmith(self, arg):
        config = self.config_manager.get_tracing_config()
        current_status = config.get('use_langsmith', 'no')
        new_status = 'yes' if current_status.lower() == 'no' else 'no'
        self.config_manager.update_model_property('tracing', 'use_langsmith', new_status)
        print(f"LangSmith tracing {'enabled' if new_status == 'yes' else 'disabled'}.")

    @command("help", "List available commands with their descriptions.")
    @visualize_after_command('visualize_state_machine')
    def do_help(self, arg):
        print("Available commands:")
        for method in dir(self):
            if method.startswith('do_'):
                command = method[3:]
                doc = getattr(self, method).__doc__
                print(f"  {command}: {doc}")

    @command("exit", "Exit the Tracing Configuration Manager.")
    def do_exit(self, arg):
        print("Exiting Tracing Configuration Manager. Goodbye!")
        return True

def main():
    RefactoredTracingConfigProcessor().cmdloop()

if __name__ == "__main__":
    main()
