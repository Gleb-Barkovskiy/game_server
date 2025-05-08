from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from jose import jwt
from app.core.config import get_settings
from app.redis import redis_client
from app.services.auth import get_current_user
from app.services.game import add_user_to_pool, start_turn, process_votes
from typing import Dict
import json
import asyncio

router = APIRouter(prefix="/game")


@router.post("/join-pool")
async def join_pool(current_user: Dict = Depends(get_current_user)):
    username = current_user["username"]
    assigned_room = await redis_client.get(f"assigned_room:{username}")
    if assigned_room:
        room_id = assigned_room.decode()
        return {"message": "Already assigned to a room", "room_id": room_id}
    success = await add_user_to_pool(username)
    if success:
        return {"message": "Added to waiting pool"}
    else:
        return {"message": "Already in pool or assigned to a room"}


@router.get("/pending-room")
async def get_pending_room(current_user: Dict = Depends(get_current_user)):
    username = current_user["username"]
    room_id = await redis_client.get(f"assigned_room:{username}")
    if not room_id:
        raise HTTPException(status_code=404, detail="No room assigned yet")
    return {"room_id": room_id.decode()}


@router.websocket("/ws-user/{username}")
async def user_websocket(websocket: WebSocket, username: str, token: str):
    try:
        payload = jwt.decode(token, get_settings().JWT_SECRET_KEY, algorithms=[get_settings().JWT_ALGORITHM])
        token_username = payload.get("sub")
        if not token_username or token_username != username:
            await websocket.close(code=4001)
            return
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"user_channel:{username}")
        await websocket.accept()

        async def listener():
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    data_str = message['data'].decode('utf-8') if isinstance(message['data'], bytes) else message[
                        'data']
                    await websocket.send_text(data_str)

        task = asyncio.create_task(listener())
        try:
            while True:
                await websocket.receive_json()
        except WebSocketDisconnect:
            pass
        finally:
            task.cancel()
            await pubsub.unsubscribe(f"user_channel:{username}")
    except Exception as e:
        print("WebSocket error:", str(e))
        await websocket.close(code=4000)


@router.websocket("/ws/{room_id}")
async def room_websocket(websocket: WebSocket, room_id: str, token: str):
    try:
        payload = jwt.decode(token, get_settings().JWT_SECRET_KEY, algorithms=[get_settings().JWT_ALGORITHM])
        username = payload.get("sub")
        if not username:
            await websocket.close(code=4001)
            return
        assigned_room = await redis_client.get(f"assigned_room:{username}")
        if not assigned_room or assigned_room.decode() != room_id:
            await websocket.close(code=4003)
            return
        room_exists = await redis_client.exists(f"room:{room_id}")
        if not room_exists:
            await websocket.close(code=4004)
            return
        await websocket.accept()

        room_data = await redis_client.hgetall(f"room:{room_id}")
        users = room_data[b"users"].decode().split(",")
        await redis_client.sadd(f"room:{room_id}:connected", username)
        connected_users = await redis_client.scard(f"room:{room_id}:connected")
        print(f"User {username} connected to room {room_id}. Connected users: {connected_users}/{len(users)}")

        spy = room_data[b"spy"].decode()
        secret_location = room_data[b"secret_location"].decode()
        if username == spy:
            await websocket.send_text(json.dumps({
                "type": "role",
                "role": "spy",
                "locations": get_settings().LOCATION_LIST
            }))
        else:
            await websocket.send_text(json.dumps({
                "type": "role",
                "role": "player",
                "location": secret_location
            }))

        status = room_data[b"status"].decode()
        if status == "active":
            current_turn = int(room_data[b"current_turn"])
            questions = json.loads(room_data[b"questions"])
            previous_question = questions[-1]["question"] if questions else None
            await websocket.send_text(json.dumps({
                "type": "turn",
                "current_player": users[current_turn],
                "previous_question": previous_question,
                "is_last": current_turn == len(users) - 1
            }))

        if connected_users == len(users):
            game_started = await redis_client.hget(f"room:{room_id}", "game_started")
            print(f"Game started flag for room {room_id}: {game_started}")
            if not game_started or game_started.decode() != "true":
                await redis_client.hset(f"room:{room_id}", "game_started", "true")
                print(f"Starting game in room {room_id}")
                await start_turn(room_id, 0)
            else:
                print(f"Game in room {room_id} already started")
        else:
            print(f"Waiting for more players to connect to room {room_id}")

        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"room_channel:{room_id}")
        listener_task = asyncio.create_task(listen_to_room(websocket, pubsub))
        try:
            while True:
                data = await websocket.receive_json()
                room_data = await redis_client.hgetall(f"room:{room_id}")
                status = room_data[b"status"].decode()
                if status != "active" and status != "voting":
                    continue
                if "submit_turn" in data:
                    current_turn = int(room_data[b"current_turn"])
                    print(f"Received submit_turn from {username}, current_turn={current_turn}, users={users}")
                    if username == users[current_turn]:
                        answer = data.get("answer", "")
                        question = data.get("question", "")
                        questions = json.loads(room_data[b"questions"])
                        questions.append({
                            "player": username,
                            "answer": answer,
                            "question": question
                        })
                        await redis_client.hset(f"room:{room_id}", "questions", json.dumps(questions))
                        await redis_client.publish(f"room_channel:{room_id}", json.dumps({
                            "type": "new_submission",
                            "player": username,
                            "answer": answer,
                            "question": question
                        }))
                        next_turn = current_turn + 1
                        print(f"Updating current_turn to {next_turn} for room {room_id}, users length: {len(users)}")
                        await redis_client.hset(f"room:{room_id}", "current_turn", str(next_turn))
                        await start_turn(room_id, next_turn)
                    else:
                        print(f"Submission rejected: {username} does not match current player {users[current_turn]}")
                elif "guess" in data and username == spy:
                    guess = data["guess"].lower()
                    if guess == secret_location.lower():
                        await redis_client.publish(f"room_channel:{room_id}", json.dumps({
                            "type": "spy_win",
                            "spy": spy,
                            "location": secret_location
                        }))
                        await redis_client.hset(f"room:{room_id}", "status", "ended")
                    else:
                        await redis_client.publish(f"room_channel:{room_id}", json.dumps({
                            "type": "spy_lose",
                            "spy": spy,
                            "guess": guess,
                            "location": secret_location
                        }))
                        await redis_client.hset(f"room:{room_id}", "status", "ended")
                elif "vote" in data and status == "voting":
                    voted_for = data["vote"]
                    if voted_for:
                        votes = json.loads(room_data[b"votes"])
                        votes[username] = voted_for
                        await redis_client.hset(f"room:{room_id}", "votes", json.dumps(votes))
                        await redis_client.publish(f"room_channel:{room_id}", json.dumps({
                            "type": "vote_cast",
                            "player": username
                        }))
                        if len(votes) == len(users):
                            await process_votes(room_id)
        except WebSocketDisconnect:
            await redis_client.srem(f"room:{room_id}:connected", username)
            print(f"User {username} disconnected from room {room_id}")
        finally:
            listener_task.cancel()
            await pubsub.unsubscribe(f"room_channel:{room_id}")
    except Exception as e:
        print(f"Room WebSocket error: {str(e)}")
        await websocket.close(code=4000)


async def listen_to_room(websocket: WebSocket, pubsub):
    async for message in pubsub.listen():
        if message['type'] == 'message':
            data_str = message['data'].decode('utf-8') if isinstance(message['data'], bytes) else message['data']
            await websocket.send_text(data_str)