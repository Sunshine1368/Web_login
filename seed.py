"""
seed.py - 创建测试数据：2 个用户、互加好友、若干聊天记录、游戏分数
用法：python seed.py
"""
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from app.database import AsyncSessionLocal, engine, Base
from app.models import User, UserSettings, Friend, ChatMessage, GameScore, Wallet
from app.utils.security import hash_password

TEST_USERS = [
    {"email": "alice@example.com", "username": "Alice", "password": "alice123"},
    {"email": "bob@example.com",   "username": "Bob",   "password": "bob12345"},
]


async def seed():
    # 确保表存在
    async with engine.begin() as conn:
        import app.models  # noqa
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        users = []
        for u_data in TEST_USERS:
            # 检查是否已存在
            result = await db.execute(select(User).where(User.email == u_data["email"]))
            user = result.scalar_one_or_none()
            if not user:
                user = User(
                    email=u_data["email"],
                    username=u_data["username"],
                    password_hash=hash_password(u_data["password"]),
                    is_active=True,
                )
                db.add(user)
                await db.flush()
                db.add(UserSettings(user_id=user.id))
                db.add(Wallet(user_id=user.id))
                print(f"  ✅ Created user: {user.username} (id={user.id})")
            else:
                print(f"  ⏭️  User already exists: {user.username} (id={user.id})")
            users.append(user)

        await db.flush()
        alice, bob = users[0], users[1]

        # ── 好友关系 ───────────────────────────────────────────────────────────
        result = await db.execute(
            select(Friend).where(Friend.user_id == alice.id, Friend.friend_id == bob.id)
        )
        if not result.scalar_one_or_none():
            friend = Friend(
                user_id=alice.id,
                friend_id=bob.id,
                status="accepted",
                action_user_id=bob.id,
            )
            db.add(friend)
            print(f"  ✅ Friend relationship: Alice <-> Bob")
        else:
            print(f"  ⏭️  Friend relationship already exists")

        # ── 聊天消息 ───────────────────────────────────────────────────────────
        result = await db.execute(select(ChatMessage).where(ChatMessage.from_user_id == alice.id))
        if not result.scalars().first():
            messages = [
                ChatMessage(from_user_id=alice.id, to_user_id=bob.id, message="Hey Bob! How are you?", is_read=True),
                ChatMessage(from_user_id=bob.id,   to_user_id=alice.id, message="Hi Alice! Doing great, thanks!", is_read=True),
                ChatMessage(from_user_id=alice.id, to_user_id=bob.id, message="Want to play Snake later?", is_read=True),
                ChatMessage(from_user_id=bob.id,   to_user_id=alice.id, message="Sure! My high score is 2500 😎", is_read=False),
                ChatMessage(from_user_id=alice.id, to_user_id=bob.id, message="Challenge accepted!", is_read=False),
            ]
            for m in messages:
                db.add(m)
            print(f"  ✅ Created {len(messages)} chat messages")

        # ── 游戏分数 ───────────────────────────────────────────────────────────
        result = await db.execute(select(GameScore).where(GameScore.user_id == alice.id))
        if not result.scalars().first():
            scores = [
                GameScore(user_id=alice.id, game_name="snake",  score=1800, extra_data={"level": 5, "duration_seconds": 120}),
                GameScore(user_id=alice.id, game_name="tetris", score=3200, extra_data={"lines_cleared": 42}),
                GameScore(user_id=bob.id,   game_name="snake",  score=2500, extra_data={"level": 7, "duration_seconds": 200}),
                GameScore(user_id=bob.id,   game_name="snake",  score=1500, extra_data={"level": 4, "duration_seconds": 90}),
                GameScore(user_id=bob.id,   game_name="tetris", score=4100, extra_data={"lines_cleared": 58}),
            ]
            for s in scores:
                db.add(s)
            print(f"  ✅ Created {len(scores)} game scores")

        await db.commit()
        print("\n🎉 Seed completed successfully!")
        print(f"\n  Test accounts:")
        for u_data in TEST_USERS:
            print(f"    Email: {u_data['email']}  Password: {u_data['password']}")


if __name__ == "__main__":
    asyncio.run(seed())
