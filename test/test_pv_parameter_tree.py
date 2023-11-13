import pytest

from odin_softioc.pv_parameter_tree import PvParameterAccessor, PvParameterTree, ParameterTreeError
from test.utils import DummyPvBuilder


class PvTreeFixture():

    def __init__(self):

        self.initial_task_count = 0
        self.three_val = 3
        self.ro_val = 50210
        self.counter = 0

        self.params = {
            "ioc_name": PvParameterAccessor(
                'ioc_name', "IOC_NAME", initial_value="test_ioc"
            ),
            "task_count": PvParameterAccessor(
                "task_count", "BG_TASK_COUNT",
                on_set=self.set_task_count, initial_value=self.initial_task_count, param_type=int,
                writeable=True
            ),
            "bound_ro": (lambda: self.ro_val, None),
            "counter": (self.get_counter, None),
            "random_value": 1.234,
            "sub_tree": {
                "message": "hello",
                "another_value": 501201,
                "interesting_pv": PvParameterAccessor(
                    "interesting_pv", "INTERESTING_PV", initial_value=3.141
                ),
                "deeper": {
                    "one": 1,
                    "two": 2.0,
                    "three": (lambda: self.three_val, None)
                }
            }
        }

        self.tree = PvParameterTree(self.params, builder=DummyPvBuilder())

        print(self.tree.has_external_params())
        self.tree.update_external_params()

        print("\n********************\n")

    def get_counter(self):
        self.counter += 1
        print(f"Getting counter with value {self.counter}")
        return self.counter

    def set_task_count(self, value):
        print(f"Task count setter called with value {value}")


@pytest.fixture(scope="class")
def test_pv_tree():
    pvt = PvTreeFixture()
    yield pvt


class TestPVParameterTree():

    def test_bound_simple_param_access(self, test_pv_tree):

        assert test_pv_tree.tree.sub_tree.deeper.one == 1
        test_pv_tree.tree.sub_tree.deeper.one = 2
        assert test_pv_tree.tree.sub_tree.deeper.one == 2

        assert test_pv_tree.tree.sub_tree.deeper.two == 2.0

    def test_bound_ro_accessor(self, test_pv_tree):

        initial_counter = test_pv_tree.tree.counter
        next_counter = test_pv_tree.tree.counter
        assert next_counter == initial_counter + 1

        print(test_pv_tree.tree.get("counter")["counter"])
        with pytest.raises(ParameterTreeError):
            test_pv_tree.tree.counter = 30

    def test_bound_param_access(self, test_pv_tree):

        assert test_pv_tree.tree.sub_tree.deeper.three == 3
        #test_pv_tree.tree.sub_tree.deeper.three += 1
        test_pv_tree.three_val += 1
        assert test_pv_tree.tree.sub_tree.deeper.three == 4

    def test_pv_parameter_access(self, test_pv_tree):


        assert test_pv_tree.tree.task_count == test_pv_tree.initial_task_count
        assert test_pv_tree.tree.get('task_count')['task_count'] == test_pv_tree.initial_task_count

        print(f">>> Update task count to {test_pv_tree.initial_task_count+1}")
        test_pv_tree.tree.task_count += 1
        print(">>> done")

        print(test_pv_tree.tree.task_count)
        print(test_pv_tree.tree.get("task_count", with_metadata=True))
    
        # assert test_pv_tree.tree.task_count == test_pv_tree.initial_task_count + 1
        # assert test_pv_tree.tree.get('task_count')['task_count'] == test_pv_tree.initial_task_count + 1

        # test_pv_tree.tree.set("task_count", test_pv_tree.tree.task_count + 1)
        # assert test_pv_tree.tree.task_count == test_pv_tree.initial_task_count + 2
        # assert test_pv_tree.tree.get('task_count')['task_count'] == test_pv_tree.initial_task_count + 2

        # data = test_pv_tree.tree.get("task_count", with_metadata=True)
        # assert data['task_count']['value'] == test_pv_tree.initial_task_count + 2
        # assert data['task_count']['writeable'] == True
        # assert data['task_count']['type'] == type(test_pv_tree.initial_task_count).__name__


