import pytest
from fastapi import HTTPException

import gears.gear.dependencies as gear_deps
import gears.gear.schema as gears_schema


class TestGearType:
    def test_climbing_gear_type_values(self):
        assert gears_schema.GearType.HARNESS == 9
        assert gears_schema.GearType.CLIMBING_SHOES == 10


class TestValidateGearType:
    @pytest.mark.parametrize("gear_type", [1, 8, 9, 10])
    def test_known_types_pass(self, gear_type):
        assert gear_deps.validate_gear_type(gear_type) is None

    @pytest.mark.parametrize("gear_type", [0, 11, 99])
    def test_unknown_types_raise_422(self, gear_type):
        with pytest.raises(HTTPException) as exc:
            gear_deps.validate_gear_type(gear_type)

        assert exc.value.status_code == 422
