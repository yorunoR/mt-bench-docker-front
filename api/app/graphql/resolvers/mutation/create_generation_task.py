import asyncio
import json
import os

from asgiref.sync import sync_to_async
from jinja2 import Template
from strawberry import ID
from strawberry.types import Info

from libs.models import Answer, Bench, GenerationSetting, GenerationTask, GenerationTaskTag, Tag
from libs.models.generation_task import Status as GenerationTaskStatus
from libs.services.gen_answer import chat_with_job_info

API_MAX_RETRY = 5


def parse_params_str(param_str):
    try:
        return json.loads(param_str)
    except Exception:
        return {}


answer_format = "回答の最後に、必ず、結果:[[数値]]の形式で最終結果を追加してください。[[と]]で囲った値を最終結果として抜き出します。"


async def resolve(
    info: Info,
    bench_code: str,
    name: str,
    model_name: str,
    host: str,
    worker_count: int,
    tag_ids: list[ID],
    param_str: str | None = None,
    description: str | None = None,
):
    api_key = "EMPTY"
    if model_name.startswith("gpt"):
        api_key = os.getenv("OPENAI_API_KEY")
    if model_name.startswith("gemini"):
        api_key = os.getenv("GEMINI_API_KEY")
    if model_name.startswith("claude"):
        api_key = os.getenv("ANTHROPIC_API_KEY")
    if model_name.startswith("command"):
        api_key = os.getenv("COHERE_API_KEY")
    if model_name.startswith("deepseek"):
        api_key = os.getenv("DEEPSEEK_API_KEY")

    parameters = parse_params_str(param_str)

    user = info.context.user
    bench = await Bench.objects.aget(code=bench_code)
    generation_task = await GenerationTask.objects.acreate(
        user=user, bench=bench, name=name, model_name=model_name, status=GenerationTaskStatus.STARTED, description=description
    )
    _generation_setting = await GenerationSetting.objects.acreate(
        user=user, generation_task=generation_task, host=host, worker_count=worker_count, parameters=parameters
    )

    async for tag in Tag.objects.filter(id__in=tag_ids):
        await GenerationTaskTag.objects.acreate(generation_task=generation_task, tag=tag)

    if not model_name.startswith("openai/"):
        host = None

    try:
        jobs = []

        if generation_task.bench.code == "jmt-multi":
            turn_count = 2
        else:
            turn_count = 1

        for index in range(turn_count):
            async for question in bench.questions.order_by("question_number").all():
                latest_generation_task = await GenerationTask.objects.filter(id=generation_task.id).afirst()
                if latest_generation_task.status == GenerationTaskStatus.ABORTED:
                    break

                settings = parameters.get(question.category) or parameters.get("default") or {}
                strategy = settings.get("strategy", "none")
                params = settings.get("params")

                if generation_task.bench.code == "aiw":
                    content = question.turns[index] + "\n" + answer_format
                    messages = [
                        {"role": "user", "content": content},
                    ]
                elif generation_task.bench.code == "bfcl":
                    system_template = Template(bench.system_template)
                    function = question.function
                    vars = {
                        "name": function["name"],
                        "description": function["description"],
                        "parameters_properties": function["parameters"]["properties"],
                    }
                    system_content = system_template.render(vars)
                    messages = [
                        # {"role": "system", "content": system_content},
                        {"role": "user", "content": system_content + "\n\n" + question.turns[index]},
                    ]
                elif generation_task.bench.code == "jmt-multi" and index > 0:
                    previous_answer = await Answer.objects.aget(generation_task=generation_task, question=question, turn_number=index)
                    messages = previous_answer.messages + [
                        {"role": "assistant", "content": previous_answer.text},
                        {"role": "user", "content": question.turns[index]},
                    ]
                else:
                    messages = [{"role": "user", "content": question.turns[index]}]

                session_id = generation_task.name.replace("/", "_") + "_" + str(generation_task.id)
                metadata = {
                    "session_id": session_id,
                    "trace_id": session_id + "." + f"{question.question_number:03}",
                    "tags": [strategy],
                }

                jobs.append(
                    chat_with_job_info(
                        question, messages, model_name, host, api_key=api_key, metadata=metadata, strategy=strategy, params=params
                    )
                )
                if len(jobs) == worker_count:
                    for i in range(API_MAX_RETRY):
                        results = await asyncio.gather(*(asyncio.wait_for(job, timeout=240) for job in jobs), return_exceptions=True)
                        if any(isinstance(result, (RuntimeError, TimeoutError, asyncio.CancelledError)) for result in results):
                            print(i)
                        else:
                            break
                    for result in results:
                        try:
                            if isinstance(result, (RuntimeError, TimeoutError, asyncio.CancelledError)):
                                raise Exception("Timeout")
                            await Answer.objects.acreate(
                                user=user,
                                generation_task=generation_task,
                                messages=result["response"]["question"],
                                text=result["response"]["answer"],
                                usage=result["response"]["usage"],
                                finish_reason=result["response"]["finish_reason"],
                                processing_time=result["processing_time"],
                                question=result["info"],
                                turn_number=index + 1,
                            )
                        except Exception as e:
                            print(result)
                            raise e
                    jobs = []

        if latest_generation_task.status != GenerationTaskStatus.ABORTED:
            generation_task.status = GenerationTaskStatus.COMPLETED
            await sync_to_async(lambda: generation_task.save())()
        return generation_task
    except Exception as e:
        print(e)
        print(question)
        generation_task.status = GenerationTaskStatus.FAILED
        await sync_to_async(lambda: generation_task.save())()
        raise e
