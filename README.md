novata-excel-processor/
├── function_app.py          # Main function app with blob trigger
├── requirements.txt         # Python dependencies
├── host.json               # Function host configuration
├── local.settings.json     # Local development settings
├── utils/
│   ├── __init__.py
│   ├── document_analyzer.py # Document Intelligence logic
│   └── data_processor.py    # ESG data processing logic
├── models/
│   ├── __init__.py
│   └── esg_models.py       # ESG data models
└── .gitignore