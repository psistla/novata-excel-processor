import os
import logging
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, ContentFormat
from typing import Dict, Any, List, Optional
import time
from functools import wraps

def retry_on_exception(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator for retrying functions on exception."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retry_delay = delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logging.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= backoff
            return None
        return wrapper
    return decorator

class DocumentAnalyzerImproved:
    """Enhanced document analyzer with better error handling and authentication."""
    
    # Maximum file size in MB
    MAX_FILE_SIZE_MB = 50
    
    def __init__(self, use_managed_identity: bool = False):
        """
        Initialize Document Intelligence client.
        
        Args:
            use_managed_identity: Use managed identity for authentication
        """
        endpoint = os.environ.get("DOCUMENTINTELLIGENCE_ENDPOINT")
        
        if not endpoint:
            raise ValueError("DOCUMENTINTELLIGENCE_ENDPOINT not configured")
        
        # Use managed identity in production, API key in development
        if use_managed_identity:
            credential = DefaultAzureCredential()
            logging.info("Using managed identity for authentication")
        else:
            api_key = os.environ.get("DOCUMENTINTELLIGENCE_API_KEY")
            if not api_key:
                raise ValueError("DOCUMENTINTELLIGENCE_API_KEY not configured")
            credential = AzureKeyCredential(api_key)
            logging.info("Using API key for authentication")
        
        self.client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=credential
        )
    
    def validate_file(self, excel_content: bytes, filename: str) -> None:
        """
        Validate the input file.
        
        Args:
            excel_content: File content
            filename: File name
            
        Raises:
            ValueError: If file validation fails
        """
        # Check file size
        file_size_mb = len(excel_content) / (1024 * 1024)
        if file_size_mb > self.MAX_FILE_SIZE_MB:
            raise ValueError(f"File size {file_size_mb:.2f}MB exceeds maximum {self.MAX_FILE_SIZE_MB}MB")
        
        # Check file extension
        valid_extensions = ['.xlsx', '.xls', '.xlsm']
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in valid_extensions:
            raise ValueError(f"Invalid file extension {file_ext}. Supported: {valid_extensions}")
        
        logging.info(f"File validation passed: {filename} ({file_size_mb:.2f}MB)")
    
    @retry_on_exception(max_retries=3, delay=2.0)
    def analyze_excel(self, excel_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Analyze Excel file using Document Intelligence with retry logic.
        
        Args:
            excel_content: Excel file content as bytes
            filename: Name of the Excel file
            
        Returns:
            Extracted data as dictionary
        """
        # Validate file first
        self.validate_file(excel_content, filename)
        
        logging.info(f"Starting Document Intelligence analysis for {filename}")
        
        try:
            # Start analysis
            poller = self.client.begin_analyze_document(
                model_id="prebuilt-layout",
                analyze_request=AnalyzeDocumentRequest(
                    bytes_source=excel_content
                ),
                features=["tables", "keyValuePairs"],
                output_content_format=ContentFormat.MARKDOWN,
                locale="en-US"  # Specify locale for better accuracy
            )
            
            # Poll with timeout
            result = poller.result(timeout=300)  # 5 minute timeout
            
            # Extract and structure data
            extracted_data = self._structure_results(result, filename)
            
            logging.info(f"Successfully analyzed {filename}. Found {len(extracted_data.get('tables', []))} tables")
            return extracted_data
            
        except Exception as e:
            logging.error(f"Failed to analyze document: {str(e)}")
            raise
    
    def _structure_results(self, result: Any, filename: str) -> Dict[str, Any]:
        """Structure the analysis results."""
        extracted_data = {
            "filename": filename,
            "analysis_timestamp": time.time(),
            "pages": [],
            "tables": [],
            "key_value_pairs": [],
            "content": "",
            "metadata": {
                "page_count": len(getattr(result, 'pages', [])),
                "table_count": len(getattr(result, 'tables', [])),
                "confidence_scores": []
            }
        }
        
        # Extract content with error handling
        if hasattr(result, 'content'):
            extracted_data["content"] = result.content
        
        # Process pages safely
        if hasattr(result, 'pages'):
            for page in result.pages:
                try:
                    page_data = self._extract_page_data(page)
                    extracted_data["pages"].append(page_data)
                except Exception as e:
                    logging.warning(f"Error processing page {getattr(page, 'page_number', 'unknown')}: {str(e)}")
        
        # Process tables with validation
        if hasattr(result, 'tables'):
            for idx, table in enumerate(result.tables):
                try:
                    table_data = self._extract_table_data(table, idx)
                    if table_data["cells"]:  # Only add non-empty tables
                        extracted_data["tables"].append(table_data)
                except Exception as e:
                    logging.warning(f"Error processing table {idx}: {str(e)}")
        
        # Process key-value pairs with confidence filtering
        if hasattr(result, 'key_value_pairs'):
            for kvp in result.key_value_pairs:
                try:
                    if self._is_valid_kvp(kvp):
                        kvp_data = {
                            "key": kvp.key.content if kvp.key else "",
                            "value": kvp.value.content if kvp.value else "",
                            "confidence": getattr(kvp, 'confidence', 0.0)
                        }
                        extracted_data["key_value_pairs"].append(kvp_data)
                        extracted_data["metadata"]["confidence_scores"].append(kvp_data["confidence"])
                except Exception as e:
                    logging.warning(f"Error processing key-value pair: {str(e)}")
        
        # Calculate average confidence
        if extracted_data["metadata"]["confidence_scores"]:
            avg_confidence = sum(extracted_data["metadata"]["confidence_scores"]) / len(extracted_data["metadata"]["confidence_scores"])
            extracted_data["metadata"]["average_confidence"] = avg_confidence
        
        return extracted_data
    
    def _extract_page_data(self, page: Any) -> Dict[str, Any]:
        """Extract data from a page object."""
        return {
            "page_number": getattr(page, 'page_number', 0),
            "width": getattr(page, 'width', 0),
            "height": getattr(page, 'height', 0),
            "unit": getattr(page, 'unit', 'pixel'),
            "lines": [
                {
                    "content": line.content,
                    "polygon": getattr(line, 'polygon', [])
                }
                for line in getattr(page, 'lines', [])
                if hasattr(line, 'content')
            ]
        }
    
    def _extract_table_data(self, table: Any, table_idx: int) -> Dict[str, Any]:
        """Extract and validate table data."""
        table_data = {
            "table_id": table_idx,
            "row_count": getattr(table, 'row_count', 0),
            "column_count": getattr(table, 'column_count', 0),
            "cells": [],
            "headers": []
        }
        
        if hasattr(table, 'cells'):
            # Sort cells by position
            sorted_cells = sorted(
                table.cells,
                key=lambda c: (c.row_index, c.column_index)
            )
            
            for cell in sorted_cells:
                cell_data = {
                    "row_index": cell.row_index,
                    "column_index": cell.column_index,
                    "content": cell.content.strip() if cell.content else "",
                    "row_span": getattr(cell, 'row_span', 1),
                    "column_span": getattr(cell, 'column_span', 1),
                    "is_header": cell.row_index == 0  # Assume first row is header
                }
                
                table_data["cells"].append(cell_data)
                
                # Extract headers
                if cell_data["is_header"]:
                    table_data["headers"].append(cell_data["content"])
        
        return table_data
    
    def _is_valid_kvp(self, kvp: Any) -> bool:
        """Check if a key-value pair is valid."""
        if not kvp:
            return False
        
        # Must have both key and value
        if not hasattr(kvp, 'key') or not hasattr(kvp, 'value'):
            return False
        
        # Check confidence threshold
        confidence = getattr(kvp, 'confidence', 0.0)
        if confidence < 0.5:  # Minimum confidence threshold
            return False
        
        return True