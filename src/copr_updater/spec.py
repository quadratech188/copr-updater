from .forge import Forge

class Spec:
    def __init__(self, text: str):
        self.lines: list[str] = text.splitlines()

        properties = [
            'Name: ',
            'Version: ',
            'Release: ',
            '%global forgeurl '
        ]

        self.property_indices: dict[str, int] = {}

        for i, line in enumerate(self.lines):
            for property in properties:
                if line.startswith(property):
                    self.property_indices[property] = i

        self.forge: Forge = Forge.get(self.get_property('%global forgeurl '))

    def get_property(self, name: str):
        line = self.lines[self.property_indices[name]]
        return line.removeprefix(name)

    def set_property(self, name: str, value: str):
        self.lines[self.property_indices[name]] = name + value

    @property
    def version(self):
        return self.get_property('Version: ')
    @version.setter
    def version(self, value: str):
        self.set_property('Version: ', value)

    @property
    def name(self):
        return self.get_property('Name: ')

    @property
    def release(self):
        return int(self.get_property('Release: ').removesuffix('%{?dist}'))
    @release.setter
    def release(self, value: int):
        self.set_property('Release: ', str(value) + '%{?dist}')

    def text(self):
        return '\n'.join(self.lines) + '\n'

def version_cmp(a: str, b: str):
    a_list = list(map(int, a.split('.')))
    b_list = list(map(int, b.split('.')))
    return a_list < b_list
