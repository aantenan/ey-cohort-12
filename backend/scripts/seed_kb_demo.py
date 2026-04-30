"""Insert 200 demo published KB articles for local testing (WO-27 seed).

Run from `backend`: `uv run python scripts/seed_kb_demo.py`
"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import get_settings
from app.db.models.kb_article import ArticleStatus, KBArticle
from app.db.models.ticket_category import TicketCategory
from app.db.models.user import User

SEED_ENTRA_ID = "kb-demo-seed-user"
TITLE_PREFIX = "[KB Demo]"

CATEGORY_NAMES = [
    "Account Access",
    "VPN & Remote",
    "Email & Collaboration",
    "Hardware",
    "Software",
    "Security",
    "Network",
    "Cloud Services",
]

TOPICS = [
    "password reset",
    "MFA enrollment",
    "VPN tunnel troubleshooting",
    "Outlook sync issues",
    "Teams audio problems",
    "printer mapping",
    "disk encryption",
    "phishing awareness",
    "Wi-Fi connectivity",
    "Azure portal navigation",
    "license activation",
    "mobile device enrollment",
    "SharePoint permissions",
    "OneDrive sync",
    "SSL certificate renewal",
    "firewall exceptions",
    "DNS configuration",
    "backup verification",
    "service desk routing",
    "PowerShell basics",
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def main() -> None:
    settings = get_settings()
    random.seed(42)
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        # Categories
        cat_map: dict[str, TicketCategory] = {}
        for name in CATEGORY_NAMES:
            r = await session.exec(select(TicketCategory).where(TicketCategory.name == name))
            existing = r.first()
            if existing:
                cat_map[name] = existing
            else:
                tc = TicketCategory(name=name)
                session.add(tc)
                await session.commit()
                await session.refresh(tc)
                cat_map[name] = tc

        r = await session.exec(select(User).where(User.entra_object_id == SEED_ENTRA_ID))
        author = r.first()
        if author is None:
            author = User(entra_object_id=SEED_ENTRA_ID, email="kb-demo@example.com")
            session.add(author)
            await session.commit()
            await session.refresh(author)

        count_stmt = (
            select(func.count())
            .select_from(KBArticle)
            .where(KBArticle.author_id == author.id)
            .where(KBArticle.title.startswith(TITLE_PREFIX))
        )
        count_val = (await session.exec(count_stmt)).first()
        if count_val is None:
            have = 0
        elif isinstance(count_val, (int, float)):
            have = int(count_val)
        else:
            have = int(count_val[0])
        need = max(0, 200 - have)
        if need == 0:
            print(f"Already have {have} demo KB articles; nothing to insert.")
            await engine.dispose()
            return

        cats = list(cat_map.values())
        now = _utcnow()
        batch: list[KBArticle] = []
        for i in range(have, have + need):
            topic = TOPICS[i % len(TOPICS)]
            extra = random.choice(
                [
                    "VPN",
                    "Teams",
                    "Outlook",
                    "Azure AD",
                    "Intune",
                    "Windows",
                    "MacOS",
                    "Chrome",
                ]
            )
            title = f"{TITLE_PREFIX} {topic.title()} — guide #{i + 1}"
            body = (
                f"This article explains how to resolve {topic} issues involving {extra}. "
                f"Start by verifying connectivity, then review logs on the client. "
                f"Common symptoms include timeouts, certificate warnings, and stale credentials. "
                f"Escalate to the platform team if tenant-wide policies block access. "
                f"Keywords: {topic}, {extra}, troubleshooting, enterprise support.\n\n"
                f"Section 1: Prerequisites — ensure MFA is enrolled and device compliance passes.\n"
                f"Section 2: Steps — clear cache, renew tokens, and reconnect {extra}.\n"
                f"Section 3: Verification — confirm success in the admin portal.\n"
            )
            pub = now - timedelta(days=random.randint(0, 365))
            batch.append(
                KBArticle(
                    title=title[:500],
                    content=body,
                    category_id=random.choice(cats).id,
                    author_id=author.id,
                    status=ArticleStatus.published,
                    published_at=pub,
                    updated_at=_utcnow(),
                )
            )
        session.add_all(batch)
        await session.commit()
        print(f"Inserted {need} demo KB articles (total demo articles: {have + need}).")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
