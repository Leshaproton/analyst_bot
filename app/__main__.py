import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.access import AccessMiddleware
from app.config import load_config
from app.handlers.assessment import router as assessment_router
from app.handlers.common import router as common_router
from app.services.assessment import load_questions
from app.services.results import ResultsRepository


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    config = load_config()
    questions = load_questions()
    results_repository = ResultsRepository(config.database_path)
    results_repository.initialize()
    dispatcher = Dispatcher(questions=questions, results_repository=results_repository)
    access = AccessMiddleware(config.allowed_user_ids)
    dispatcher.message.outer_middleware(access)
    dispatcher.callback_query.outer_middleware(access)
    dispatcher.include_router(common_router)
    dispatcher.include_router(assessment_router)
    await dispatcher.start_polling(Bot(token=config.bot_token))


if __name__ == "__main__":
    asyncio.run(main())
