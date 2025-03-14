import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import axios from 'axios';
import FileUpload from '../../frontend/src/components/FileUpload';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

// Mock useNavigate
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn(),
}));

describe('FileUpload Component', () => {
  
  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();
  });

  test('renders upload area', () => {
    render(
      <BrowserRouter>
        <FileUpload />
      </BrowserRouter>
    );
    
    expect(screen.getByText(/Upload Time Series Data/i)).toBeInTheDocument();
    expect(screen.getByText(/Drag & drop a CSV file here/i)).toBeInTheDocument();
  });

  test('handles file selection', async () => {
    render(
      <BrowserRouter>
        <FileUpload />
      </BrowserRouter>
    );
    
    // Create a mock file
    const file = new File(['timestamp,value\n2023-01-01,42'], 'test.csv', { type: 'text/csv' });
    
    // Get the file input
    const input = screen.getByText(/Drag & drop a CSV file here/i).closest('div');
    
    // Simulate dropping a file
    if (input) {
      fireEvent.drop(input, {
        dataTransfer: {
          files: [file],
        },
      });
    }
    
    // Check that file name is displayed
    await waitFor(() => {
      expect(screen.getByText(/Selected file: test.csv/i)).toBeInTheDocument();
    });
  });

  test('submits form and handles response', async () => {
    // Mock successful response
    mockedAxios.post.mockResolvedValueOnce({
      data: { 
        analysis_id: 'test-id',
        columns: ['timestamp', 'value'],
        time_column: 'timestamp',
        value_columns: ['value']
      }
    });
    
    render(
      <BrowserRouter>
        <FileUpload />
      </BrowserRouter>
    );
    
    // Create a mock file and trigger selection
    const file = new File(['timestamp,value\n2023-01-01,42'], 'test.csv', { type: 'text/csv' });
    const input = screen.getByText(/Drag & drop a CSV file here/i).closest('div');
    
    if (input) {
      fireEvent.drop(input, {
        dataTransfer: {
          files: [file],
        },
      });
    }
    
    // Wait for the form to be processed
    await waitFor(() => {
      expect(screen.getByText(/Selected file: test.csv/i)).toBeInTheDocument();
    });
    
    // Click the analyze button
    const analyzeButton = await screen.findByText(/Analyze Time Series/i);
    fireEvent.click(analyzeButton);
    
    // Verify axios was called correctly
    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalledWith(
        expect.stringContaining('/api/upload-csv/'),
        expect.any(FormData),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'multipart/form-data'
          })
        })
      );
    });
  });

  test('displays error message on API failure', async () => {
    // Mock error response
    mockedAxios.post.mockRejectedValueOnce({
      response: {
        data: {
          detail: 'Invalid CSV format'
        }
      }
    });
    
    render(
      <BrowserRouter>
        <FileUpload />
      </BrowserRouter>
    );
    
    // Create a mock file and trigger selection
    const file = new File(['invalid,format'], 'test.csv', { type: 'text/csv' });
    const input = screen.getByText(/Drag & drop a CSV file here/i).closest('div');
    
    if (input) {
      fireEvent.drop(input, {
        dataTransfer: {
          files: [file],
        },
      });
    }
    
    // Wait for the form to be processed
    await waitFor(() => {
      expect(screen.getByText(/Selected file: test.csv/i)).toBeInTheDocument();
    });
    
    // Click the analyze button
    const analyzeButton = await screen.findByText(/Analyze Time Series/i);
    fireEvent.click(analyzeButton);
    
    // Verify error message is displayed
    await waitFor(() => {
      expect(screen.getByText(/Invalid CSV format/i)).toBeInTheDocument();
    });
  });
});