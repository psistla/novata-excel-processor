import azure.functions as func
import logging
import json
import os
from utils.document_analyzer import DocumentAnalyzerImproved
from utils.data_processor import ESGDataProcessor
from typing import Optional
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Initialize the function app
app = func.FunctionApp()

# Global initialization for better performance
doc_analyzer: Optional[DocumentAnalyzerImproved] = None
data_processor: Optional[ESGDataProcessor] = None

def get_analyzers():
    """Get or create analyzer instances."""
    global doc_analyzer, data_processor
    
    if doc_analyzer is None:
        use_managed_identity = os.environ.get("USE_MANAGED_IDENTITY", "false").lower() == "true"
        doc_analyzer = DocumentAnalyzerImproved(use_managed_identity=use_managed_identity)
    
    if data_processor is None:
        data_processor = ESGDataProcessor()
    
    return doc_analyzer, data_processor

@app.blob_trigger(
    arg_name="inputblob",
    path="input-files/{name}",
    connection="AzureWebJobsStorage"
)
@app.blob_output(
    arg_name="outputblob",
    path="output-files/{name}.json",
    connection="AzureWebJobsStorage"
)
def process_esg_excel(inputblob: func.InputStream, outputblob: func.Out[str]) -> None:
    """
    Azure Function triggered by blob upload to process ESG Excel files.
    
    Args:
        inputblob: Input Excel file from blob storage
        outputblob: Output JSON file to blob storage
    """
    # Create correlation ID for tracking
    import uuid
    correlation_id = str(uuid.uuid4())
    
    logging.info(f"[{correlation_id}] Processing ESG Excel file: {inputblob.name}")
    logging.info(f"[{correlation_id}] File size: {inputblob.length} bytes")
    
    # Initialize error output
    error_output = {
        "status": "error",
        "filename": inputblob.name,
        "correlation_id": correlation_id,
        "error": None,
        "details": None
    }
    
    try:
        # Get analyzer instances
        doc_analyzer, data_processor = get_analyzers()
        
        # Read the Excel file content
        excel_content = inputblob.read()
        
        # Analyze document with Azure AI Document Intelligence
        extracted_data = doc_analyzer.analyze_excel(
            excel_content, 
            inputblob.name
        )
        
        # Log extraction metrics
        logging.info(f"[{correlation_id}] Extraction complete. "
                    f"Tables: {len(extracted_data.get('tables', []))}, "
                    f"KV Pairs: {len(extracted_data.get('key_value_pairs', []))}")
        
        # Process and structure ESG data
        esg_data = data_processor.process_esg_data(extracted_data)
        
        # Add processing metadata
        esg_data["processing_metadata"] = {
            "correlation_id": correlation_id,
            "status": "success",
            "file_size_bytes": inputblob.length,
            "processing_timestamp": extracted_data.get("analysis_timestamp"),
            "document_intelligence_metadata": extracted_data.get("metadata", {})
        }
        
        # Convert to JSON and save
        output_json = json.dumps(esg_data, indent=2, ensure_ascii=False)
        outputblob.set(output_json)
        
        logging.info(f"[{correlation_id}] Successfully processed {inputblob.name}. "
                    f"Found {len(esg_data.get('metrics', []))} ESG metrics")
        
    except ValueError as ve:
        # Validation errors
        error_output["error"] = "Validation Error"
        error_output["details"] = str(ve)
        logging.error(f"[{correlation_id}] Validation error: {str(ve)}")
        outputblob.set(json.dumps(error_output, indent=2))
        
    except Exception as e:
        # Unexpected errors
        error_output["error"] = type(e).__name__
        error_output["details"] = str(e)
        error_output["traceback"] = traceback.format_exc()
        
        logging.error(f"[{correlation_id}] Error processing file {inputblob.name}: {str(e)}")
        logging.error(f"[{correlation_id}] Traceback: {traceback.format_exc()}")
        
        # Save error output
        outputblob.set(json.dumps(error_output, indent=2))
        
        # Re-raise to mark function execution as failed
        raise