import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useDropzone } from 'react-dropzone';

const FileUpload: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [columns, setColumns] = useState<string[]>([]);
  const [timeColumn, setTimeColumn] = useState<string>('');
  const [valueColumns, setValueColumns] = useState<string[]>([]);
  const [previewData, setPreviewData] = useState<any[]>([]);
  
  const navigate = useNavigate();

  const onDrop = (acceptedFiles: File[]) => {
    const selectedFile = acceptedFiles[0];
    setFile(selectedFile);
    
    // Parse CSV for preview and column selection
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      const lines = text.split('\n');
      const headers = lines[0].split(',').map(h => h.trim());
      
      setColumns(headers);
      // Default time column to first column
      setTimeColumn(headers[0]);
      // Default value columns to all but first column
      setValueColumns(headers.slice(1));
      
      // Preview first few rows
      const previewRows = [];
      for (let i = 1; i < Math.min(6, lines.length); i++) {
        if (lines[i].trim()) {
          const rowData = lines[i].split(',').map(d => d.trim());
          const rowObj: any = {};
          headers.forEach((header, idx) => {
            rowObj[header] = rowData[idx];
          });
          previewRows.push(rowObj);
        }
      }
      setPreviewData(previewRows);
    };
    reader.readAsText(selectedFile);
  };

  const { getRootProps, getInputProps } = useDropzone({ 
    onDrop,
    accept: {
      'text/csv': ['.csv']
    } 
  });

  const handleTimeColumnChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selected = e.target.value;
    setTimeColumn(selected);
    // Update value columns (exclude the time column)
    setValueColumns(columns.filter(col => col !== selected));
  };

  const handleValueColumnChange = (column: string) => {
    setValueColumns(prev => {
      if (prev.includes(column)) {
        return prev.filter(col => col !== column);
      } else {
        return [...prev, column];
      }
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!file) {
      setError('Please select a file');
      return;
    }
    
    try {
      setLoading(true);
      setError('');
      
      const formData = new FormData();
      formData.append('file', file);
      formData.append('time_column', timeColumn);
      formData.append('value_columns', JSON.stringify(valueColumns));
      
      const response = await axios.post('http://localhost:8000/api/upload-csv/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      const analysisId = response.data.analysis_id;
      navigate(`/view/${analysisId}`);
      
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload file');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="file-upload-container">
      <h2>Upload Time Series Data</h2>
      
      <div {...getRootProps({ className: 'dropzone' })}>
        <input {...getInputProps()} />
        <p>Drag & drop a CSV file here, or click to select one</p>
      </div>
      
      {file && (
        <div className="file-info">
          <p>Selected file: {file.name}</p>
          
          {columns.length > 0 && (
            <div className="column-selection">
              <h3>Configure Time Series</h3>
              
              <div className="form-group">
                <label htmlFor="time-column">Time Column:</label>
                <select 
                  id="time-column" 
                  value={timeColumn} 
                  onChange={handleTimeColumnChange}
                >
                  {columns.map(col => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>
              
              <div className="form-group">
                <label>Value Columns:</label>
                <div className="checkbox-group">
                  {columns
                    .filter(col => col !== timeColumn)
                    .map(col => (
                      <div key={col} className="checkbox-item">
                        <input
                          type="checkbox"
                          id={`col-${col}`}
                          checked={valueColumns.includes(col)}
                          onChange={() => handleValueColumnChange(col)}
                        />
                        <label htmlFor={`col-${col}`}>{col}</label>
                      </div>
                    ))
                  }
                </div>
              </div>
              
              {previewData.length > 0 && (
                <div className="preview-data">
                  <h4>Data Preview</h4>
                  <table>
                    <thead>
                      <tr>
                        {columns.map(col => (
                          <th key={col}>{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {previewData.map((row, idx) => (
                        <tr key={idx}>
                          {columns.map(col => (
                            <td key={`${idx}-${col}`}>{row[col]}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              
              <button 
                className="submit-button" 
                onClick={handleSubmit}
                disabled={loading}
              >
                {loading ? 'Processing...' : 'Analyze Time Series'}
              </button>
              
              {error && <div className="error-message">{error}</div>}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default FileUpload;