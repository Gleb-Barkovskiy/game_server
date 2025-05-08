import random
import asyncio
import json
from uuid import uuid4
from app.redis import redis_client
from app.core.config import get_settings
import time

settings = get_settings()


async def add_user_to_pool(username: str):
    assigned_room = await redis_client.get(f"assigned_room:{username}")
    if assigned_room:
        print(f"User {username} already has room: {assigned_room.decode()}")
        return False
    await redis_client.sadd("waiting_users", username)
    print(f"Added {username} to waiting pool")
    return True


async def find_match():
    count = await redis_client.scard("waiting_users")
    if count >= 3:
        users = await redis_client.srandmember("waiting_users", number=8)
        users = [u.decode('utf-8') for u in users]
        if len(users) >= 3:
            room_id = str(uuid4())
            secret_location = random.choice(settings.LOCATION_LIST)
            spy = random.choice(users)
            room_key = f"room:{room_id}"
            await redis_client.hset(room_key, mapping={
                "secret_location": secret_location,
                "spy": spy,
                "users": ",".join(users),
                "status": "active",
                "current_turn": "0",
                "questions": json.dumps([]),
                "votes": json.dumps({}),
                "start_time": str(time.time()),
                "game_started": "false"
            })
            await redis_client.expire(room_key, 960)  # 16 minutes
            for user in users:
                await redis_client.srem("waiting_users", user)
                await redis_client.setex(f"assigned_room:{user}", 960, room_id)
                if user == spy:
                    await redis_client.publish(f"user_channel:{user}", json.dumps({
                        "type": "assigned_room",
                        "room_id": room_id,
                        "role": "spy",
                        "locations": settings.LOCATION_LIST
                    }))
                else:
                    await redis_client.publish(f"user_channel:{user}", json.dumps({
                        "type": "assigned_room",
                        "room_id": room_id,
                        "role": "player",
                        "location": secret_location
                    }))
            print(f"Room {room_id} created with users: {users}")
            asyncio.create_task(game_timeout(room_id))


async def start_turn(room_id: str, turn_index: int):
    room_key = f"room:{room_id}"
    room_data = await redis_client.hgetall(room_key)
    if not room_data or room_data[b"status"].decode() != "active":
        print(f"Cannot start turn in room {room_id}: Room does not exist or game is not active")
        return
    users = room_data[b"users"].decode().split(",")
    print(f"Starting turn in room {room_id}, turn_index={turn_index}, users={users}")
    if turn_index >= len(users):
        print(f"Starting voting in room {room_id}, turn_index={turn_index}, users length={len(users)}")
        await redis_client.hset(room_key, "status", "voting")
        await redis_client.publish(f"room_channel:{room_id}", json.dumps({"type": "start_voting"}))
        asyncio.create_task(voting_timeout(room_id))
        return
    current_player = users[turn_index]
    questions = json.loads(room_data[b"questions"])
    previous_question = questions[-1]["question"] if questions else None
    print(
        f"Sending turn message for room {room_id}: current_player={current_player}, turn_index={turn_index}, is_last={turn_index == len(users) - 1}")
    await redis_client.publish(f"room_channel:{room_id}", json.dumps({
        "type": "turn",
        "current_player": current_player,
        "previous_question": previous_question,
        "is_last": turn_index == len(users) - 1
    }))
    asyncio.create_task(turn_timeout(room_id, turn_index))


async def turn_timeout(room_id: str, turn_index: int):
    await asyncio.sleep(150)  # 2.5 minutes
    room_key = f"room:{room_id}"
    room_data = await redis_client.hgetall(room_key)
    if room_data and room_data[b"status"].decode() == "active" and int(room_data[b"current_turn"]) == turn_index:
        print(f"Turn timeout in room {room_id} for turn {turn_index}")
        next_turn = turn_index + 1
        await redis_client.hset(room_key, "current_turn", str(next_turn))
        await start_turn(room_id, next_turn)


async def process_votes(room_id: str):
    room_key = f"room:{room_id}"
    room_data = await redis_client.hgetall(room_key)
    votes = json.loads(room_data[b"votes"])
    users = room_data[b"users"].decode().split(",")

    vote_counts = {}
    for user in users:
        vote_counts[user] = 0
    for voter, voted_for in votes.items():
        if voted_for in vote_counts:
            vote_counts[voted_for] += 1

    max_votes = max(vote_counts.values())
    top_voted_players = [player for player, count in vote_counts.items() if count == max_votes]

    if len(top_voted_players) > 1:
        print(f"Tie in votes in room {room_id}: {top_voted_players} with {max_votes} votes each")
        # Reset votes and start a new voting round
        await redis_client.hset(room_key, "votes", json.dumps({}))
        await redis_client.publish(f"room_channel:{room_id}", json.dumps({
            "type": "voting_tie"
        }))
        await redis_client.hset(room_key, "status", "voting")
        asyncio.create_task(voting_timeout(room_id))
        return

    voted_player = top_voted_players[0]
    spy = room_data[b"spy"].decode()

    if voted_player == spy:
        await redis_client.publish(f"room_channel:{room_id}", json.dumps({
            "type": "players_win",
            "spy": spy
        }))
        await redis_client.hset(room_key, "status", "ended")
    else:
        users.remove(voted_player)

        await redis_client.hset(room_key, mapping={
            "users": ",".join(users),
            "current_turn": "0",
            "questions": json.dumps([]),
            "votes": json.dumps({}),
            "status": "active"
        })
        await redis_client.publish(f"room_channel:{room_id}", json.dumps({
            "type": "player_eliminated",
            "player": voted_player
        }))
        if len(users) == 2:
            await redis_client.publish(f"room_channel:{room_id}", json.dumps({
                "type": "spy_win_two_players",
                "spy": spy
            }))
            await redis_client.hset(room_key, "status", "ended")
        elif len(users) > 2:
            print(f"Starting new round in room {room_id} with remaining players: {users}")
            await start_turn(room_id, 0)
        else:
            await redis_client.publish(f"room_channel:{room_id}", json.dumps({
                "type": "spy_win",
                "spy": spy
            }))
            await redis_client.hset(room_key, "status", "ended")


async def voting_timeout(room_id: str):
    await asyncio.sleep(60)  # 1 minute
    room_key = f"room:{room_id}"
    room_data = await redis_client.hgetall(room_key)
    if room_data[b"status"].decode() == "voting":
        print(f"Voting timeout in room {room_id}")
        await process_votes(room_id)


async def game_timeout(room_id: str):
    await asyncio.sleep(960)  # 16 minutes
    room_key = f"room:{room_id}"
    room_data = await redis_client.hgetall(room_key)
    if room_data and room_data[b"status"].decode() == "active":
        spy = room_data[b"spy"].decode()
        await redis_client.publish(f"room_channel:{room_id}", json.dumps({
            "type": "spy_win_timeout",
            "spy": spy
        }))
        await redis_client.hset(room_key, "status", "ended")