from abc import ABC, abstractmethod
import json

class AgentCommunicator(ABC):
    @abstractmethod
    def send_update(self, update_data: dict):
        pass

class DummyAgentCommunicator(AgentCommunicator):
    def send_update(self, update_data: dict):
        print("Update to Agent CLIBase (Dummy):")
        print(json.dumps(update_data, indent=2))