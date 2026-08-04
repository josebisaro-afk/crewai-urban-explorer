from crewai import Agent, Task

from tasks._common import city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str, context: list[Task]) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nRevisá los items JSON del contexto y asegurate de que TODO "
            "texto (name, description_es/description_en/description, "
            "fun_fact, historical_period, address) esté íntegramente en "
            "target_language. Reescribí vos mismo cualquier campo que esté en "
            "otro idioma o mezcle idiomas. No cambies nombres propios de "
            "lugares que no tienen traducción natural. Devolvé la lista "
            "completa corregida."
        ),
        expected_output="El mismo array JSON, con consistencia de idioma garantizada. Solo JSON.",
        agent=agent,
        context=context,
    )
