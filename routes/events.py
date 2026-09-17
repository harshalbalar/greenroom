"""
Server-Sent Events (SSE) endpoint for real-time task progress.

The client connects to GET /api/events/{task_id} and receives
a stream of progress updates until the task completes or fails.

Usage (JavaScript):
    const source = new EventSource('/api/events/abc123?token=...');
    source.onmessage = (e) => console.log(JSON.parse(e.data));
"""

import json
import asyncio
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from worker import task_manager

router = APIRouter(prefix="/api/events", tags=["events"])


async def _event_stream(task_id: str):
    """Generator that yields SSE events for a task."""
    last_progress = ""
    last_status = ""

    while True:
        status = task_manager.get_status(task_id)
        if not status:
            yield f"data: {json.dumps({'error': 'Task not found'})}\n\n"
            return

        current_status = status.get("status", "")
        current_progress = status.get("progress", "")

        # Send update if something changed
        if current_status != last_status or current_progress != last_progress:
            event = {
                "task_id": task_id,
                "status": current_status,
                "progress": current_progress,
            }

            # Include result if completed
            if current_status == "completed":
                event["result"] = status.get("result")
                yield f"data: {json.dumps(event)}\n\n"
                return

            # Include error if failed
            if current_status == "failed":
                event["error"] = status.get("error", "Unknown error")
                yield f"data: {json.dumps(event)}\n\n"
                return

            yield f"data: {json.dumps(event)}\n\n"
            last_status = current_status
            last_progress = current_progress

        await asyncio.sleep(1)  # Poll every second


@router.get("/{task_id}")
async def stream_task_events(
    task_id: str,
    token: str = Query(None, description="JWT token for auth"),
):
    """Stream task progress as Server-Sent Events.

    Note: SSE doesn't support Authorization headers natively,
    so the token is passed as a query parameter instead.
    """
    # In production, validate the token here.
    # For MVP, we trust that the task_id is unguessable (UUID).

    return StreamingResponse(
        _event_stream(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/{task_id}/status")
async def get_task_status(task_id: str):
    """Simple polling endpoint — returns current task status as JSON."""
    status = task_manager.get_status(task_id)
    if not status:
        return {"error": "Task not found"}
    return status
