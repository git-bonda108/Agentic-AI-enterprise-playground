import type { CatalogModel, ChatParams } from "@/lib/playground-types";

export type SnippetLang = "python" | "typescript" | "csharp" | "java" | "curl";

export const SNIPPET_LANGS: { id: SnippetLang; label: string }[] = [
  { id: "python", label: "Python" },
  { id: "typescript", label: "TypeScript" },
  { id: "csharp", label: "C#" },
  { id: "java", label: "Java" },
  { id: "curl", label: "curl" },
];

const esc = (s: string) => s.replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\n/g, "\\n");

/** The same request expressed against the playground's OpenAI-compatible gateway endpoint. */
export function buildSnippet(lang: SnippetLang, model: CatalogModel, prompt: string, params: ChatParams, gatewayUrl: string): string {
  const sys = params.system ? `{"role": "system", "content": "${esc(params.system)}"}, ` : "";
  const user = `{"role": "user", "content": "${esc(prompt || "Hello")}"}`;
  switch (lang) {
    case "python":
      return `from openai import OpenAI

client = OpenAI(base_url="${gatewayUrl}/v1", api_key="<your playground key>")

response = client.chat.completions.create(
    model="${model.id}",
    messages=[${sys}${user}],
    temperature=${params.temperature},
    max_tokens=${params.max_tokens},
    stream=True,
)
for chunk in response:
    print(chunk.choices[0].delta.content or "", end="")`;
    case "typescript":
      return `import OpenAI from "openai";

const client = new OpenAI({ baseURL: "${gatewayUrl}/v1", apiKey: "<your playground key>" });

const stream = await client.chat.completions.create({
  model: "${model.id}",
  messages: [${sys}${user}],
  temperature: ${params.temperature},
  max_tokens: ${params.max_tokens},
  stream: true,
});
for await (const chunk of stream) process.stdout.write(chunk.choices[0]?.delta?.content ?? "");`;
    case "csharp":
      return `using OpenAI;
using OpenAI.Chat;

var client = new ChatClient("${model.id}", new System.ClientModel.ApiKeyCredential("<your playground key>"),
    new OpenAIClientOptions { Endpoint = new Uri("${gatewayUrl}/v1") });

var messages = new List<ChatMessage> { ${params.system ? `new SystemChatMessage("${esc(params.system)}"), ` : ""}new UserChatMessage("${esc(prompt || "Hello")}") };
await foreach (var update in client.CompleteChatStreamingAsync(messages, new ChatCompletionOptions { Temperature = ${params.temperature}f, MaxOutputTokenCount = ${params.max_tokens} }))
    foreach (var part in update.ContentUpdate) Console.Write(part.Text);`;
    case "java":
      return `import com.openai.client.OpenAIClient;
import com.openai.client.okhttp.OpenAIOkHttpClient;
import com.openai.models.chat.completions.ChatCompletionCreateParams;

OpenAIClient client = OpenAIOkHttpClient.builder()
    .baseUrl("${gatewayUrl}/v1").apiKey("<your playground key>").build();

ChatCompletionCreateParams params = ChatCompletionCreateParams.builder()
    .model("${model.id}")${params.system ? `\n    .addSystemMessage("${esc(params.system)}")` : ""}
    .addUserMessage("${esc(prompt || "Hello")}")
    .temperature(${params.temperature}).maxCompletionTokens(${params.max_tokens})
    .build();
client.chat().completions().createStreaming(params).stream()
    .forEach(chunk -> chunk.choices().forEach(c -> c.delta().content().ifPresent(System.out::print)));`;
    case "curl":
      return `curl ${gatewayUrl}/v1/chat/completions \\
  -H "Authorization: Bearer <your playground key>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "${model.id}",
    "messages": [${sys}${user}],
    "temperature": ${params.temperature},
    "max_tokens": ${params.max_tokens},
    "stream": true
  }'`;
  }
}
