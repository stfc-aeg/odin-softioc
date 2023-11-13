class DummyPvRecord():

    def __init__(self, name, initial_value=None, on_update=None):

        self.name = name
        self.value = initial_value
        self.on_update = on_update

    def set(self, value):

        print(f"DummyPvRecord {self.name} set called with value {value} {self.on_update}")
        self.value = value
        if self.on_update:
            self.on_update(value)

    def get(self):

        return self.value

class DummyPvBuilder():

    def __init__(self):
        pass

    @staticmethod
    def _create_record(name, **kwargs):

        print(f"DummyBuilder creating record {name}")
        return DummyPvRecord(name, **kwargs)

    aOut = _create_record
    longOut = _create_record
    longStringOut = _create_record
    aIn = _create_record
    longIn = _create_record
    longStringIn = _create_record