"""
Builds a 7-day PracticeArc from a completed conversation's action steps and tradition cards.

Day layout:
  Days 1–6: action steps cycled (3 steps → days repeat 1-2-3-1-2-3)
  Day 7: always "Reflection & integration"
  Morning content: tradition cards cycled across days
  Evening prompt: derived from the day's task title
"""
import uuid
from datetime import datetime, timezone

from soulra.database import AsyncSessionLocal
from soulra.models.conversation import ActionStep, Conversation
from soulra.models.practice import PracticeArc, PracticeDay
from soulra.models.tradition_card import TraditionCard
from soulra.core.logging import logger

_WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_REFLECTION_TITLE = "Reflection & integration"
_REFLECTION_BODY = "Sit with what emerged this week. No new practice today."


def _day_label(arc_created_at: datetime, day_number: int) -> str:
    weekday = (arc_created_at.weekday() + day_number - 1) % 7
    return _WEEKDAY_LABELS[weekday]


def _build_days(arc: PracticeArc, steps: list[ActionStep], cards: list[TraditionCard]) -> list[PracticeDay]:
    days = []
    for day_num in range(1, 8):
        if day_num == 7:
            task_title = _REFLECTION_TITLE
            task_body = _REFLECTION_BODY
        else:
            step = steps[(day_num - 1) % len(steps)]
            task_title = step.title
            task_body = step.body

        card = cards[(day_num - 1) % len(cards)]
        evening_prompt = f'Did "{task_title.lower()}" show up today, even once? What did you notice?'

        days.append(PracticeDay(
            arc_id=arc.id,
            day_number=day_num,
            day_label=_day_label(arc.created_at, day_num),
            task_title=task_title,
            task_body=task_body,
            morning_quote=card.quote,
            morning_author=card.author,
            morning_citation=card.citation,
            morning_analysis=card.analysis,
            evening_prompt=evening_prompt,
            completed=False,
        ))
    return days


async def save_conversation_and_create_arc(
    conversation_id: str,
    thread_id: str,
    situation: str,
    clarify_q: str,
    clarify_ans: str,
    tradition_cards_data: list[dict],
    action_steps_data: list[dict],
    user_id: str,
) -> None:
    """Persist conversation, tradition cards, action steps and auto-build a practice arc."""
    if not tradition_cards_data or not action_steps_data:
        logger.warning("practice_skip_empty", thread_id=thread_id)
        return

    async with AsyncSessionLocal() as db:
        try:
            now = datetime.now(timezone.utc)

            conv = Conversation(
                id=uuid.UUID(conversation_id),
                user_id=user_id,
                thread_id=thread_id,
                situation=situation,
                clarify_q=clarify_q or None,
                clarify_ans=clarify_ans or None,
                created_at=now,
                completed_at=now,
            )
            db.add(conv)
            await db.flush()

            steps: list[ActionStep] = []
            for i, s in enumerate(action_steps_data):
                step = ActionStep(
                    conversation_id=conv.id,
                    step_number=i + 1,
                    title=s.get("title", ""),
                    body=s.get("body", ""),
                )
                db.add(step)
                steps.append(step)

            cards: list[TraditionCard] = []
            for i, c in enumerate(tradition_cards_data):
                card = TraditionCard(
                    conversation_id=conv.id,
                    card_order=i,
                    tradition=c.get("tradition", ""),
                    author=c.get("author", ""),
                    quote=c.get("quote", ""),
                    citation=c.get("citation", ""),
                    analysis=c.get("analysis", ""),
                    source_passage=c.get("source_passage", ""),
                )
                db.add(card)
                cards.append(card)

            await db.flush()

            arc = PracticeArc(
                conversation_id=conv.id,
                theme=situation[:120],
                status="active",
                current_day=1,
                created_at=now,
            )
            db.add(arc)
            await db.flush()

            for day in _build_days(arc, steps, cards):
                db.add(day)

            await db.commit()
            logger.info("practice_arc_created", conversation_id=str(conv.id))

        except Exception:
            await db.rollback()
            logger.exception("practice_arc_failed", thread_id=thread_id)
