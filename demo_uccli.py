from uccli import GenericCLI, StateMachine, State

class DemoCLI(GenericCLI):
    def __init__(self):
        initial_state = State("initial", self)
        authors_added_state = State("authors_added", self)

        initial_state.add_transition("add_author", authors_added_state)
        authors_added_state.add_transition("add_author", authors_added_state)
        authors_added_state.add_transition("list_authors", authors_added_state)

        state_machine = StateMachine(initial_state)
        state_machine.add_state(authors_added_state)

        super().__init__(state_machine)

        self.authors = []

    def do_add_author(self, arg):
        self.authors.append(arg)
        print(f"Added author: {arg}")

    def do_list_authors(self, arg):
        if not self.authors:
            print("No authors added yet.")
        else:
            for i, author in enumerate(self.authors, 1):
                print(f"{i}. {author}")

if __name__ == "__main__":
    cli = DemoCLI()
    
    # Simulate user input
    cli.onecmd("add_author Jane Austen")
    cli.onecmd("add_author Charles Dickens")
    cli.onecmd("list_authors")
    
    print("\nDemo completed. You can now interact with the CLI:")
    cli.cmdloop()