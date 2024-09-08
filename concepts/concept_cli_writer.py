from generalized import GenericCLICompleter,GenericCLI, StateMachine, State, visualize_after_command, command
import json

class ArticleWritingCLI(GenericCLI):
    intro = "Welcome to the Article Writing Assistant. Type 'help' or '?' to list commands."
    prompt = "(ArticleWriter) "

    def __init__(self):
        # Define states
        initial_state = State("initial")
        outlined_state = State("outlined")
        writing_state = State("writing")
        editing_state = State("editing")
        completed_state = State("completed")

        # Define transitions
        initial_state.add_transition("plan", outlined_state)
        initial_state.add_transition("load", outlined_state)

        outlined_state.add_transition("write", writing_state)
        outlined_state.add_transition("save", outlined_state)
        outlined_state.add_transition("edit_outline", outlined_state)

        writing_state.add_transition("edit", editing_state)
        writing_state.add_transition("complete", completed_state)
        writing_state.add_transition("save", writing_state)
        writing_state.add_transition("status", writing_state)

        editing_state.add_transition("fix", writing_state)
        editing_state.add_transition("unfix", writing_state)
        editing_state.add_transition("save", editing_state)
        editing_state.add_transition("status", editing_state)

        completed_state.add_transition("edit", editing_state)
        completed_state.add_transition("save", completed_state)
        completed_state.add_transition("status", completed_state)

        # Add 'exit', 'view_outline', 'back', 'review', 'jump_to_section', and 'word_count' transitions to all states
        for state in [initial_state, outlined_state, writing_state, editing_state, completed_state]:
            state.add_transition("exit", state)
            state.add_transition("view_outline", state)
            state.add_transition("back", state)
            state.add_transition("review", state)
            state.add_transition("jump_to_section", state)
            state.add_transition("word_count", state)

        # Create state machine
        state_machine = StateMachine(initial_state)
        for state in [outlined_state, writing_state, editing_state, completed_state]:
            state_machine.add_state(state)

        super().__init__(state_machine)

        self.outline = None
        self.current_section = None
        self.article_content = {}
        self.state_history = []

    @visualize_after_command('visualize_state_machine')
    @command("plan", "Create an outline for the article")
    def do_plan(self, arg):
        # Here you would call your AI model to generate the outline
        # For now, we'll use a mock outline
        self.outline = {
            "introduction": 300,
            "main_body_1": 800,
            "main_body_2": 800,
            "main_body_3": 800,
            "conclusion": 300
        }
        print("Outline created:")
        print(json.dumps(self.outline, indent=2))
        self.state_history.append(self.state_machine.current_state)

    @visualize_after_command('visualize_state_machine')
    @command("write", "Write the next section of the article")
    def do_write(self, arg):
        if not self.outline:
            print("Error: You need to create an outline first.")
            return
        
        for section, word_count in self.outline.items():
            if section not in self.article_content:
                self.current_section = section
                # Here you would call your AI model to write the section
                self.article_content[section] = f"Content for {section} ({word_count} words)"
                print(f"Writing section: {section}")
                print(self.article_content[section])
                self.state_history.append(self.state_machine.current_state)
                return
        
        print("All sections have been written.")
        self.state_machine.transition_to("completed")
        self.state_history.append(self.state_machine.current_state)

    @visualize_after_command('visualize_state_machine')
    @command("edit", "Edit the current section")
    def do_edit(self, arg):
        if not self.current_section:
            print("Error: No current section to edit.")
            return
        print(f"Editing {self.current_section}:")
        new_content = input("Enter the new content (or press Enter to keep current content):\n")
        if new_content:
            self.article_content[self.current_section] = new_content
            print(f"Updated content for {self.current_section}")
        self.state_history.append(self.state_machine.current_state)

    @visualize_after_command('visualize_state_machine')
    @command("fix", "Apply edits and move to the next section")
    def do_fix(self, arg):
        if not self.current_section:
            print("Error: No current section to fix.")
            return
        print(f"Applied edits to {self.current_section}")
        self.state_machine.transition_to("writing")
        self.state_history.append(self.state_machine.current_state)

    @visualize_after_command('visualize_state_machine')
    @command("unfix", "Discard edits and move to the next section")
    def do_unfix(self, arg):
        if not self.current_section:
            print("Error: No current section to unfix.")
            return
        print(f"Discarded edits for {self.current_section}")
        self.state_machine.transition_to("writing")
        self.state_history.append(self.state_machine.current_state)

    @visualize_after_command('visualize_state_machine')
    @command("complete", "Mark the article as completed")
    def do_complete(self, arg):
        if len(self.article_content) != len(self.outline):
            print("Error: Not all sections have been written yet.")
            return
        print("Article marked as completed.")
        self.state_history.append(self.state_machine.current_state)

    @visualize_after_command('visualize_state_machine')
    @command("save", "Save the current work in progress")
    def do_save(self, arg):
        filename = arg or "article_wip.json"
        data = {
            "outline": self.outline,
            "content": self.article_content,
            "current_section": self.current_section
        }
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Work in progress saved to {filename}")

    @visualize_after_command('visualize_state_machine')
    @command("load", "Load a previously saved work in progress")
    def do_load(self, arg):
        filename = arg or "article_wip.json"
        try:
            with open(filename, "r") as f:
                data = json.load(f)
            self.outline = data["outline"]
            self.article_content = data["content"]
            self.current_section = data["current_section"]
            print(f"Loaded work in progress from {filename}")
            self.state_machine.transition_to("outlined")
            self.state_history.append(self.state_machine.current_state)
        except FileNotFoundError:
            print(f"Error: File {filename} not found.")

    @visualize_after_command('visualize_state_machine')
    @command("status", "Show the current status of the article")
    def do_status(self, arg):
        print("Current status:")
        print(f"State: {self.state_machine.current_state.name}")
        print(f"Current section: {self.current_section}")
        print("Completed sections:")
        for section in self.article_content:
            print(f"- {section}")

    @command("exit", "Exit the program")
    def do_exit(self, arg):
        print("Goodbye!")
        return True

    @command("view_outline", "View the current outline")
    def do_view_outline(self, arg):
        if not self.outline:
            print("No outline created yet.")
        else:
            print("Current outline:")
            print(json.dumps(self.outline, indent=2))

    @visualize_after_command('visualize_state_machine')
    @command("back", "Go back to the previous state")
    def do_back(self, arg):
        if len(self.state_history) > 1:
            self.state_history.pop()  # Remove current state
            previous_state = self.state_history.pop()
            self.state_machine.transition_to(previous_state.name)
            print(f"Returned to {previous_state.name} state.")
        else:
            print("Cannot go back further.")

    @visualize_after_command('visualize_state_machine')
    @command("edit_outline", "Modify the current outline")
    def do_edit_outline(self, arg):
        if not self.outline:
            print("No outline to edit. Create an outline first.")
            return
        print("Current outline:")
        print(json.dumps(self.outline, indent=2))
        print("\nEnter new section names and word counts (e.g., 'introduction:300'). Enter 'done' when finished.")
        new_outline = {}
        while True:
            entry = input("> ")
            if entry.lower() == 'done':
                break
            try:
                section, word_count = entry.split(':')
                new_outline[section.strip()] = int(word_count)
            except ValueError:
                print("Invalid format. Use 'section:word_count'.")
        if new_outline:
            self.outline = new_outline
            print("Updated outline:")
            print(json.dumps(self.outline, indent=2))

    @command("review", "Review the entire article")
    def do_review(self, arg):
        if not self.article_content:
            print("No content to review yet.")
            return
        print("Article Review:")
        for section, content in self.article_content.items():
            print(f"\n--- {section.upper()} ---")
            print(content)

    @visualize_after_command('visualize_state_machine')
    @command("jump_to_section", "Jump to a specific section")
    def do_jump_to_section(self, arg):
        if not self.outline:
            print("No outline created yet. Create an outline first.")
            return
        print("Available sections:")
        for section in self.outline.keys():
            print(f"- {section}")
        section = input("Enter the section name to jump to: ")
        if section in self.outline:
            self.current_section = section
            print(f"Jumped to section: {section}")
            if self.state_machine.current_state.name != "writing":
                self.state_machine.transition_to("writing")
            self.state_history.append(self.state_machine.current_state)
        else:
            print(f"Section '{section}' not found in the outline.")

    @command("word_count", "Show word count for each section")
    def do_word_count(self, arg):
        if not self.outline:
            print("No outline created yet.")
            return
        print("Word count by section:")
        total_words = 0
        for section, target_count in self.outline.items():
            actual_count = len(self.article_content.get(section, "").split())
            print(f"{section}: {actual_count}/{target_count} words")
            total_words += actual_count
        print(f"\nTotal word count: {total_words}")

if __name__ == "__main__":
    cli = ArticleWritingCLI()
    cli.cmdloop()