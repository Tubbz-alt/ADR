from adr.Components import FreeBody
from adr.World import Ambient
from vec import Vector2
import math
import pytest


@pytest.fixture
def freebody():
    env = Ambient()
    freebody = FreeBody(
        name='freebody',
        type='generic_freebody',
        mass=23.4,
        position_cg=Vector2(-0.2, 0.02),
        pitch_rot_inertia=5.2,
        ambient=env,
    )
    return freebody


def test_instantiation(freebody):
    assert(freebody.position_cg.x == -0.2)
    assert(freebody.position_cg.y == 0.02)
    assert(freebody.pitch_rot_inertia == 5.2)
    assert(freebody.ambient.temperature == 273.15)


def test_states(freebody):
    freebody.position = Vector2(15.1, 1.2)
    freebody.angle = math.radians(15)
    freebody.velocity = Vector2(12.1, 0.7)
    freebody.rot_velocity = 14
    assert(freebody.position == Vector2(15.1, 1.2))
    assert(freebody.angle == math.radians(15))
    assert(freebody.velocity == Vector2(12.1, 0.7))
    assert(freebody.rot_velocity == 14)