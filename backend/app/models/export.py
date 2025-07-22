from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4


class ExportFormat(BaseModel):
    """Supported export format configuration"""

    name: str
    extension: str
    mime_type: str
    description: str
    supports_templates: bool = True
    supports_styling: bool = True
    ats_friendly: bool = False


class ExportTemplate(BaseModel):
    """Export template configuration"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    format_support: List[str] = []  # Supported formats

    # Template files
    template_files: Dict[str, str] = {}  # format -> file_path

    # Customization options
    customizable_sections: List[str] = []
    styling_options: Dict[str, Any] = {}

    # Template metadata
    category: Optional[str] = None
    industry: Optional[str] = None
    experience_level: Optional[str] = None

    # Usage statistics
    usage_count: int = 0
    rating: Optional[float] = Field(None, ge=0.0, le=5.0)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ExportRequest(BaseModel):
    """Single export request"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    resume_id: str

    # Export configuration
    format: str
    template: str
    filename: Optional[str] = None

    # Customization options
    include_metadata: bool = True
    ats_optimized: bool = False
    custom_styling: Dict[str, Any] = {}
    sections_to_include: List[str] = []

    # Optimization integration
    apply_optimizations: bool = True
    optimization_results: Optional[Dict[str, Any]] = None

    # Request metadata
    status: Literal["pending", "processing", "completed", "failed"] = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Output information
    output_path: Optional[str] = None
    file_size: Optional[int] = None
    download_url: Optional[str] = None

    # Error handling
    error_message: Optional[str] = None
    retry_count: int = 0


class BatchExportRequest(BaseModel):
    """Batch export request for multiple resume versions"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    batch_name: str

    # Export configurations
    export_requests: List[ExportRequest] = []
    output_format: Literal["zip", "individual"] = "zip"

    # Batch settings
    include_manifest: bool = True
    compress_output: bool = True

    # Status tracking
    status: Literal["pending", "processing", "completed", "failed", "partial"] = (
        "pending"
    )
    total_items: int = 0
    completed_items: int = 0
    failed_items: int = 0

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Output information
    output_path: Optional[str] = None
    total_size: Optional[int] = None
    download_url: Optional[str] = None

    # Progress tracking
    progress_percentage: float = 0.0
    current_item: Optional[str] = None
    estimated_completion: Optional[datetime] = None


class ExportHistory(BaseModel):
    """Export history tracking"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    export_request_id: str

    # Export details
    format: str
    template: str
    filename: str
    file_size: int

    # Download tracking
    download_count: int = 0
    last_downloaded: Optional[datetime] = None
    download_history: List[datetime] = []

    # File management
    file_path: str
    is_available: bool = True
    expires_at: Optional[datetime] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}


class ExportAnalytics(BaseModel):
    """Export analytics and usage statistics"""

    user_id: str

    # Usage statistics
    total_exports: int = 0
    exports_by_format: Dict[str, int] = {}
    exports_by_template: Dict[str, int] = {}

    # Popular combinations
    popular_format_template_combos: List[Dict[str, Any]] = []

    # Performance metrics
    average_export_time: float = 0.0
    success_rate: float = 0.0

    # User preferences
    preferred_formats: List[str] = []
    preferred_templates: List[str] = []

    # Time-based analytics
    exports_by_month: Dict[str, int] = {}
    peak_usage_hours: List[int] = []

    # Quality metrics
    average_file_size: float = 0.0
    download_to_export_ratio: float = 0.0

    last_updated: datetime = Field(default_factory=datetime.utcnow)


class ExportPreview(BaseModel):
    """Export preview information"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    export_request_id: str

    # Preview data
    preview_type: Literal["thumbnail", "html", "text"] = "html"
    preview_content: str
    preview_url: Optional[str] = None

    # Preview metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    # Preview settings
    include_styling: bool = True
    max_content_length: int = 5000


class ExportConfiguration(BaseModel):
    """Global export configuration settings"""

    # Supported formats
    supported_formats: List[ExportFormat] = []

    # Default settings
    default_format: str = "docx"
    default_template: str = "modern"

    # File management
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    retention_days: int = 30
    cleanup_frequency: int = 24  # hours

    # Performance settings
    max_concurrent_exports: int = 5
    batch_size_limit: int = 20
    timeout_seconds: int = 300

    # Storage settings
    storage_path: str = "generated"
    temp_path: str = "temp"
    archive_path: str = "archive"

    # Security settings
    allowed_file_types: List[str] = ["docx", "pdf", "txt", "json", "html"]
    scan_for_malware: bool = False

    # Feature flags
    enable_batch_export: bool = True
    enable_preview: bool = True
    enable_analytics: bool = True
    enable_compression: bool = True


class ExportError(BaseModel):
    """Export error information"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    export_request_id: str

    # Error details
    error_type: str
    error_message: str
    error_code: Optional[str] = None

    # Context information
    step_failed: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None

    # Recovery information
    is_recoverable: bool = False
    recovery_suggestions: List[str] = []

    # Timing
    occurred_at: datetime = Field(default_factory=datetime.utcnow)

    # Technical details
    stack_trace: Optional[str] = None
    system_info: Dict[str, Any] = {}


class ExportNotification(BaseModel):
    """Export completion notification"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    export_request_id: str

    # Notification details
    type: Literal["success", "failure", "warning"] = "success"
    title: str
    message: str

    # Action items
    download_url: Optional[str] = None
    retry_url: Optional[str] = None

    # Delivery settings
    delivery_method: List[Literal["in_app", "email", "webhook"]] = ["in_app"]

    # Status
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
