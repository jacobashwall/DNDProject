# routers/combat.py
import random
import re
from fastapi import APIRouter, HTTPException, Request
from schemas import AttackRequest, CastRequest

# Create a router instance for this specific domain
router = APIRouter()

@router.post("/attack")
async def execute_attack(payload: AttackRequest, request: Request):
    # Access the database pool stored in the main app state
    async with request.app.state.pool.acquire() as connection:
        attacker = await connection.fetchrow("SELECT * FROM characters WHERE id = $1", payload.attacker_id)
        target = await connection.fetchrow("SELECT * FROM characters WHERE id = $1", payload.target_id)
        weapon = await connection.fetchrow("SELECT * FROM weapons WHERE id = $1", payload.weapon_id)

        owns_weapon = await connection.fetchval(
            "SELECT EXISTS(SELECT 1 FROM inventory WHERE character_id = $1 AND weapon_id = $2)",
            payload.attacker_id, payload.weapon_id
        )
        if not owns_weapon:
            raise HTTPException(status_code=400, detail="Character does not have this weapon equipped!")

        str_modifier = (attacker['strength'] - 10) // 2
        dex_modifier = (attacker['dexterity'] - 10) // 2

        if weapon['is_finesse']:
            attack_modifier = max(str_modifier, dex_modifier)
            used_stat = "STR" if str_modifier >= dex_modifier else "DEX"
        else:
            attack_modifier = str_modifier
            used_stat = "STR"

        d20_roll = random.randint(1, 20)
        attack_total = d20_roll + attack_modifier

        if attack_total >= target['armor_class']:
            match = re.match(r'(\d+)d(\d+)', weapon['damage_dice'])
            num_dice = int(match.group(1))
            dice_faces = int(match.group(2))

            dice_roll_total = sum(random.randint(1, dice_faces) for _ in range(num_dice))
            total_damage = dice_roll_total + attack_modifier
            new_hp = max(0, target['hp_current'] - total_damage)

            await connection.execute("UPDATE characters SET hp_current = $1 WHERE id = $2", new_hp, target['id'])

            return {
                "result": "HIT",
                "weapon_used": weapon['name'],
                "stat_used": used_stat,
                "damage_dealt": total_damage,
                "target_remaining_hp": new_hp,
                "narrative_hint": f"{attacker['name']} struck with their {weapon['name']} using {used_stat} for {total_damage} damage!"
            }
        else:
            return {"result": "MISS", "narrative_hint": f"{attacker['name']} missed."}


@router.post("/cast")
async def execute_spell(payload: CastRequest, request: Request):
    async with request.state.pool.acquire() as connection:
        caster = await connection.fetchrow("SELECT * FROM characters WHERE id = $1", payload.caster_id)
        target = await connection.fetchrow("SELECT * FROM characters WHERE id = $1", payload.target_id)

        # 1. Verify the caster has spell slots available
        slot_name = f"Level {payload.spell_level} Spell Slot"
        slots = await connection.fetchrow(
            "SELECT * FROM resource_slots WHERE character_id = $1 AND resource_name = $2",
            payload.caster_id, slot_name
        )

        if not slots or slots['current_amount'] <= 0:
            raise HTTPException(status_code=400, detail=f"Not enough {slot_name}s!")

        # 2. Deduct the spell slot (The Cost)
        await connection.execute(
            "UPDATE resource_slots SET current_amount = current_amount - 1 WHERE id = $1",
            slots['id']
        )

        # 3. Resolve the Spell (e.g., a simple damage spell)
        # Note: In a real app, you'd look up the spell's damage dice in a 'spells' database table.
        spell_damage = random.randint(1, 10)  # Simulating a 1d10 Firebolt
        new_hp = max(0, target['hp_current'] - spell_damage)

        # 4. Update Target HP
        await connection.execute(
            "UPDATE characters SET hp_current = $1 WHERE id = $2",
            new_hp, target['id']
        )

        return {
            "result": "SPELL CAST",
            "spell_used": payload.spell_name,
            "slots_remaining": slots['current_amount'] - 1,
            "damage_dealt": spell_damage,
            "target_remaining_hp": new_hp,
            "narrative_hint": f"{caster['name']} cast {payload.spell_name} and burned {target['name']} for {spell_damage} damage!"
        }