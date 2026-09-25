from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str


class ChatParams(BaseModel):
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=128_000)
    top_p: float | None = Field(default=None, ge=0, le=1)
    system: str | None = None


class ChatStreamRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    params: ChatParams = Field(default_factory=ChatParams)
    conversation_id: str | None = None
    persist: bool = True
    feature: str = Field(default="chat", pattern="^(chat|compare)$")


class ConversationCreate(BaseModel):
    title: str = "New conversation"
    model: str
    system_prompt: str = ""
    tags: list[str] = Field(default_factory=list)


class ConversationPatch(BaseModel):
    title: str | None = None
    tags: list[str] | None = None
    pinned: bool | None = None
    system_prompt: str | None = None
    model: str | None = None
