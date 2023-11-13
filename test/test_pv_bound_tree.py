import pytest

from odin_softioc.pv_parameter_tree import PvBoundTree, PvParameterAccessor, ParameterAccessor

ext_ro_val = 123

@pytest.fixture()
def bound_tree():

    def on_get():
        return ext_ro_val

    external_pv_param = PvParameterAccessor(
        "ext_pv_param", "EXT_PV_PARAM", on_get=on_get, writeable=False, param_type=int
    )
    external_pa_param = ParameterAccessor("ext_pa_param", on_get)

    tree = PvBoundTree(name='/')
    tree.bind(external_pv_param._name, external_pv_param)
    tree.bind("ext_pa_param", external_pa_param)

    yield tree

class TestPvBoundTree():

    def test_bound_tree_has_external_pv_param(self, bound_tree):

        assert "ext_pv_param" in bound_tree.external_params

    def test_bound_tree_has_external_pa_param(self, bound_tree):

        assert "ext_pa_param" in bound_tree.external_params
