from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
import datetime
import uuid

# Core Data Types
class TextPart(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    text: str

class FilePart(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    media_type: str = Field(..., alias='mediaType')
    file_with_uri: Optional[str] = Field(None, alias='fileWithUri')
    file_with_bytes: Optional[str] = Field(None, alias='fileWithBytes')
    name: Optional[str] = None

class DataPart(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    data: Dict[str, Any]

class Part(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    text: Optional[str] = None
    file: Optional[FilePart] = None
    data: Optional[DataPart] = None
    metadata: Optional[Dict[str, Any]] = None

class Message(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    role: Literal["user", "agent"]
    parts: List[Part]
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias='messageId')
    context_id: Optional[str] = Field(None, alias='contextId')
    task_id: Optional[str] = Field(None, alias='taskId')
    metadata: Optional[Dict[str, Any]] = None
    extensions: Optional[List[str]] = None
    reference_task_ids: Optional[List[str]] = Field(None, alias='referenceTaskIds')

class TaskStatus(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    state: Literal[
        "submitted", "working", "completed", "failed", "cancelled", 
        "input-required", "rejected", "auth-required"
    ]
    message: Optional[Message] = None
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

class Artifact(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    artifact_id: str = Field(..., alias='artifactId')
    name: Optional[str] = None
    description: Optional[str] = None
    parts: List[Part]
    metadata: Optional[Dict[str, Any]] = None
    extensions: Optional[List[str]] = None

class Task(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str
    status: TaskStatus
    context_id: Optional[str] = Field(None, alias='contextId')
    history: Optional[List[Message]] = None
    artifacts: Optional[List[Artifact]] = None
    metadata: Optional[Dict[str, Any]] = None

# Request/Response Types
class SendMessageRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    message: Message
    configuration: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class StreamResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    task: Optional[Task] = None
    message: Optional[Message] = None
    status_update: Optional[TaskStatusUpdateEvent] = Field(None, alias='statusUpdate')
    artifact_update: Optional[TaskArtifactUpdateEvent] = Field(None, alias='artifactUpdate')

class TaskStatusUpdateEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    task_id: str = Field(..., alias='taskId')
    context_id: Optional[str] = Field(None, alias='contextId')
    status: TaskStatus
    final: bool = False
    metadata: Optional[Dict[str, Any]] = None

class TaskArtifactUpdateEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    task_id: str = Field(..., alias='taskId')
    context_id: Optional[str] = Field(None, alias='contextId')
    artifact: Artifact
    append: bool = False
    last_chunk: bool = Field(False, alias='lastChunk')
    metadata: Optional[Dict[str, Any]] = None

# Agent Card and Discovery Types
class AgentExtension(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    uri: str
    description: Optional[str] = None
    required: bool = False
    params: Optional[Dict[str, Any]] = None

class AgentCapabilities(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    streaming: bool = False
    push_notifications: bool = Field(False, alias='pushNotifications')
    state_transition_history: bool = Field(False, alias='stateTransitionHistory')
    extensions: Optional[List[AgentExtension]] = None

class AgentSkill(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str
    name: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    examples: Optional[List[str]] = None
    input_modes: Optional[List[str]] = Field(None, alias='inputModes')
    output_modes: Optional[List[str]] = Field(None, alias='outputModes')
    security: Optional[List[Dict[str, Any]]] = None

class AgentInterface(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    protocol_binding: str = Field(default="", alias='protocolBinding')
    url: str = Field(default="")

class AgentProvider(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    organization: Optional[str] = None
    url: Optional[str] = None

class SecurityScheme(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    # This is a simplified model. A full implementation would have models for each scheme type.
    type: str
    description: Optional[str] = None

class AgentCard(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    protocol_version: str = Field("1.0", alias='protocolVersion')
    name: str
    description: str
    provider: Optional[AgentProvider] = None
    capabilities: Optional[AgentCapabilities] = None
    skills: Optional[List[AgentSkill]] = None
    default_input_modes: Optional[List[str]] = Field(None, alias='defaultInputModes')
    default_output_modes: Optional[List[str]] = Field(None, alias='defaultOutputModes')
    supported_interfaces: Optional[List[AgentInterface]] = Field(None, alias='supportedInterfaces')
    security_schemes: Optional[Dict[str, SecurityScheme]] = Field(None, alias='securitySchemes')
    security: Optional[List[Dict[str, List[str]]]] = None
    icon_url: Optional[str] = Field(None, alias='iconUrl')
    documentation_url: Optional[str] = Field(None, alias='documentationUrl')
    version: Optional[str] = None
    supports_authenticated_extended_card: bool = Field(False, alias='supportsAuthenticatedExtendedCard')

    # For backward compatibility during migration
    url: Optional[str] = None