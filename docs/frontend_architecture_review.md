# Frontend Architecture Review - Time Series Analyzer

This document provides an overview of the frontend architecture for the Time Series Analyzer project, focusing on key technologies, structural organization, component purposes, and their interactions.

## 1. Main Technologies and Frameworks:

*   **React:** The core JavaScript library for building user interfaces.
*   **TypeScript:** Used for type-checking, enhancing code quality and maintainability.
*   **CSS:** For styling the components, primarily through `frontend/src/App.css` and potentially other component-specific CSS.
*   **React Router DOM:** For declarative routing within the single-page application.
*   **Axios:** A promise-based HTTP client for making requests to the backend API.
*   **D3.js (Data-Driven Documents):** A JavaScript library for manipulating documents based on data, used here for rendering interactive time series charts.
*   **React Dropzone:** A component for handling drag-and-drop file uploads.

## 2. Overall Structure of the Frontend:

The frontend is organized within the `frontend/` directory, following a typical React application structure:

*   `frontend/public/`: Contains static assets, primarily `frontend/public/index.html`, which is the entry point for the web application.
*   `frontend/src/`: Contains the main application source code.
    *   `frontend/src/App.css`: Global CSS styles for the application.
    *   `frontend/src/App.tsx`: The main application component, responsible for setting up routing and overall layout.
    *   `frontend/src/index.tsx`: The entry point of the React application, rendering the `App` component into the `index.html`.
    *   `frontend/src/components/`: A directory for reusable UI components.
        *   `frontend/src/components/FileUpload.tsx`: Component for handling CSV file uploads and column selection.
        *   `frontend/src/components/Header.tsx`: The application's header navigation component.
        *   `frontend/src/components/TimeSeriesViewer.tsx`: Component for displaying time series data using D3.js.
        *   `frontend/src/components/__tests__/`: Contains test files for components, e.g., `frontend/src/components/__tests__/FileUpload.test.tsx`.

## 3. Purpose of Main Components:

*   **`index.tsx`**: This is the root of the React application. It imports `React` and `ReactDOM`, applies global styles from `App.css`, and renders the main `App` component into the HTML element with the ID 'root' in `public/index.html`. It also wraps the `App` component in `React.StrictMode` for development-time checks.

*   **`App.tsx`**: This component acts as the main layout and routing hub.
    *   It uses `react-router-dom` to define application routes.
    *   It includes the `Header` component, which provides navigation.
    *   It defines two main routes:
        *   `/`: Renders the `FileUpload` component, serving as the initial landing page for uploading data.
        *   `/view/:analysisId`: Renders the `TimeSeriesViewer` component, displaying the analysis results for a specific `analysisId`.

*   **`FileUpload.tsx`**: This component is responsible for:
    *   Allowing users to drag-and-drop or select CSV files using `react-dropzone`.
    *   Parsing the selected CSV file to extract headers and preview the first few rows.
    *   Enabling users to select a "time column" and multiple "value columns" from the CSV data.
    *   Sending the selected file and column configurations to the backend API (`http://localhost:8000/api/upload-csv/`) using `axios`.
    *   Navigating to the `TimeSeriesViewer` component with the `analysisId` received from the backend upon successful upload.
    *   Managing loading states and displaying errors.

*   **`Header.tsx`**: This component provides the main navigation for the application.
    *   It displays the application title "Time Series Analyzer".
    *   It includes navigation links:
        *   "Upload": Links back to the root path (`/`), which renders the `FileUpload` component.
        *   "GitHub": An external link to the project's GitHub repository.

*   **`TimeSeriesViewer.tsx`**: This component is responsible for:
    *   Fetching time series data from the backend API (`http://localhost:8000/api/analyze/:analysisId`) based on the `analysisId` from the URL parameters.
    *   Displaying the fetched data using D3.js to render interactive charts.
    *   Allowing users to switch between "Time Domain" and "Frequency Domain" views.
    *   Providing options for time scaling (millisecond, second, minute, hour, day) and stacked view for time domain charts.
    *   Enabling users to select which data series (columns) to display on the chart.
    *   Offering functionality to export the displayed data in CSV or JSON format.
    *   Managing loading states and displaying errors during data fetching.

## 4. How Components Interact:

The components interact in a clear flow:

```mermaid
graph TD
    A[index.tsx] --> B(App.tsx);
    B --> C(Header.tsx);
    B --> D{Routes};
    D -- "/" --> E(FileUpload.tsx);
    D -- "/view/:analysisId" --> F(TimeSeriesViewer.tsx);
    E -- Upload CSV & Get analysisId --> F;
    F -- Fetch Data --> G(Backend API);
    G -- Data Response --> F;
    C -- Navigate --> E;