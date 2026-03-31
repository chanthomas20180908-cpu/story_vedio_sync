from google import genai

client = genai.Client()

response = client.models.generate_content(
    model="gemini-3-pro-preview",
    contents="Find the race condition in this multi-threaded C++ snippet: [code here]",
)

print(response.text)


Gemini 3 系列隆重登场
Gemini 3 Pro 是新系列中的首款模型，最适合需要广泛的世界知识和跨模态高级推理能力的复杂任务。

Gemini 3 Flash 是我们最新的 3 系列模型，具有专业级智能，但速度和价格与 Flash 相当。

Nano Banana Pro（也称为 Gemini 3 Pro Image）是我们迄今为止质量最高的图片生成模型。

所有 Gemini 3 模型目前均为预览版。

模型 ID	上下文窗口（输入 / 输出）	知识截点	定价（输入 / 输出）*
gemini-3-pro-preview	100 万 / 6.4 万	2025 年 1 月	2 美元 / 12 美元（<20 万个 token）
4 美元 / 18 美元（>20 万个 token）
gemini-3-flash-preview	100 万 / 6.4 万	2025 年 1 月	$0.50 / $3
gemini-3-pro-image-preview	65k / 32k	2025 年 1 月	$2（文本输入）/ $0.134（图片输出）**


思考等级
Gemini 3 系列模型默认使用动态思考来对提示进行推理。您可以使用 thinking_level 参数，该参数可控制模型在生成回答之前执行的内部推理过程的最大深度。Gemini 3 将这些级别视为相对的思考余量，而不是严格的令牌保证。

如果未指定 thinking_level，Gemini 3 将默认为 high。如果不需要复杂的推理，您可以将模型的思维水平限制为 low，以获得更快、延迟更低的回答。

Gemini 3 Pro 和 Flash 的思考水平：

Gemini 3 Pro 和 Gemini 3 Flash 均支持以下思考级别：

low：最大限度地缩短延迟时间并降低费用。最适合简单指令遵循、聊天或高吞吐量应用
high（默认，动态）：最大限度地提高推理深度。模型可能需要更长时间才能生成第一个 token，但输出结果的推理会更加严谨。
Gemini 3 Flash 思维水平

除了上述级别之外，Gemini 3 Flash 还支持以下 Gemini 3 Pro 目前不支持的思维级别：

minimal：与大多数查询的“不思考”设置相匹配。对于复杂的编码任务，该模型可能只会进行非常简单的思考。最大限度地缩短聊天或高吞吐量应用的延迟时间。

注意： 即使将 Gemini 3 Flash 的思考级别设置为 minimal，也需要循环思考签名。
medium：针对大多数任务的平衡思考。

Python
JavaScript
REST

from google import genai
from google.genai import types

client = genai.Client()

response = client.models.generate_content(
    model="gemini-3-pro-preview",
    contents="How does AI work?",
    config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="low")
    ),
)

print(response.text)
重要提示： 您不能在同一请求中同时使用 thinking_level 和旧版 thinking_budget 参数。这样做会返回 400 错误。