from fastapi import APIRouter, Depends
from soulra.core.auth import get_current_user
from soulra.models.user import User
from soulra.schemas.responses import SuccessResponse
from soulra.schemas.user import MeOut

router = APIRouter(tags=["me"])


@router.get(
    "/me",
    response_model=SuccessResponse[MeOut],
    summary="Get the current authenticated user's profile",
)
async def get_me(user: User = Depends(get_current_user)):
    return SuccessResponse(data=MeOut.model_validate(user))
