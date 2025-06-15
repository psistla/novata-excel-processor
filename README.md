# Novata Excel Processor

This project is an Azure Function App designed to automate the extraction and processing of ESG (Environmental, Social, Governance) metrics from Excel files. When an Excel file is uploaded to a designated Azure Blob Storage container, the function is triggered, analyzes the document using Azure AI Document Intelligence, processes the extracted data to identify ESG metrics, and outputs a structured JSON report to another Blob Storage container.

## Features

- **Blob-triggered processing:** Automatically processes Excel files uploaded to Azure Blob Storage.
- **Azure AI Document Intelligence:** Uses Azure's prebuilt models to extract tables, key-value pairs, and content from Excel files.
- **ESG Data Extraction:** Identifies and structures ESG metrics using customizable keyword patterns.
- **Structured Output:** Outputs a detailed JSON report with metrics, summary statistics, and processing metadata.
- **Robust Error Handling:** Handles validation and runtime errors, outputting error details as JSON.

## Project Structure

```
novata-excel-processor/
├── function_app.py              # Main Azure Function with blob trigger
├── requirements.txt             # Python dependencies
├── host.json                    # Azure Functions host configuration
├── local.settings.json          # Local development settings (not for production)
├── utils/
│   ├── __init__.py
│   ├── document_analyzer.py     # Azure Document Intelligence logic
│   └── data_processor.py        # ESG data processing logic
├── models/
│   ├── __init__.py
│   └── esg_models.py            # ESG data models
└── .gitignore
```

## Prerequisites

- Python 3.8 or later
- Azure Subscription
- [Azure Functions Core Tools](https://docs.microsoft.com/azure/azure-functions/functions-run-local)
- [Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli)
- An Azure Storage Account
- Azure AI Document Intelligence resource (endpoint & API key or managed identity)

## Local Development

1. **Clone the repository:**
   ```sh
   git clone <your-repo-url>
   cd novata-excel-processor
   ```

2. **Install dependencies:**
   ```sh
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure local settings:**
   - Copy `local.settings.example.json` to `local.settings.json` and fill in:
     - `AzureWebJobsStorage` (connection string for your storage account)
     - `DOCUMENTINTELLIGENCE_ENDPOINT`
     - `DOCUMENTINTELLIGENCE_API_KEY`
     - Optionally, set `USE_MANAGED_IDENTITY` to `"true"` if using managed identity.

4. **Run the function locally:**
   ```sh
   func start
   ```

## Deployment to Azure

### 1. Create Azure Resources

- **Resource Group:**
  ```sh
  az group create --name <your-resource-group> --location <region>
  ```

- **Storage Account:**
  ```sh
  az storage account create --name <yourstorageacct> --resource-group <your-resource-group> --sku Standard_LRS
  ```

- **Function App (Python):**
  ```sh
  az functionapp create --resource-group <your-resource-group> --consumption-plan-location <region> \
    --runtime python --runtime-version 3.8 --functions-version 4 \
    --name <your-function-app-name> --storage-account <yourstorageacct>
  ```

- **Azure AI Document Intelligence Resource:**  
  Create via [Azure Portal](https://portal.azure.com/) or CLI.

### 2. Configure Application Settings

Set the following application settings for your Function App (replace values as needed):

```sh
az functionapp config appsettings set --name <your-function-app-name> --resource-group <your-resource-group> --settings \
  DOCUMENTINTELLIGENCE_ENDPOINT="<your-endpoint>" \
  DOCUMENTINTELLIGENCE_API_KEY="<your-api-key>" \
  USE_MANAGED_IDENTITY="false"
```

If using managed identity, set `USE_MANAGED_IDENTITY="true"` and assign the identity access to the Document Intelligence resource.

### 3. Deploy the Code

```sh
func azure functionapp publish <your-function-app-name>
```

### 4. Set Up Blob Containers

- Create two containers in your storage account:
  - `input-files` (for uploading Excel files)
  - `output-files` (for processed JSON output)

### 5. Test the Function

- Upload an Excel file (`.xlsx`, `.xls`, or `.xlsm`) to the `input-files` container.
- The function will process the file and output a JSON report to the `output-files` container.

## Notes

- Ensure your Azure Function has network access to the Document Intelligence endpoint.
- For production, use managed identities and secure your API keys.
- Monitor logs via Azure Portal or Application Insights.

## License

MIT License

---

For more details, see the code in [function_app.py](function_app.py), [utils/document_analyzer.py](utils/document_analyzer.py), and [utils/data_processor.py](utils/data_processor.py).