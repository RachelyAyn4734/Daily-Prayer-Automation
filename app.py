from fastapi import FastAPI

from pydantic import BaseModel
from typing import Optional

from prayer_logic.add_prayers import add_prayer




app = FastAPI()


class PrayerRequest(BaseModel):
    prayer_name: str
    request: Optional[str] = None
    phone: Optional[str] = None
    contact_name: Optional[str] = None

    # האם לתייג את איש הקשר
    tag_contact: bool = False

    # לאן לשמור את הנתונים
    target_list: str = "default"


@app.post("/add_prayer")
def add_prayer_api(payload: PrayerRequest):
    add_prayer(
        prayer_name=payload.prayer_name,
        request=payload.request,
        phone=payload.phone,
        contact_name=payload.contact_name,
        tag_contact=payload.tag_contact,
        target_list=payload.target_list
    )

    return {
        "status": "ok",
        "message": "Prayer added successfully"
    }
@app.get("/ping")
def ping():
    return {"status": "alive"}

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000)

