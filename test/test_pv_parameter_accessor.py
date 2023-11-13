import pytest

from odin_softioc.pv_parameter_tree import PvParameterAccessor, ParameterTreeError
from test.utils import DummyPvBuilder

int_ro_value = 0
int_rw_value = 1

ext_ro_value = 123
ext_rw_value = 987

@pytest.fixture()
def internal_ro_param():
    param_name = "int_ro"
    param = PvParameterAccessor(
        param_name, param_name.upper(), initial_value=int_ro_value, param_type=int
    )
    yield param

@pytest.fixture()
def internal_rw_param():
    param_name = "int_rw"
    param = PvParameterAccessor(
        param_name, param_name.upper(), writeable=True, initial_value=int_rw_value,
        param_type=int
    )
    yield param

@pytest.fixture()
def external_ro_param():

    def get_ro_param():
        print("get_ro_param called")
        return ext_ro_value

    param_name = "ext_ro"
    param = PvParameterAccessor(
        param_name, param_name.upper(), writeable=False, on_get=get_ro_param,
        initial_value=ext_ro_value, param_type=int
    )
    yield param

@pytest.fixture()
def external_rw_param():

    def on_get():
        return ext_rw_value

    def on_set(value):
        global ext_rw_value
        ext_rw_value = value

    param_name = "ext_rw"
    param = PvParameterAccessor(
        param_name, param_name.upper(), writeable=True, on_get=on_get, on_set=on_set,
        initial_value=ext_rw_value, param_type=int
    )
    yield param

class TestPvParameterAccessor():

    def test_internal_ro_param(self, internal_ro_param):

        # The parameter value should be as initialised
        assert internal_ro_param.get() == int_ro_value

        # The parameter writeable metadata flag should be False
        assert internal_ro_param.get(with_metadata=True)['writeable'] == False

        # Direct setting of internal value should update the parameter
        internal_ro_param._set(int_ro_value + 1)
        assert internal_ro_param.get() == int_ro_value + 1

        # External calls to set the parameter should raise an exception
        with pytest.raises(ParameterTreeError) as exc_info:
            internal_ro_param.set(int_ro_value + 2)

        assert f"Parameter {internal_ro_param._name} is read-only" in str(exc_info.value)

    def test_bound_internal_ro_param(self, internal_ro_param):

        # Bind the parameter to a dummy PV record
        internal_ro_param.bind(DummyPvBuilder())

        # Accessing the value of the parameter via the bound PV should give a consistent value
        param_val = internal_ro_param.get()
        assert internal_ro_param._pv.get() == param_val

        # Direct setting of internal value should update the parameter
        param_val += 1
        internal_ro_param._set(param_val)
        assert internal_ro_param._get() == param_val

        # Updating the parameter internally should also update the bound PV
        param_val += 1
        internal_ro_param._set(param_val)
        assert internal_ro_param._pv.get() == param_val 

    def test_internal_rw_param(self, internal_rw_param):

        # The parameter value should be as initialised
        assert internal_rw_param.get() == int_rw_value

        # The parameter writeable metadata flag should be True
        assert internal_rw_param.get(with_metadata=True)['writeable'] == True

        # Direct setting of the the internal value should update the parameter
        new_rw_value = int_rw_value + 3
        internal_rw_param._set(new_rw_value)
        assert internal_rw_param.get() == new_rw_value

        # External calls to set the parameter, e.g. via tree, should update the value
        new_rw_value = new_rw_value + 2
        internal_rw_param.set(new_rw_value)
        assert internal_rw_param.get() == new_rw_value

    def test_bound_internal_rw_param(self, internal_rw_param):

        # Bind the parameter to a dummy PV record
        internal_rw_param.bind(DummyPvBuilder())

        # Accessing the value of the parameter via the bound PV should give a consistent value
        param_val = internal_rw_param.get()
        assert internal_rw_param._pv.get() == param_val

        # Updating the parameter internally should also update the bound PV
        internal_rw_param._set(param_val + 1)
        assert internal_rw_param._pv.get() == param_val + 1

    def test_external_ro_param(self, external_ro_param):

        global ext_ro_value

        # The parameter value should match the external value
        assert external_ro_param.get() == ext_ro_value

        # The parameter should update if the external value changes
        ext_ro_value += 1
        assert external_ro_param.get() == ext_ro_value

        # External calls to set the parameter should raise an exception
        with pytest.raises(ParameterTreeError) as exc_info:
            external_ro_param.set(ext_ro_value + 2)

        assert f"Parameter {external_ro_param._name} is read-only" in str(exc_info.value)

    def test_bound_external_ro_param(self, external_ro_param):

        global ext_ro_value

        # Bind the parameter to a dummy PV record
        external_ro_param.bind(DummyPvBuilder())

        # Accessing the value of the parameter via the bound PV should give a consistent value
        param_val = external_ro_param.get()
        assert external_ro_param._pv.get() == param_val

        # The parameter should update if the external value changes
        ext_ro_value += 1
        assert external_ro_param._get() == ext_ro_value

        # Updating the external value should also update the bound PV
        ext_ro_value += 1
        external_ro_param._set(ext_ro_value)
        assert external_ro_param._pv.get() == ext_ro_value

    def test_external_rw_param(self, external_rw_param):

        global ext_rw_value

        # The parameter value should match the external value
        assert external_rw_param.get() == ext_rw_value

        # The parameter should updat eif the external value changes
        ext_rw_value += 1
        assert external_rw_param.get() == ext_rw_value

        # Setting the parameter should update the external value
        new_ext_val = ext_rw_value + 2
        external_rw_param.set(new_ext_val)
        assert external_rw_param.get() == new_ext_val
        assert ext_rw_value == new_ext_val

    def test_bound_external_rw_param(self, external_rw_param):

        # Bind the parameter to a dummy PV record
        external_rw_param.bind(DummyPvBuilder())

        # Accessing the value of the parameter via the bound PV should give a consistent value
        param_val = external_rw_param.get()
        assert external_rw_param._pv.get() == param_val

        # Updating the parameter externally should also update the bound PV
        external_rw_param._set(param_val + 1)
        assert external_rw_param._pv.get() == param_val + 1