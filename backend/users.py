from fastapi import APIRouter, HTTPException, Request

import queries
from auth import get_current_user_id
from database import get_db
from geocoding import geocode_city
from models import CityUpdate

router = APIRouter()


@router.post("/city")
def update_city(body: CityUpdate, request: Request):
    user_id = get_current_user_id(request)

    coords = geocode_city(body.city)
    if not coords:
        raise HTTPException(
            status_code=400,
            detail=f"Could not geocode '{body.city}'. Try a more specific name, e.g. 'Cincinnati, OH'.",
        )

    lat, lng = coords
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(queries.UPDATE_CITY, {
                "user_id": user_id,
                "city": body.city,
                "lat": lat,
                "lng": lng,
            })
            # Wipe cached shows so /concerts re-fetches with the new coordinates
            cur.execute(queries.DELETE_USER_SHOWS, {"user_id": user_id})

    return {"ok": True, "lat": lat, "lng": lng}
