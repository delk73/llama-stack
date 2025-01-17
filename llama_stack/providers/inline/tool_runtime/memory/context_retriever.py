# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.


from typing import List

from jinja2 import Template
from pydantic import BaseModel

from llama_stack.apis.common.content_types import InterleavedContent
from llama_stack.apis.inference import UserMessage
from llama_stack.providers.utils.inference.prompt_adapter import (
    interleaved_content_as_str,
)

from .config import (
    DefaultMemoryQueryGeneratorConfig,
    LLMMemoryQueryGeneratorConfig,
    MemoryQueryGenerator,
    MemoryQueryGeneratorConfig,
)


async def generate_rag_query(
    config: MemoryQueryGeneratorConfig,
    messages: List[InterleavedContent],
    **kwargs,
):
    """
    Generates a query that will be used for
    retrieving relevant information from the memory bank.
    """
    if config.type == MemoryQueryGenerator.default.value:
        query = await default_rag_query_generator(config, messages, **kwargs)
    elif config.type == MemoryQueryGenerator.llm.value:
        query = await llm_rag_query_generator(config, messages, **kwargs)
    else:
        raise NotImplementedError(f"Unsupported memory query generator {config.type}")
    return query


async def default_rag_query_generator(
    config: DefaultMemoryQueryGeneratorConfig,
    messages: List[InterleavedContent],
    **kwargs,
):
    return config.sep.join(interleaved_content_as_str(m) for m in messages)


async def llm_rag_query_generator(
    config: LLMMemoryQueryGeneratorConfig,
    messages: List[InterleavedContent],
    **kwargs,
):
    assert "inference_api" in kwargs, "LLMRAGQueryGenerator needs inference_api"
    inference_api = kwargs["inference_api"]

    m_dict = {
        "messages": [
            message.model_dump() if isinstance(message, BaseModel) else message
            for message in messages
        ]
    }

    template = Template(config.template)
    content = template.render(m_dict)

    model = config.model
    message = UserMessage(content=content)
    response = await inference_api.chat_completion(
        model_id=model,
        messages=[message],
        stream=False,
    )

    query = response.completion_message.content

    return query
