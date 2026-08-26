from copr_updater.version import Version, make_version, version_to_str


class Spec:
    def __init__(self, text: str):
        self.lines: list[str] = text.splitlines()

        properties = [
            'Name: ',
            'Version: ',
            'Release: ',
        ]

        self.property_indices: dict[str, int] = {}

        for i, line in enumerate(self.lines):
            for property in properties:
                if line.startswith(property):
                    self.property_indices[property] = i

    def get_property(self, name: str):
        line = self.lines[self.property_indices[name]]
        return line.removeprefix(name)

    def set_property(self, name: str, value: str):
        self.lines[self.property_indices[name]] = name + value

    @property
    def version(self):
        return make_version(self.get_property('Version: '))
    @version.setter
    def version(self, value: Version):
        self.set_property('Version: ', version_to_str(value))

    @property
    def name(self):
        return self.get_property('Name: ')

    @property
    def release(self):
        value = self.get_property('Release: ')
        if value == '%autorelease':
            return value
        return int(value.removesuffix('%{?dist}'))
    @release.setter
    def release(self, value: int):
        self.set_property('Release: ', str(value) + '%{?dist}')

    def text(self):
        return '\n'.join(self.lines) + '\n'

def version_cmp(a: str, b: str) -> bool:
    def int_if_possible(x: str):
        try:
            return int(x)
        except Exception:
            return x

    a_list = list(map(int_if_possible, a.split('.')))
    b_list = list(map(int_if_possible, b.split('.')))
    return a_list < b_list
