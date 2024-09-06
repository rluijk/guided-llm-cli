import pytest
from unittest.mock import patch
from io import StringIO
from typing import Set
from concepts.generalized import State, StateMachine, AuthorListCLI, GenericCLI, command


# Test State
def test_state_add_transition():
    state1 = State("state1")
    state2 = State("state2")
    state1.add_transition("command1", state2)
    assert state1.transitions["command1"] == state2

# Test StateMachine
def test_state_machine_add_state():
    state_machine = StateMachine(State("initial"))
    new_state = State("new_state")
    state_machine.add_state(new_state)
    assert state_machine.states["new_state"] == new_state

def test_state_machine_transition_success():
    initial_state = State("initial")
    next_state = State("next_state")
    initial_state.add_transition("command1", next_state)
    state_machine = StateMachine(initial_state)
    assert state_machine.transition("command1")
    assert state_machine.current_state == next_state

def test_state_machine_transition_failure():
    initial_state = State("initial")
    state_machine = StateMachine(initial_state)
    assert not state_machine.transition("invalid_command")
    assert state_machine.current_state == initial_state

def test_state_machine_get_available_commands():
    initial_state = State("initial")
    next_state = State("next_state")
    initial_state.add_transition("command1", next_state)
    initial_state.add_transition("command2", next_state)
    state_machine = StateMachine(initial_state)
    assert state_machine.get_available_commands() == {"command1", "command2"}

# Test AuthorListCLI
@patch('sys.stdout', new_callable=StringIO)
def test_author_list_cli_add_author(mock_stdout):
    cli = AuthorListCLI()
    cli.onecmd("add_author John Doe")
    assert "Added author: John Doe" in mock_stdout.getvalue()

@patch('sys.stdout', new_callable=StringIO)
def test_author_list_cli_list_authors(mock_stdout):
    cli = AuthorListCLI()
    cli.onecmd("add_author John Doe")
    cli.onecmd("add_author Jane Smith")
    cli.onecmd("list_authors")
    output = mock_stdout.getvalue()
    assert "1. John Doe" in output
    assert "2. Jane Smith" in output

@patch('sys.stdout', new_callable=StringIO)
def test_author_list_cli_select_model_valid(mock_stdout):
    cli = AuthorListCLI()
    cli.onecmd("select_model model1")
    assert "Selected model: model1" in mock_stdout.getvalue()

@patch('sys.stdout', new_callable=StringIO)
def test_author_list_cli_select_model_invalid(mock_stdout):
    cli = AuthorListCLI()
    cli.onecmd("select_model invalid_model")
    assert "Invalid model." in mock_stdout.getvalue()

@patch('sys.stdout', new_callable=StringIO)
def test_author_list_cli_analyze_authors(mock_stdout):
    cli = AuthorListCLI()
    cli.onecmd("select_model model2")
    cli.onecmd("add_author John Doe")
    cli.onecmd("analyze_authors")
    assert "Analyzing authors using model model2..." in mock_stdout.getvalue()

# Test state transitions
def test_author_list_cli_state_transitions():
    cli = AuthorListCLI()
    assert cli.state_machine.current_state.name == "initial"

    cli.onecmd("add_author John Doe")
    assert cli.state_machine.current_state.name == "authors_added"

    cli.onecmd("select_model model1")
    assert cli.state_machine.current_state.name == "ready"

    cli.onecmd("add_author Jane Smith")
    assert cli.state_machine.current_state.name == "ready" 

    cli.onecmd("select_model model2")
    assert cli.state_machine.current_state.name == "ready"

    cli.onecmd("analyze_authors")
    assert cli.state_machine.current_state.name == "ready"

# Test invalid command in current state
@patch('sys.stdout', new_callable=StringIO)
def test_author_list_cli_invalid_command(mock_stdout):
    cli = AuthorListCLI()
    cli.onecmd("analyze_authors")  # Invalid in the initial state
    assert "Command 'analyze_authors' not available in current state." in mock_stdout.getvalue()

@patch('sys.stdout', new_callable=StringIO)
def test_author_list_cli_list_authors_in_initial_state(mock_stdout):
    cli = AuthorListCLI()  # Start in the initial state
    cli.onecmd("list_authors")  # Execute list_authors in the initial state
    output = mock_stdout.getvalue()
    assert output.strip() == "No authors added yet."    

@patch('sys.stdout', new_callable=StringIO)
def test_author_list_cli_list_authors_in_authors_added_state(mock_stdout):
    cli = AuthorListCLI()
    cli.onecmd("add_author John Doe")  # Transition to authors_added state
    cli.onecmd("list_authors")  # Execute list_authors
    output = mock_stdout.getvalue()
    # Assert that the added author is listed
    assert "1. John Doe" in output
    # Check that the state remains in "authors_added"
    assert cli.state_machine.current_state.name == "authors_added"

@patch('sys.stdout', new_callable=StringIO)
def test_author_list_cli_list_authors_in_model_selected_state(mock_stdout):
    cli = AuthorListCLI()
    cli.onecmd("select_model model1")  # Transition to model_selected state

    # Reset mock_stdout to capture only list_authors output
    mock_stdout.seek(0)
    mock_stdout.truncate(0)

    cli.onecmd("list_authors")  # Execute list_authors
    output = mock_stdout.getvalue()
    assert output.strip() == "No authors added yet."


@patch('sys.stdout', new_callable=StringIO)
def test_author_list_cli_list_authors_in_ready_state(mock_stdout):
    cli = AuthorListCLI()
    cli.onecmd("add_author John Doe") 
    cli.onecmd("select_model model1")  # Transition to ready state
    cli.onecmd("list_authors")  # Execute list_authors
    output = mock_stdout.getvalue()
    # Assert that the added author is listed
    assert "1. John Doe" in output
    # Check that the state remains in "ready"
    assert cli.state_machine.current_state.name == "ready"


def run_cli_commands(cli, commands):
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        for command in commands:
            cli.onecmd(command)  # Execute one command at a time
        return mock_stdout.getvalue()

def test_author_list_cli_list_authors_initial_state():
    cli = AuthorListCLI()
    output = run_cli_commands(cli, ["list_authors"])
    assert "1." not in output  # No authors should be listed initially

def test_author_list_cli_list_authors_after_add():
    cli = AuthorListCLI()
    output = run_cli_commands(cli, ["add_author John Doe", "list_authors"])
    assert "1. John Doe" in output  # John Doe should be listed

def test_author_list_cli_list_authors_multiple_authors():
    cli = AuthorListCLI()
    output = run_cli_commands(cli, [
        "add_author John Doe", 
        "add_author Jane Smith", 
        "list_authors"
    ])
    assert "1. John Doe" in output
    assert "2. Jane Smith" in output  # Both authors should be listed

def test_author_list_cli_list_authors_after_model_select():
    cli = AuthorListCLI()
    output = run_cli_commands(cli, [
        "select_model model1", 
        "add_author John Doe", 
        "list_authors"
    ])
    assert "1. John Doe" in output  # Author added after model selection

def test_author_list_cli_list_authors_displayed_as_available():
    cli = AuthorListCLI()
    available_commands = cli.state_machine.get_available_commands()
    assert "list_authors" in available_commands  # Check if list_authors is available

@patch('sys.stdout', new_callable=StringIO)
def test_author_list_cli_list_authors_executable_in_initial_state(mock_stdout):
    cli = AuthorListCLI()
    cli.onecmd("list_authors") 
    output = mock_stdout.getvalue()
    # Check if the command executed without error (e.g., "Command not available")
    assert "Command 'list_authors' not available" not in output    
class CounterCLI(GenericCLI):
    def __init__(self):
        # Define states
        zero_state = State("zero", self)
        positive_state = State("positive", self)

        # Define transitions
        zero_state.add_transition("increment", positive_state)
        positive_state.add_transition("increment", positive_state)
        positive_state.add_transition("decrement", positive_state)  # Changed this
        positive_state.add_transition("decrement_to_zero", zero_state)  # Added this

        # Add common commands to both states
        for state in [zero_state, positive_state]:
            state.add_transition("show", state)

        # Create state machine
        state_machine = StateMachine(zero_state)
        state_machine.add_state(positive_state)

        super().__init__(state_machine)
        self.counter = 0

    @command("increment", "Increment the counter")
    def do_increment(self, arg):
        self.counter += 1
        print(f"Counter: {self.counter}")

    @command("decrement", "Decrement the counter")
    def do_decrement(self, arg):
        if self.counter > 1:
            self.counter -= 1
            print(f"Counter: {self.counter}")
        elif self.counter == 1:
            self.counter = 0
            self.state_machine.transition("decrement_to_zero")
            print(f"Counter: {self.counter}")
        else:
            print("Counter is already at zero")

    @command("show", "Show the current counter value")
    def do_show(self, arg):
        print(f"Counter: {self.counter}")

    def get_available_commands(self) -> Set[str]:
        state_commands = super().get_available_commands()
        always_available = {'help', 'exit'}
        return state_commands.union(always_available)
# Tests for CounterCLI
@pytest.fixture
def counter_cli():
    return CounterCLI()

def test_counter_cli_initial_state(counter_cli):
    assert counter_cli.state_machine.current_state.name == "zero"
    assert counter_cli.counter == 0

@patch('sys.stdout', new_callable=StringIO)
def test_counter_cli_increment(mock_stdout, counter_cli):
    counter_cli.onecmd("increment")
    assert counter_cli.state_machine.current_state.name == "positive"
    assert counter_cli.counter == 1
    assert "Counter: 1" in mock_stdout.getvalue()


@patch('sys.stdout', new_callable=StringIO)
def test_counter_cli_decrement_at_zero(mock_stdout, counter_cli):
    counter_cli.onecmd("decrement")
    assert counter_cli.state_machine.current_state.name == "zero"
    assert counter_cli.counter == 0
    assert "Command 'decrement' not available in current state." in mock_stdout.getvalue()

@patch('sys.stdout', new_callable=StringIO)
def test_counter_cli_increment_and_decrement(mock_stdout, counter_cli):
    counter_cli.onecmd("increment")
    counter_cli.onecmd("increment")
    counter_cli.onecmd("decrement")
    assert counter_cli.state_machine.current_state.name == "positive"
    assert counter_cli.counter == 1
    assert "Counter: 1" in mock_stdout.getvalue()

@patch('sys.stdout', new_callable=StringIO)
def test_counter_cli_show_command(mock_stdout, counter_cli):
    counter_cli.onecmd("increment")
    mock_stdout.truncate(0)
    mock_stdout.seek(0)
    counter_cli.onecmd("show")
    assert "Counter: 1" in mock_stdout.getvalue()

def test_counter_cli_available_commands(counter_cli):
    zero_state_commands = counter_cli.get_available_commands()
    assert "increment" in zero_state_commands
    assert "decrement" not in zero_state_commands
    assert "show" in zero_state_commands

    counter_cli.onecmd("increment")
    positive_state_commands = counter_cli.get_available_commands()
    assert "increment" in positive_state_commands
    assert "decrement" in positive_state_commands
    assert "show" in positive_state_commands

@patch('sys.stdout', new_callable=StringIO)
def test_counter_cli_invalid_command_in_zero_state(mock_stdout, counter_cli):
    counter_cli.onecmd("decrement")
    assert "Command 'decrement' not available in current state." in mock_stdout.getvalue()

@patch('sys.stdout', new_callable=StringIO)
def test_counter_cli_state_transition(mock_stdout, counter_cli):
    assert counter_cli.state_machine.current_state.name == "zero"
    counter_cli.onecmd("increment")
    assert counter_cli.state_machine.current_state.name == "positive"
    counter_cli.onecmd("decrement")
    assert counter_cli.state_machine.current_state.name == "zero"