import asyncio
import json
import os
import re

from asgiref.sync import sync_to_async
from django.conf import settings
from strawberry import ID
from strawberry.types import Info

from libs.models import EvaluationTask, GenerationTask, Rate
from libs.models.evaluation_task import Status as EvaluationTaskStatus
from libs.models.generation_task import Status as GenerationTaskStatus
from libs.services.gen_answer import chat_with_job_info

api_key = os.getenv("API_KEY", "EMPTY")


async def resolve(info: Info, generation_task_id: ID, eval_name: str, model: str, worker_count: int):
    user = info.context.user
    generation_task = await GenerationTask.objects.aget(id=generation_task_id, user=user, status=GenerationTaskStatus.COMPLETED)
    evaluation_task = await EvaluationTask.objects.acreate(
        user=user, generation_task=generation_task, name=eval_name, points={}, status=EvaluationTaskStatus.STARTED
    )

    templates = {}
    path = os.path.join(settings.BASE_DIR, "data", "japanese_mt_bench", "judge_ja_prompts.jsonl")
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            data = json.loads(line)
            templates[data["name"]] = data["prompt_template"]
    template = templates["single-v1"]

    try:
        jobs = []
        async for answer in generation_task.answers.order_by("id").all():
            question = answer.messages[0]["content"]
            content = template.format(question=question, answer=answer.text)
            messages = [
                {"role": "system", "content": "評価の点数は必ず[[評価]]の形式で示す。説明は簡潔にする。"},
                {"role": "user", "content": content},
            ]
            params = {"temperature": 0, "max_tokens": 1024}
            jobs.append(chat_with_job_info(answer, messages, model, host=None, api_key=api_key, params=params))
            if len(jobs) == worker_count:
                results = await asyncio.gather(*(asyncio.wait_for(job, timeout=180) for job in jobs), return_exceptions=True)
                jobs = []
                for result in results:
                    if isinstance(result, asyncio.exceptions.CancelledError):
                        raise Exception("Timeout")
                    match = re.search(r"\[\[(\d{1,2})\]\]", result["response"]["answer"])
                    point = int(match.group(1))
                    await Rate.objects.acreate(
                        user=user,
                        evaluation_task=evaluation_task,
                        answer=result["info"],
                        text=result["response"]["answer"],
                        usage=result["response"]["usage"],
                        finish_reason=result["response"]["finish_reason"],
                        processing_time=result["processing_time"],
                        point=point,
                        model=model,
                    )
        evaluation_task.status = EvaluationTaskStatus.COMPLETED
        await sync_to_async(lambda: evaluation_task.save())()
        return evaluation_task
    except Exception as e:
        print(e)
        evaluation_task.status = EvaluationTaskStatus.FAILED
        await sync_to_async(lambda: evaluation_task.save())()
        return evaluation_task
