"""Tests for the Sonarr sensor platform."""
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from sonarr import SonarrError

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sonarr.const import DOMAIN
from homeassistant.const import (
    ATTR_ICON,
    ATTR_UNIT_OF_MEASUREMENT,
    DATA_GIGABYTES,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from tests.common import MockConfigEntry, async_fire_time_changed

UPCOMING_ENTITY_ID = f"{SENSOR_DOMAIN}.sonarr_upcoming"


async def test_sensors(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_sonarr: MagicMock,
) -> None:
    """Test the creation and values of the sensors."""
    entry = mock_config_entry
    registry = er.async_get(hass)

    # Pre-create registry entries for disabled by default sensors
    sensors = {
        "commands": "sonarr_commands",
        "diskspace": "sonarr_disk_space",
        "queue": "sonarr_queue",
        "series": "sonarr_shows",
        "wanted": "sonarr_wanted",
    }

    for (unique, oid) in sensors.items():
        registry.async_get_or_create(
            SENSOR_DOMAIN,
            DOMAIN,
            f"{entry.entry_id}_{unique}",
            suggested_object_id=oid,
            disabled_by=None,
        )

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    for (unique, oid) in sensors.items():
        entity = registry.async_get(f"sensor.{oid}")
        assert entity
        assert entity.unique_id == f"{entry.entry_id}_{unique}"

    state = hass.states.get("sensor.sonarr_commands")
    assert state
    assert state.attributes.get(ATTR_ICON) == "mdi:code-braces"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "Commands"
    assert state.state == "2"

    state = hass.states.get("sensor.sonarr_disk_space")
    assert state
    assert state.attributes.get(ATTR_ICON) == "mdi:harddisk"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == DATA_GIGABYTES
    assert state.attributes.get("C:\\") == "263.10/465.42GB (56.53%)"
    assert state.state == "263.10"

    state = hass.states.get("sensor.sonarr_queue")
    assert state
    assert state.attributes.get(ATTR_ICON) == "mdi:download"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "Episodes"
    assert state.attributes.get("The Andy Griffith Show S01E01") == "100.00%"
    assert state.state == "1"

    state = hass.states.get("sensor.sonarr_shows")
    assert state
    assert state.attributes.get(ATTR_ICON) == "mdi:television"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "Series"
    assert state.attributes.get("The Andy Griffith Show") == "0/0 Episodes"
    assert state.state == "1"

    state = hass.states.get("sensor.sonarr_upcoming")
    assert state
    assert state.attributes.get(ATTR_ICON) == "mdi:television"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "Episodes"
    assert state.attributes.get("Bob's Burgers") == "S04E11"
    assert state.state == "1"

    state = hass.states.get("sensor.sonarr_wanted")
    assert state
    assert state.attributes.get(ATTR_ICON) == "mdi:television"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "Episodes"
    assert state.attributes.get("Bob's Burgers S04E11") == "2014-01-26"
    assert state.attributes.get("The Andy Griffith Show S01E01") == "1960-10-03"
    assert state.state == "2"


@pytest.mark.parametrize(
    "entity_id",
    (
        "sensor.sonarr_commands",
        "sensor.sonarr_disk_space",
        "sensor.sonarr_queue",
        "sensor.sonarr_shows",
        "sensor.sonarr_wanted",
    ),
)
async def test_disabled_by_default_sensors(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    entity_id: str,
) -> None:
    """Test the disabled by default sensors."""
    registry = er.async_get(hass)

    state = hass.states.get(entity_id)
    assert state is None

    entry = registry.async_get(entity_id)
    assert entry
    assert entry.disabled
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION


async def test_availability(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_sonarr: MagicMock,
) -> None:
    """Test entity availability."""
    now = dt_util.utcnow()

    mock_config_entry.add_to_hass(hass)
    with patch("homeassistant.util.dt.utcnow", return_value=now):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert hass.states.get(UPCOMING_ENTITY_ID).state == "1"

    # state to unavailable
    mock_sonarr.calendar.side_effect = SonarrError

    future = now + timedelta(minutes=1)
    with patch("homeassistant.util.dt.utcnow", return_value=future):
        async_fire_time_changed(hass, future)
        await hass.async_block_till_done()

    assert hass.states.get(UPCOMING_ENTITY_ID).state == STATE_UNAVAILABLE

    # state to available
    mock_sonarr.calendar.side_effect = None

    future += timedelta(minutes=1)
    with patch("homeassistant.util.dt.utcnow", return_value=future):
        async_fire_time_changed(hass, future)
        await hass.async_block_till_done()

    assert hass.states.get(UPCOMING_ENTITY_ID).state == "1"

    # state to unavailable
    mock_sonarr.calendar.side_effect = SonarrError

    future += timedelta(minutes=1)
    with patch("homeassistant.util.dt.utcnow", return_value=future):
        async_fire_time_changed(hass, future)
        await hass.async_block_till_done()

    assert hass.states.get(UPCOMING_ENTITY_ID).state == STATE_UNAVAILABLE

    # state to available
    mock_sonarr.calendar.side_effect = None

    future += timedelta(minutes=1)
    with patch("homeassistant.util.dt.utcnow", return_value=future):
        async_fire_time_changed(hass, future)
        await hass.async_block_till_done()

    assert hass.states.get(UPCOMING_ENTITY_ID).state == "1"
