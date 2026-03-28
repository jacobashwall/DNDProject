from fastapi import APIRouter, HTTPException, Request

# Create a router instance for the Character domain
router = APIRouter()


@router.get("/{character_id}")
async def get_basic_character(character_id: str, request: Request):
    """Fetches just the basic stats (HP, AC, Attributes) for a character."""
    async with request.app.state.pool.acquire() as connection:
        row = await connection.fetchrow(
            "SELECT * FROM characters WHERE id = $1", character_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Character not found")

        return dict(row)


@router.get("/{character_id}/sheet")
async def get_full_character_sheet(character_id: str, request: Request):
    """
    Fetches the complete character state including Inventory (with weapon stats)
    and Resource Slots. This is the exact payload fed to the Flash-Lite AI models.
    """
    async with request.app.state.pool.acquire() as connection:
        # 1. Fetch Base Stats
        char_row = await connection.fetchrow(
            "SELECT * FROM characters WHERE id = $1", character_id
        )
        if not char_row:
            raise HTTPException(status_code=404, detail="Character not found")

        character_data = dict(char_row)

        # 2. Fetch Inventory and JOIN with the Weapons table
        # This tells the AI exactly how much damage their weapons do and if they have range
        inventory_rows = await connection.fetch(
            """
            SELECT w.id as weapon_id,
                   w.name,
                   w.damage_dice,
                   w.damage_type,
                   w.is_finesse,
                   w.range_normal,
                   i.quantity
            FROM inventory i
                     JOIN weapons w ON i.weapon_id = w.id
            WHERE i.character_id = $1
            """,
            character_id
        )
        # Convert the asyncpg Records into a standard list of dictionaries
        character_data['inventory'] = [dict(row) for row in inventory_rows]

        # 3. Fetch Available Spell Slots / Abilities
        resource_rows = await connection.fetch(
            """
            SELECT resource_name, total_amount, current_amount
            FROM resource_slots
            WHERE character_id = $1
            """,
            character_id
        )
        character_data['resources'] = [dict(row) for row in resource_rows]

        return character_data