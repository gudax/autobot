"""
WebSocket API endpoints
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import logging
import json

from app.services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/{channel}")
async def websocket_endpoint(
    websocket: WebSocket,
    channel: str
):
    """
    WebSocket endpoint for real-time updates

    Channels:
    - **dashboard**: General dashboard updates
    - **trading**: Trading signals and execution updates
    - **positions**: Position updates
    - **sessions**: Session status updates
    - **all**: All updates
    """
    await ws_manager.connect(websocket, channel)

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)

                # Handle client messages
                message_type = message.get("type")

                if message_type == "ping":
                    # Respond to ping with pong
                    await ws_manager.send_personal_message(
                        {"type": "pong", "timestamp": message.get("timestamp")},
                        websocket
                    )

                elif message_type == "subscribe":
                    # Subscribe to additional channel
                    new_channel = message.get("channel")
                    if new_channel and new_channel in ws_manager.channels:
                        ws_manager.channels[new_channel].add(websocket)
                        await ws_manager.send_personal_message(
                            {
                                "type": "subscribed",
                                "channel": new_channel,
                                "message": f"Subscribed to {new_channel}"
                            },
                            websocket
                        )

                elif message_type == "unsubscribe":
                    # Unsubscribe from channel
                    old_channel = message.get("channel")
                    if old_channel and old_channel in ws_manager.channels:
                        ws_manager.channels[old_channel].discard(websocket)
                        await ws_manager.send_personal_message(
                            {
                                "type": "unsubscribed",
                                "channel": old_channel,
                                "message": f"Unsubscribed from {old_channel}"
                            },
                            websocket
                        )

                elif message_type == "get_statistics":
                    # Send connection statistics
                    stats = ws_manager.get_statistics()
                    await ws_manager.send_personal_message(
                        {
                            "type": "statistics",
                            "data": stats
                        },
                        websocket
                    )

                else:
                    # Unknown message type
                    await ws_manager.send_personal_message(
                        {
                            "type": "error",
                            "error": f"Unknown message type: {message_type}"
                        },
                        websocket
                    )

            except json.JSONDecodeError:
                await ws_manager.send_personal_message(
                    {"type": "error", "error": "Invalid JSON"},
                    websocket
                )

            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}", exc_info=True)
                await ws_manager.send_personal_message(
                    {"type": "error", "error": str(e)},
                    websocket
                )

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info(f"Client disconnected from channel '{channel}'")

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        ws_manager.disconnect(websocket)


@router.websocket("/ws")
async def websocket_default(websocket: WebSocket):
    """
    Default WebSocket endpoint (subscribes to 'all' channel)
    """
    await websocket_endpoint(websocket, "all")
