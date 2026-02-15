from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import engine, Base, get_db
from app.models import Prayer
from app.schemas import PrayerIn

app = FastAPI(title="Prayers API")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.post("/add_prayer")
async def add_prayer(
    prayer: PrayerIn,
    db: AsyncSession = Depends(get_db)
):
    new_prayer = Prayer(
        prayer_name=prayer.prayer_name,
        request=prayer.request,
        phone=prayer.phone,
        contact_name=prayer.contact_name,
        tag_contact=prayer.tag_contact
       
    )

    db.add(new_prayer)
    await db.commit()
    await db.refresh(new_prayer)

    return {
        "status": "ok",
        "id": new_prayer.id
    }
