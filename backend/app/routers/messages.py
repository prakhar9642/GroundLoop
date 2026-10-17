"""Message submission endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..models import MessageSubmission
from ..protocol import ProtocolError
from ..service import GroundLoopService, InvalidStateError, MessageIdReuseError


router = APIRouter(prefix="/api")


@router.post("/messages")
def submit_message(payload: MessageSubmission, request: Request) -> JSONResponse:
    service: GroundLoopService = request.app.state.service
    try:
        result = service.submit_message(payload.raw_message)
    except ProtocolError as error:
        return JSONResponse(
            status_code=400,
            content={"error_code": error.code, "message": error.message},
        )
    except MessageIdReuseError as error:
        return JSONResponse(
            status_code=409,
            content={
                "error_code": "MESSAGE_ID_REUSE",
                "message": f"MID {error.args[0]} was already used with a different payload",
            },
        )
    except InvalidStateError as error:
        return JSONResponse(
            status_code=409,
            content={"error_code": "INVALID_STATE", "message": str(error)},
        )

    return JSONResponse(status_code=result.status_code, content=result.body)
