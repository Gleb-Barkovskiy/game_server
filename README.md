<h1>Spy Game Server API</h1>
<h2>Overview</h2>
<p>This is a FastAPI-based server for an online multiplayer game called Spy Game. The game involves players joining rooms where one player is randomly assigned as the <em>spy</em>, and others are given a secret location. Players take turns asking and answering questions to deduce who the spy is, while the spy tries to guess the secret location or avoid detection.</p>
<p>The server uses <strong>FastAPI</strong> for the API, <strong>Redis</strong> for real-time game state management and matchmaking, <strong>PostgreSQL</strong> for persistent user data, and <strong>WebSocket</strong> for real-time communication. The game supports user authentication, matchmaking, room management, and real-time gameplay interactions.</p>

<h2>Features</h2>
<ul>
        <li><strong>User Authentication</strong>: Register and login with JWT-based authentication.</li>
        <li><strong>Matchmaking</strong>: Players can join a waiting pool, and the server automatically creates game rooms when enough players (3–8) are available.</li>
        <li><strong>Gameplay</strong>:
            <ul>
                <li>Players are assigned roles (spy or player) and a secret location.</li>
                <li>Turns involve asking and answering questions to identify the spy.</li>
                <li>Voting rounds to eliminate suspected spies.</li>
                <li>The spy can guess the secret location to win.</li>
                <li>Game ends with either the spy winning (by guessing the location or surviving) or players winning (by identifying the spy).</li>
            </ul>
        </li>
        <li><strong>Real-Time Communication</strong>: WebSocket connections for user-specific updates and room-specific gameplay events.</li>
        <li><strong>Room Management</strong>: Players can join, leave, or get information about game rooms.</li>
        <li><strong>Timeouts</strong>: Automatic turn, voting, and game timeouts to ensure smooth gameplay.</li>
</ul>

<h2>Tech Stack</h2>
<ul>
        <li><strong>Backend</strong>: FastAPI (Python)</li>
        <li><strong>Database</strong>: PostgreSQL with SQLAlchemy (async)</li>
        <li><strong>Cache/Real-Time</strong>: Redis (async)</li>
        <li><strong>Authentication</strong>: JWT with OAuth2</li>
        <li><strong>WebSocket</strong>: FastAPI WebSocket support</li>
        <li><strong>CORS</strong>: Configured to allow cross-origin requests</li>
</ul>

<h2>API Endpoints</h2>

<h3>Authentication (<code>/auth</code>)</h3>
    <ul>
        <li><strong>POST /register</strong>: Register a new user.
            <ul>
                <li>Body: <code>{ "username": str, "email": str, "password": str }</code></li>
                <li>Response: <code>{ "access_token": str, "token_type": "bearer", "username": str }</code></li>
            </ul>
        </li>
        <li><strong>POST /login</strong>: Login and receive a JWT token.
            <ul>
                <li>Body: <code>{ "username": str, "password": str }</code></li>
                <li>Response: <code>{ "access_token": str, "token_type": "bearer", "username": str }</code></li>
            </ul>
        </li>
    </ul>

<h3>Game (<code>/game</code>)</h3>
    <ul>
        <li><strong>POST /join-pool</strong>: Add the authenticated user to the matchmaking pool.
            <ul>
                <li>Response: <code>{ "message": str, "room_id": str (optional) }</code></li>
            </ul>
        </li>
        <li><strong>GET /pending-room</strong>: Check if the user has been assigned to a room.
            <ul>
                <li>Response: <code>{ "room_id": str }</code></li>
            </ul>
        </li>
        <li><strong>WebSocket /ws-user/{username}</strong>: User-specific WebSocket for receiving room assignment and role updates.
            <ul>
                <li>Query: <code>?token=&lt;JWT&gt;</code></li>
            </ul>
        </li>
        <li><strong>WebSocket /ws/{room_id}</strong>: Room-specific WebSocket for gameplay events (turns, questions, votes, etc.).
            <ul>
                <li>Query: <code>?token=&lt;JWT&gt;</code></li>
            </ul>
        </li>
    </ul>

  <h3>Room (<code>/room</code>)</h3>
    <ul>
        <li><strong>GET /{room_id}</strong>: Get room information (status, users).
            <ul>
                <li>Response: <code>{ "room_id": str, "status": str, "users": list[str] }</code></li>
            </ul>
        </li>
        <li><strong>GET /{room_id}/users</strong>: Get the list of users in the room.
            <ul>
                <li>Response: <code>{ "users": list[str] }</code></li>
            </ul>
        </li>
        <li><strong>POST /{room_id}/leave</strong>: Leave the specified room.
            <ul>
                <li>Response: <code>{ "message": str }</code></li>
            </ul>
        </li>
    </ul>

<h2>WebSocket Communication</h2>

<h3>User WebSocket (<code>/game/ws-user/{username}</code>)</h3>
    <p>Receives messages like:</p>
    <ul>
        <li><code>assigned_room</code>: Informs the user of their room ID and role (<code>spy</code> or <code>player</code>).
            <ul>
                <li>Example (spy): <code>{ "type": "assigned_room", "room_id": str, "role": "spy", "locations": list[str] }</code></li>
                <li>Example (player): <code>{ "type": "assigned_room", "room_id": str, "role": "player", "location": str }</code></li>
            </ul>
        </li>
    </ul>

<h3>Room WebSocket (<code>/game/ws/{room_id}</code>)</h3>
    <p>Receives gameplay events:</p>
    <ul>
        <li><code>role</code>: Informs the user of their role and relevant data (e.g., spy gets location list, player gets secret location).</li>
        <li><code>turn</code>: Indicates the current player's turn, previous question, and whether it's the last turn.</li>
        <li><code>new_submission</code>: Broadcasts a player's question and answer.</li>
        <li><code>start_voting</code>: Signals the start of a voting round.</li>
        <li><code>vote_cast</code>: Notifies when a player casts a vote.</li>
        <li><code>voting_tie</code>: Indicates a tie in voting, triggering a new voting round.</li>
        <li><code>player_eliminated</code>: Notifies when a player is voted out.</li>
        <li><code>spy_win</code>/<code>players_win</code>: Announces the game outcome.</li>
        <li><code>spy_win_timeout</code>: Spy wins if the game exceeds 16 minutes.</li>
        <li><code>spy_win_two_players</code>: Spy wins if only two players remain.</li>
        <li><code>player_left</code>: Notifies when a player leaves the room.</li>
        <li><code>room_closed</code>: Informs players the room has been closed.</li>
    </ul>
    <p>Sends messages like:</p>
    <ul>
        <li><code>submit_turn</code>: <code>{ "submit_turn": true, "question": str, "answer": str }</code> (by the current player).</li>
        <li><code>guess</code>: <code>{ "guess": str }</code> (by the spy to guess the location).</li>
        <li><code>vote</code>: <code>{ "vote": str }</code> (to vote for a suspected spy).</li>
    </ul>

<h2>Game Rules</h2>
    <ul>
        <li><strong>Setup</strong>: 3–8 players per room. One is randomly chosen as the spy; others share a secret location.</li>
        <li><strong>Turns</strong>: Players take turns asking and answering questions to deduce the spy. Each turn has a 2.5-minute timeout.</li>
        <li><strong>Voting</strong>: After all turns, players vote to eliminate a suspected spy (1-minute timeout per voting round).</li>
        <li><strong>Win Conditions</strong>:
            <ul>
                <li><strong>Spy Wins</strong>: Guesses the correct location, survives until only two players remain, or the game exceeds 16 minutes.</li>
                <li><strong>Players Win</strong>: Correctly identify the spy through voting.</li>
            </ul>
        </li>
        <li><strong>Timeouts</strong>:
            <ul>
                <li>Turn: 2.5 minutes</li>
                <li>Voting: 1 minute</li>
                <li>Game: 16 minutes</li>
            </ul>
        </li>
        <li><strong>Room Cleanup</strong>: Rooms are automatically cleaned up after the game ends or if all players leave.</li>
    </ul>

<h2>Development Notes</h2>
    <ul>
        <li><strong>Redis Keys</strong>:
            <ul>
                <li><code>waiting_users</code>: Set of users in the matchmaking pool.</li>
                <li><code>assigned_room:{username}</code>: Tracks the room a user is assigned to (expires after 16 minutes).</li>
                <li><code>room:{room_id}</code>: Hash storing room data (e.g., users, spy, secret_location, status).</li>
                <li><code>room:{room_id}:connected</code>: Set of connected users in the room.</li>
                <li><code>room_channel:{room_id}</code>: Pub/sub channel for room events.</li>
                <li><code>user_channel:{username}</code>: Pub/sub channel for user-specific events.</li>
            </ul>
        </li>
        <li><strong>Timeouts</strong>: Implemented using <code>asyncio.create_task</code> to handle turn, voting, and game expirations.</li>
        <li><strong>SSL for Neon.tech</strong>: Configured in <code>database.py</code> to disable hostname verification for Neon.tech PostgreSQL.</li>
    </ul>

<h2>Contributing</h2>
    <ol>
        <li>Fork the repository.</li>
        <li>Create a feature branch (<code>git checkout -b feature/&lt;feature-name&gt;</code>).</li>
        <li>Commit changes (<code>git commit -m "Add feature"</code>).</li>
        <li>Push to the branch (<code>git push origin feature/&lt;feature-name&gt;</code>).</li>
        <li>Open a pull request.</li>
    </ol>

<h2>License</h2>
    <p>This project is licensed under the MIT License. See the <code>LICENSE</code> file for details.</p>
