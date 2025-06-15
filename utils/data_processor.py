import logging
from typing import Dict, Any, List
from datetime import datetime
import re
from models.esg_models import ESGMetric, ESGReport

class ESGDataProcessor:
    """Processes extracted data to identify and structure ESG metrics."""
    
    # Common ESG metric keywords and patterns
    ESG_KEYWORDS = {
        "environmental": [
            "carbon", "co2", "emission", "ghg", "greenhouse gas",
            "energy", "renewable", "waste", "water", "recycling",
            "biodiversity", "climate", "pollution", "sustainability"
        ],
        "social": [
            "employee", "diversity", "inclusion", "safety", "health",
            "community", "human rights", "labor", "training", "education",
            "customer satisfaction", "privacy", "data protection"
        ],
        "governance": [
            "board", "ethics", "compliance", "risk", "audit",
            "transparency", "corruption", "policy", "management",
            "shareholder", "stakeholder", "executive compensation"
        ]
    }
    
    def __init__(self):
        """Initialize the ESG data processor."""
        self.metric_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Compile regex patterns for ESG metrics identification."""
        patterns = {}
        for category, keywords in self.ESG_KEYWORDS.items():
            patterns[category] = [
                re.compile(rf'\b{keyword}\b', re.IGNORECASE) 
                for keyword in keywords
            ]
        return patterns
    
    def process_esg_data(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process extracted data to identify and structure ESG metrics.
        
        Args:
            extracted_data: Raw data from Document Intelligence
            
        Returns:
            Structured ESG report data
        """
        logging.info("Processing ESG data")
        
        # Initialize ESG report
        esg_report = ESGReport(
            filename=extracted_data.get("filename", ""),
            extraction_date=datetime.utcnow().isoformat(),
            metrics=[]
        )
        
        # Process tables to find ESG metrics
        if "tables" in extracted_data:
            for table_idx, table in enumerate(extracted_data["tables"]):
                metrics = self._extract_metrics_from_table(table, table_idx)
                esg_report.metrics.extend(metrics)
        
        # Process key-value pairs
        if "key_value_pairs" in extracted_data:
            for kvp in extracted_data["key_value_pairs"]:
                metric = self._process_key_value_pair(kvp)
                if metric:
                    esg_report.metrics.append(metric)
        
        # Analyze content for additional metrics
        if "content" in extracted_data:
            content_metrics = self._analyze_content(extracted_data["content"])
            esg_report.metrics.extend(content_metrics)
        
        # Calculate summary statistics
        esg_report.summary = self._calculate_summary(esg_report.metrics)
        
        return esg_report.to_dict()
    
    def _extract_metrics_from_table(self, table: Dict[str, Any], table_idx: int) -> List[ESGMetric]:
        """Extract ESG metrics from a table."""
        metrics = []
        
        # Organize cells by row
        rows = {}
        for cell in table.get("cells", []):
            row_idx = cell["row_index"]
            col_idx = cell["column_index"]
            
            if row_idx not in rows:
                rows[row_idx] = {}
            rows[row_idx][col_idx] = cell["content"]
        
        # Check if first row contains headers
        headers = rows.get(0, {})
        
        # Process data rows
        for row_idx in sorted(rows.keys()):
            if row_idx == 0:  # Skip header row
                continue
                
            row_data = rows[row_idx]
            
            # Try to identify ESG metrics in the row
            for col_idx, value in row_data.items():
                # Check if this might be a metric name
                category = self._categorize_text(value)
                if category:
                    # Look for associated values
                    metric_value = None
                    unit = None
                    
                    # Check adjacent cells for numeric values
                    for adj_col in range(col_idx + 1, max(row_data.keys()) + 1):
                        if adj_col in row_data:
                            parsed = self._parse_value(row_data[adj_col])
                            if parsed:
                                metric_value, unit = parsed
                                break
                    
                    if metric_value is not None:
                        metric = ESGMetric(
                            category=category,
                            metric_name=value,
                            value=metric_value,
                            unit=unit,
                            source_table=table_idx,
                            confidence=0.8  # Default confidence for table data
                        )
                        metrics.append(metric)
        
        return metrics
    
    def _process_key_value_pair(self, kvp: Dict[str, Any]) -> ESGMetric:
        """Process a key-value pair to extract ESG metric."""
        key = kvp.get("key", "")
        value = kvp.get("value", "")
        confidence = kvp.get("confidence", 0.5)
        
        category = self._categorize_text(key)
        if category:
            parsed = self._parse_value(value)
            if parsed:
                metric_value, unit = parsed
                return ESGMetric(
                    category=category,
                    metric_name=key,
                    value=metric_value,
                    unit=unit,
                    confidence=confidence
                )
        
        return None
    
    def _analyze_content(self, content: str) -> List[ESGMetric]:
        """Analyze free text content for ESG metrics."""
        metrics = []
        
        # Split content into sentences
        sentences = re.split(r'[.!?]+', content)
        
        for sentence in sentences:
            # Look for patterns like "X metric: Y value"
            match = re.search(r'([^:]+):\s*([0-9,.\s]+)([a-zA-Z%]*)', sentence)
            if match:
                metric_name = match.group(1).strip()
                value_str = match.group(2).strip()
                unit = match.group(3).strip()
                
                category = self._categorize_text(metric_name)
                if category:
                    try:
                        value = float(value_str.replace(',', ''))
                        metric = ESGMetric(
                            category=category,
                            metric_name=metric_name,
                            value=value,
                            unit=unit or None,
                            confidence=0.6  # Lower confidence for content extraction
                        )
                        metrics.append(metric)
                    except ValueError:
                        pass
        
        return metrics
    
    def _categorize_text(self, text: str) -> str:
        """Categorize text as E, S, or G based on keywords."""
        if not text:
            return None
            
        text_lower = text.lower()
        
        for category, patterns in self.metric_patterns.items():
            for pattern in patterns:
                if pattern.search(text_lower):
                    return category
        
        return None
    
    def _parse_value(self, value_str: str) -> tuple:
        """Parse a value string to extract numeric value and unit."""
        if not value_str:
            return None
            
        # Remove common formatting
        value_str = value_str.strip().replace(',', '')
        
        # Try to extract number and unit
        match = re.match(r'([0-9.]+)\s*([a-zA-Z%]*)', value_str)
        if match:
            try:
                value = float(match.group(1))
                unit = match.group(2) or None
                return (value, unit)
            except ValueError:
                pass
        
        return None
    
    def _calculate_summary(self, metrics: List[ESGMetric]) -> Dict[str, Any]:
        """Calculate summary statistics for ESG metrics."""
        summary = {
            "total_metrics": len(metrics),
            "metrics_by_category": {
                "environmental": 0,
                "social": 0,
                "governance": 0
            },
            "average_confidence": 0.0
        }
        
        if metrics:
            total_confidence = 0
            for metric in metrics:
                summary["metrics_by_category"][metric.category] += 1
                total_confidence += metric.confidence
            
            summary["average_confidence"] = total_confidence / len(metrics)
        
        return summary