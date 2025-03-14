# Time Series Analyzer API Documentation

This document provides information about the REST API endpoints available in the Time Series Analyzer application.

## Base URL

For local development, the base URL is:
```
http://localhost:8000
```

## Endpoints

### Health Check

**GET /api/health**

Check if the API is running properly.

**Response**:
```json
{
  "status": "healthy"
}
```

### Upload CSV

**POST /api/upload-csv/**

Upload a CSV file containing time series data for analysis.

**Parameters**:
- `file`: The CSV file to upload (required)
- `time_column`: Name of the column containing time data (optional)
- `value_columns`: List of column names to analyze (optional)

**Response**:
```json
{
  "analysis_id": "uuid-string",
  "columns": ["timestamp", "temperature", "humidity", "pressure"],
  "time_column": "timestamp",
  "value_columns": ["temperature", "humidity", "pressure"],
  "time_domain": {
    "time": ["2023-01-01 00:00:00", "2023-01-01 01:00:00", ...],
    "series": {
      "temperature": [22.5, 21.8, ...],
      "humidity": [45, 47, ...],
      "pressure": [1013.25, 1012.1, ...]
    }
  }
}
```

### Get Analysis

**GET /api/analyze/{analysis_id}**

Retrieve analysis results for a specific analysis ID.

**Parameters**:
- `analysis_id`: UUID of the analysis (path parameter, required)
- `domain`: Analysis domain, either "time" or "frequency" (query parameter, default: "time")

**Response**:
Same structure as the upload response, but may include frequency_domain data if requested:
```json
{
  "analysis_id": "uuid-string",
  "columns": ["timestamp", "temperature", "humidity", "pressure"],
  "time_column": "timestamp",
  "value_columns": ["temperature", "humidity", "pressure"],
  "time_domain": { ... },
  "frequency_domain": {
    "frequencies": {
      "temperature": [0.1, 0.2, ...],
      "humidity": [0.1, 0.2, ...],
      "pressure": [0.1, 0.2, ...]
    },
    "amplitudes": {
      "temperature": [1.2, 0.5, ...],
      "humidity": [0.8, 1.1, ...],
      "pressure": [0.3, 0.4, ...]
    }
  }
}
```

### Export Analysis

**GET /api/export/{analysis_id}**

Export analysis data in various formats.

**Parameters**:
- `analysis_id`: UUID of the analysis (path parameter, required)
- `format`: Export format, either "csv" or "json" (query parameter, default: "csv")
- `domain`: Analysis domain, either "time" or "frequency" (query parameter, default: "time")

**Response**:
- For CSV format: A downloadable CSV file
- For JSON format: Same as the analysis result JSON

## Error Responses

All endpoints may return error responses with appropriate HTTP status codes:

**400 Bad Request**:
```json
{
  "detail": "Error description"
}
```

**404 Not Found**:
```json
{
  "detail": "Analysis not found: uuid-string"
}
```

**500 Internal Server Error**:
```json
{
  "detail": "Error processing CSV: error description"
}
```