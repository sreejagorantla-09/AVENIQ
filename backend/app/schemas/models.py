from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID

# ----------------------------------------------------
# 1. Merchant Schemas
# ----------------------------------------------------
class MerchantBase(BaseModel):
    merchant_code: str = Field(..., max_length=50)
    business_name: str = Field(..., max_length=255)
    business_type: Optional[str] = None
    description: Optional[str] = None
    website_url: Optional[str] = None
    country: Optional[str] = None
    currency: str = "INR"
    trust_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    status: str = "active"

class MerchantCreate(MerchantBase):
    pass

class MerchantResponse(MerchantBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ----------------------------------------------------
# 2. Merchant Policy Schemas
# ----------------------------------------------------
class MerchantPolicyBase(BaseModel):
    merchant_id: UUID
    policy_type: str = Field(..., description="spending_limit, return, refund, etc.")
    policy_name: str = Field(..., max_length=255)
    description: Optional[str] = None
    rules: Dict[str, Any] = Field(default_factory=dict)
    priority: int = 100
    is_active: bool = True

class MerchantPolicyCreate(MerchantPolicyBase):
    pass

class MerchantPolicyResponse(MerchantPolicyBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ----------------------------------------------------
# 3. Product Schemas
# ----------------------------------------------------
class ProductBase(BaseModel):
    merchant_id: UUID
    sku: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    price: float = Field(..., ge=0.0)
    currency: str = "INR"
    stock_quantity: int = Field(0, ge=0)
    status: str = "active"
    metadata: Optional[Dict[str, Any]] = None

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ----------------------------------------------------
# 4. AI Agent Schemas
# ----------------------------------------------------
class AiAgentBase(BaseModel):
    merchant_id: UUID
    agent_code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    agent_type: Optional[str] = None
    status: str = "active"
    capabilities: Optional[Dict[str, Any]] = None

class AiAgentCreate(AiAgentBase):
    pass

class AiAgentResponse(AiAgentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ----------------------------------------------------
# 5. Agent Request Schemas
# ----------------------------------------------------
class AgentRequestBase(BaseModel):
    agent_id: UUID
    merchant_id: UUID
    request_type: str
    raw_request: str
    structured_intent: Dict[str, Any] = Field(default_factory=dict)
    requested_action: Dict[str, Any] = Field(default_factory=dict)
    status: str = "received"

class AgentRequestCreate(AgentRequestBase):
    pass

class AgentRequestResponse(AgentRequestBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ----------------------------------------------------
# 6. Policy Decision Schemas
# ----------------------------------------------------
class PolicyDecisionBase(BaseModel):
    request_id: UUID
    merchant_id: UUID
    decision: str = Field(..., description="ALLOW, DENY, REQUIRE_APPROVAL")
    policy_results: Dict[str, Any] = Field(default_factory=dict)
    reason: Optional[str] = None

class PolicyDecisionCreate(PolicyDecisionBase):
    pass

class PolicyDecisionResponse(PolicyDecisionBase):
    id: UUID
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ----------------------------------------------------
# 7. Approval Schemas
# ----------------------------------------------------
class ApprovalBase(BaseModel):
    request_id: UUID
    merchant_id: UUID
    approval_type: Optional[str] = None
    requested_by: Optional[str] = None
    approved_by: Optional[str] = None
    status: str = "pending"
    reason: Optional[str] = None

class ApprovalCreate(ApprovalBase):
    pass

class ApprovalResponse(ApprovalBase):
    id: UUID
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# ----------------------------------------------------
# 8. Transaction Schemas
# ----------------------------------------------------
class TransactionBase(BaseModel):
    merchant_id: UUID
    request_id: UUID
    product_id: Optional[UUID] = None
    amount: float = Field(..., ge=0.0)
    currency: str = "INR"
    payment_provider: str
    provider_transaction_id: Optional[str] = None
    status: str
    metadata: Optional[Dict[str, Any]] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionResponse(TransactionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ----------------------------------------------------
# 9. Audit Event Schemas
# ----------------------------------------------------
class AuditEventBase(BaseModel):
    merchant_id: UUID
    agent_id: Optional[UUID] = None
    request_id: Optional[UUID] = None
    event_type: str
    actor_type: str = Field(..., description="agent, merchant, system, admin")
    actor_id: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    action: Optional[str] = None
    decision: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    previous_event_hash: Optional[str] = None
    event_hash: Optional[str] = None

class AuditEventCreate(AuditEventBase):
    pass

class AuditEventResponse(AuditEventBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
