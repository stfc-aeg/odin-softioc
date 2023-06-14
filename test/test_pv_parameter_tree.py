import pytest

from odin_softioc.pv_parameter_tree import PvParameterAccessor, PvParameterTree, ParameterTreeError

def set_task_count(value):
    print(f"Task count setter called with value {value}")

def test_pv_parameter_tree():

    initial_task_count = 0
    three_val = 3
    params = {
        "task_count": PvParameterAccessor(
            "task_count", "BG_TASK_COUNT", set_task_count, initial_task_count, int
        ),
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
                "three": (lambda: three_val, None)
            }
        }
    }

    tree = PvParameterTree(params)

    print("\n****\n")

    # print(tree.get(''))
    # print(tree.task_count)
    # print(tree.get('task_count'))
    # print(tree.sub_tree.interesting_pv)
    # print(tree.sub_tree.deeper.two)
    # print(tree.get('sub_tree/interesting_pv', with_metadata=True))

    # print(tree.get('sub_tree/deeper/one'))
    # tree.set('sub_tree/deeper', {"one": 2})
    # print(tree.get('sub_tree/deeper/one'))
    # print(tree.sub_tree.deeper.one)
    # tree.sub_tree.deeper.one = 3
    # print(tree.get('sub_tree/deeper/one'))
    # print(tree.sub_tree.deeper.one)

    # print(tree.get("sub_tree/deeper/three"))
    # print(tree.sub_tree.deeper.one) #.three)
    # print(tree.task_count)
    # print(tree.sub_tree.message)

    # two_val = 2.0
    # quickie = ParameterTree({
    #     "one": 1,
    #     "two": (lambda: two_val, None)
    # })
    # print(quickie.get('', with_metadata=True))
    # print(quickie.get("one"))

    #quickie.set('', {"two": 3.0})

    assert tree.task_count == initial_task_count
    assert tree.get('task_count')['task_count'] == initial_task_count

    tree.task_count += 1
    assert tree.task_count == initial_task_count + 1
    assert tree.get('task_count')['task_count'] == initial_task_count + 1

    tree.set("task_count", tree.task_count + 1)
    assert tree.task_count == initial_task_count + 2
    assert tree.get('task_count')['task_count'] == initial_task_count + 2

    data = tree.get("task_count", with_metadata=True)
    assert data['task_count']['value'] == initial_task_count + 2
    assert data['task_count']['writeable'] == True
    assert data['task_count']['type'] == type(initial_task_count).__name__

    assert tree.sub_tree.deeper.one == 1
    tree.sub_tree.deeper.one = 2
    assert tree.sub_tree.deeper.one == 2

    assert tree.sub_tree.deeper.three == 3

    with pytest.raises(ParameterTreeError):
        tree.sub_tree.deeper.three = 4

