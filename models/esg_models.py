from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime

@dataclass
class ESGMetric:
    """Represents a single ESG metric."""
    category: str  # 'environmental', 'social', or 'governance'
    metric_name: str
    value: float
    unit: Optional[str] = None
    year: Optional[int] = None
    source_table: Optional[int] = None
    source_page: Optional[int] = None
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

@dataclass
class ESGReport:
    """Represents a complete ESG report."""
    filename: str
    extraction_date: str
    metrics: List[ESGMetric]
    summary: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "filename": self.filename,
            "extraction_date": self.extraction_date,
            "metrics": [metric.to_dict() for metric in self.metrics],
            "summary": self.summary,
            "metadata": self.metadata
        }