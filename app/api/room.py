from fastapi import APIRouter, Depends, HTTPException
from app.redis import redis_client
from app.services.auth import get_current_user
from app.services.game import cleanup_room
from typing import Dict
import json

router = APIRouter(prefix="/room")

@router.get("/{room_id}")
async def get_room_info(room_id: str, current_user: Dict = Depends(get_current_user)):
    username = current_user["username"]
    assigned_room = await redis_client.get(f"assigned_room:{username}")
    if not assigned_room or assigned_room.decode() != room_id:
        raise HTTPException(status_code=403, detail="Not authorized for this room")
    room_data = await redis_client.hgetall(f"room:{room_id}")
    if not room_data:
        raise HTTPException(status_code=404, detail="Room not found")
    room_info = {
        "room_id": room_id,
        "status": room_data.get(b"status", b"unknown").decode(),
        "users": room_data.get(b"users", b"").decode().split(","),
    }
    return room_info

@router.get("/{room_id}/users")
async def get_room_users(room_id: str, current_user: Dict = Depends(get_current_user)):
    username = current_user["username"]
    assigned_room = await redis_client.get(f"assigned_room:{username}")
    if not assigned_room or assigned_room.decode() != room_id:
        raise HTTPException(status_code=403, detail="Not authorized for this room")
    room_data = await redis_client.hgetall(f"room:{room_id}")
    if not room_data or b"users" not in room_data:
        raise HTTPException(status_code=404, detail="Room not found")
    users = room_data[b"users"].decode().split(",")
    return {"users": users}

@router.post("/{room_id}/leave")
async def leave_room(room_id: str, current_user: Dict = Depends(get_current_user)):
    username = current_user["username"]
    assigned_room = await redis_client.get(f"assigned_room:{username}")
    if not assigned_room or assigned_room.decode() != room_id:
        raise HTTPException(status_code=403, detail="Not in this room")
    await redis_client.delete(f"assigned_room:{username}")
    room_key = f"room:{room_id}"
    room_data = await redis_client.hgetall(room_key)
    if room_data and b"users" in room_data:
        users = room_data[b"users"].decode().split(",")
        if username in users:
            users.remove(username)
            current_turn = int(room_data[b"current_turn"])
            if current_turn >= len(users) > 0:
                current_turn = 0
            if len(users) > 0:
                await redis_client.hset(room_key, mapping={
                    "users": ",".join(users),
                    "current_turn": str(current_turn)
                })
                await redis_client.publish(f"room_channel:{room_id}", json.dumps({
                    "type": "player_left",
                    "player": username
                }))
            else:
                await cleanup_room(room_id)
    return {"message": "Left room successfully"}