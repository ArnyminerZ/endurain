"""Tests for gears.gear.dependencies.require_owned_gears."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

import core.exceptions as core_exceptions
import modules.gears.gear.dependencies as gear_dependencies
import modules.gears.gear.schema as gears_schema


@patch("modules.gears.gear.dependencies.gears_crud")
class TestRequireOwnedGears:
    """A client-supplied gear id is only accepted when it is the caller's."""

    def test_owned_gears_pass(self, mock_crud):
        mock_crud.get_gear_user_by_id.return_value = MagicMock()

        gear_dependencies.require_owned_gears(7, [1, 2], MagicMock())

        assert mock_crud.get_gear_user_by_id.call_count == 2

    def test_a_foreign_gear_is_not_found(self, mock_crud):
        mock_crud.get_gear_user_by_id.return_value = None

        with pytest.raises(core_exceptions.NotFoundError):
            gear_dependencies.require_owned_gears(7, [1], MagicMock())

    def test_clearing_a_gear_needs_no_lookup(self, mock_crud):
        gear_dependencies.require_owned_gears(7, [None], MagicMock())

        mock_crud.get_gear_user_by_id.assert_not_called()

    def test_a_repeated_id_is_looked_up_once(self, mock_crud):
        mock_crud.get_gear_user_by_id.return_value = MagicMock()

        gear_dependencies.require_owned_gears(7, [3, 3, None], MagicMock())

        mock_crud.get_gear_user_by_id.assert_called_once()


class TestGearType:
    def test_climbing_gear_type_values(self):
        assert gears_schema.GearType.HARNESS == 9
        assert gears_schema.GearType.CLIMBING_SHOES == 10


class TestValidateGearType:
    @pytest.mark.parametrize("gear_type", [1, 8, 9, 10])
    def test_known_types_pass(self, gear_type):
        assert gear_dependencies.validate_gear_type(gear_type) is None

    @pytest.mark.parametrize("gear_type", [0, 11, 99])
    def test_unknown_types_raise_422(self, gear_type):
        with pytest.raises(HTTPException) as exc:
            gear_dependencies.validate_gear_type(gear_type)

        assert exc.value.status_code == 422
