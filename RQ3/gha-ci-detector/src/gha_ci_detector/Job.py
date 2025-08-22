from typing import Optional

from gha_ci_detector.Step import Step


class Job:
    def __init__(self, name, yaml):
        self.name = name
        self.yaml: dict = yaml

    @property
    def job_name(self):
        if isinstance(self.yaml, dict) and "name" in self.yaml.keys():
            return self.yaml["name"]
        else:
            return self.name

    def has_permissions(self):
        if not isinstance(self.yaml, dict):
            return False
        return "permissions" in self.yaml.keys()

    def get_steps(self) -> list[Step]:
        if not isinstance(self.yaml, dict):
            return []
        if "steps" in self.yaml.keys():
            if self.yaml["steps"] is None:
                return []
            return list(map(lambda x: Step(x), self.yaml["steps"]))
        elif "uses" in self.yaml.keys():
            return [Step({
                "uses": self.yaml["uses"]
            }, True)]
        else:
            return []

    def get_if(self) -> Optional[str]:
        if isinstance(self.yaml, dict) and "if" in self.yaml.keys():
            return self.yaml["if"]
        else:
            return None

    def __str__(self):
        return "Job: \n" + self.name + " " + str(self.yaml) + "\n"

    def __repr__(self):
        return self.__str__()
