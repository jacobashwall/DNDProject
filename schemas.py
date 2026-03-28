# schemas.py
from pydantic import BaseModel

class AttackRequest(BaseModel):
    attacker_id: str
    target_id: str
    weapon_id: str

class CastRequest(BaseModel):
    caster_id: str
    target_id: str
    spell_name: str
    spell_level: int