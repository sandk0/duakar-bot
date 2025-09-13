from pydantic import BaseModel, Field
from typing import Generic, TypeVar, Optional, Any, List, Dict
from datetime import datetime

T = TypeVar('T')


class PaginationSchema(BaseModel):
    """Pagination metadata"""
    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(..., ge=1, le=100, description="Items per page")
    total: int = Field(..., ge=0, description="Total number of items")
    pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class ResponseSchema(BaseModel, Generic[T]):
    """Generic response schema"""
    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[T] = Field(None, description="Response data")
    message: Optional[str] = Field(None, description="Response message")
    errors: Optional[List[str]] = Field(None, description="List of errors")
    pagination: Optional[PaginationSchema] = Field(None, description="Pagination metadata")


class PaginatedResponseSchema(BaseModel, Generic[T]):
    """Paginated response schema"""
    items: List[T] = Field(..., description="List of items")
    pagination: PaginationSchema = Field(..., description="Pagination metadata")


class FilterSchema(BaseModel):
    """Base filter schema"""
    search: Optional[str] = Field(None, description="Search query")
    date_from: Optional[datetime] = Field(None, description="Filter from date")
    date_to: Optional[datetime] = Field(None, description="Filter to date")
    sort_by: Optional[str] = Field("created_at", description="Sort field")
    sort_order: Optional[str] = Field("desc", regex="^(asc|desc)$", description="Sort order")


class StatsSchema(BaseModel):
    """Base statistics schema"""
    total: int = Field(..., ge=0, description="Total count")
    active: int = Field(..., ge=0, description="Active count")
    inactive: int = Field(..., ge=0, description="Inactive count")
    growth_rate: Optional[float] = Field(None, description="Growth rate percentage")


class MetadataSchema(BaseModel):
    """Metadata schema"""
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    version: Optional[str] = Field(None, description="Version information")
    tags: Optional[List[str]] = Field(None, description="Tags")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class HealthCheckSchema(BaseModel):
    """Health check response schema"""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Check timestamp")
    version: str = Field(..., description="Service version")
    uptime: float = Field(..., description="Service uptime in seconds")
    components: Dict[str, str] = Field(..., description="Component statuses")


class ErrorSchema(BaseModel):
    """Error response schema"""
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")