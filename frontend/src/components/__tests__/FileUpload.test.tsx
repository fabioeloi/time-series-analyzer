import React from 'react';
import '@testing-library/jest-dom';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import axios from 'axios';
import FileUpload from '../FileUpload';

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
    jest.clearAllMocks();
  });

  test('renders upload area', () => {
    render(
      <BrowserRouter>
        <FileUpload />
      </BrowserRouter>
    );
    expect(screen.getByText(/Drag & drop a CSV file here/i)).toBeInTheDocument();
  });

  test('handles file upload', async () => {
    const { container } = render(
      <BrowserRouter>
        <FileUpload />
      </BrowserRouter>
    );

    const csvContent = 'timestamp,value\n2023-01-01,42';
    const file = new File([csvContent], 'test.csv', { type: 'text/csv' });
    const dropzone = container.querySelector('.dropzone');
    
    expect(dropzone).toBeTruthy();
    
    if (dropzone) {
      const inputEl = container.querySelector('input[type="file"]');
      expect(inputEl).toBeTruthy();
      
      if (inputEl) {
        Object.defineProperty(inputEl, 'files', {
          value: [file]
        });

        fireEvent.change(inputEl);
        
        await waitFor(() => {
          expect(screen.getByText(/Selected file: test.csv/i)).toBeInTheDocument();
        });

        // Check if columns are detected
        await waitFor(() => {
          expect(screen.getByText('Configure Time Series')).toBeInTheDocument();
          expect(screen.getByLabelText('Time Column:')).toBeInTheDocument();
        });
      }
    }
  });

  test('submits form successfully', async () => {
    mockedAxios.post.mockResolvedValueOnce({
      data: { analysis_id: 'test-123' }
    });

    const { container } = render(
      <BrowserRouter>
        <FileUpload />
      </BrowserRouter>
    );

    const csvContent = 'timestamp,value\n2023-01-01,42';
    const file = new File([csvContent], 'test.csv', { type: 'text/csv' });
    const inputEl = container.querySelector('input[type="file"]');
    
    if (inputEl) {
      Object.defineProperty(inputEl, 'files', {
        value: [file]
      });

      fireEvent.change(inputEl);

      await waitFor(() => {
        expect(screen.getByText(/Selected file: test.csv/i)).toBeInTheDocument();
      });

      const submitButton = await screen.findByText('Analyze Time Series');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockedAxios.post).toHaveBeenCalledWith(
          'http://localhost:8000/api/upload-csv/',
          expect.any(FormData),
          expect.objectContaining({
            headers: {
              'Content-Type': 'multipart/form-data'
            }
          })
        );
      });
    }
  });
});