"""PDF export route — download travel plan as a professional PDF."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import require_user_or_above
from app.models.user import User
from app.models.travel import TravelPlan
from app.services.pdf_export import generate_itinerary_pdf
from app.services.audit import log_action, AuditActions

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/trips/{trip_id}/pdf")
async def export_trip_pdf(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user_or_above),
):
    """
    Download a travel plan as a professionally formatted PDF.
    Users can only export their own trips.
    """
    result = await db.execute(
        select(TravelPlan).where(
            TravelPlan.id == trip_id,
            TravelPlan.user_id == current_user.id,
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Travel plan not found")

    try:
        pdf_bytes = generate_itinerary_pdf(
            destination=plan.destination,
            start_date=str(plan.start_date) if plan.start_date else None,
            end_date=str(plan.end_date) if plan.end_date else None,
            itinerary=plan.itinerary,
            budget=plan.budget,
            weather_info=plan.weather_info,
            user_name=current_user.full_name,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Log the export
    await log_action(
        db=db,
        action=AuditActions.EXPORT_PDF,
        user_id=current_user.id,
        resource="travel_plan",
        resource_id=plan.id,
        detail=f"Exported PDF for: {plan.destination}",
    )

    safe_dest = plan.destination.replace(" ", "_").replace(",", "")[:40]
    filename = f"itinerary_{safe_dest}_{trip_id}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
