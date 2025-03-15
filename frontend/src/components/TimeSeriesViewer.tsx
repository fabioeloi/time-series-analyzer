import React, { useEffect, useState, useRef } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import * as d3 from 'd3';

interface TimeSeriesData {
  analysis_id: string;
  columns: string[];
  time_column: string;
  value_columns: string[];
  time_domain: {
    time: any[];
    series: {
      [key: string]: number[];
    };
  };
  frequency_domain?: {
    frequencies: {
      [key: string]: number[];
    };
    amplitudes: {
      [key: string]: number[];
    };
  };
}

const TimeSeriesViewer: React.FC = () => {
  const { analysisId } = useParams<{ analysisId: string }>();
  const [data, setData] = useState<TimeSeriesData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');
  const [domain, setDomain] = useState<'time' | 'frequency'>('time');
  const [selectedColumns, setSelectedColumns] = useState<string[]>([]);
  const [timeScale, setTimeScale] = useState<'auto' | 'millisecond' | 'second' | 'minute' | 'hour' | 'day'>('auto');
  const [stacked, setStacked] = useState<boolean>(false);
  const [exportFormat, setExportFormat] = useState<'csv' | 'json'>('csv');
  
  const svgRef = useRef<SVGSVGElement | null>(null);
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`http://localhost:8000/api/analyze/${analysisId}?domain=${domain}`);
        setData(response.data);
        
        // Initialize selected columns
        if (response.data.value_columns && response.data.value_columns.length > 0) {
          setSelectedColumns(response.data.value_columns);
        }
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to fetch data');
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [analysisId, domain]);
  
  useEffect(() => {
    if (data && svgRef.current) {
      if (domain === 'time') {
        renderTimeChart();
      } else {
        renderFrequencyChart();
      }
    }
  }, [data, domain, selectedColumns, timeScale, stacked]);
  
  const renderTimeChart = () => {
    if (!data || !svgRef.current) return;
    
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    
    const margin = { top: 20, right: 80, bottom: 30, left: 50 };
    const width = svgRef.current.clientWidth - margin.left - margin.right;
    const height = svgRef.current.clientHeight - margin.top - margin.bottom;
    
    const g = svg.append("g")
      .attr("transform", `translate(${margin.left}, ${margin.top})`);
    
    // Parse times based on selected scale
    let times = data.time_domain.time;
    if (timeScale !== 'auto') {
      const parseTime = getTimeParser(timeScale);
      times = times.map((t: string) => parseTime(t));
    }
    
    // X scale
    const xScale = d3.scaleTime()
      .domain(d3.extent(times, d => new Date(d)) as [Date, Date])
      .range([0, width]);
    
    // Y scale (depends on stacked or not)
    let yScale: d3.ScaleLinear<number, number>;
    if (stacked) {
      // For stacked, find the max sum of all selected columns
      const stackedData = d3.stack()
        .keys(selectedColumns)
        .value((d: any, key) => d[key] || 0)(
          times.map((t, i) => {
            const obj: any = { time: t };
            selectedColumns.forEach(col => {
              obj[col] = data.time_domain.series[col][i] || 0;
            });
            return obj;
          })
        );
      
      yScale = d3.scaleLinear()
        .domain([0, d3.max(stackedData[stackedData.length - 1], d => d[1]) || 0])
        .range([height, 0]);
    } else {
      // For unstacked, find the min and max across all selected columns
      const allValues: number[] = [];
      selectedColumns.forEach(col => {
        allValues.push(...data.time_domain.series[col]);
      });
      
      yScale = d3.scaleLinear()
        .domain([d3.min(allValues) || 0, d3.max(allValues) || 0])
        .range([height, 0]);
    }
    
    // X axis
    g.append("g")
      .attr("transform", `translate(0, ${height})`)
      .call(d3.axisBottom(xScale));
    
    // Y axis
    g.append("g")
      .call(d3.axisLeft(yScale));
    
    // Color scale for multiple lines
    const colorScale = d3.scaleOrdinal(d3.schemeCategory10)
      .domain(selectedColumns);
    
    if (stacked) {
      // Render stacked area chart
      const stackedData = d3.stack()
        .keys(selectedColumns)
        .value((d: any, key) => d[key] || 0)(
          times.map((t, i) => {
            const obj: any = { time: t };
            selectedColumns.forEach(col => {
              obj[col] = data.time_domain.series[col][i] || 0;
            });
            return obj;
          })
        );
      
      const area = d3.area<d3.SeriesPoint<any>>()
        .x((d, i) => xScale(new Date(times[i])))
        .y0(d => yScale(d[0]))
        .y1(d => yScale(d[1]));
      
      g.selectAll(".area")
        .data(stackedData)
        .enter()
        .append("path")
        .attr("class", "area")
        .attr("d", area)
        .style("fill", (d, i) => colorScale(d.key as string))
        .style("opacity", 0.7);
        
    } else {
      // Render multiple line chart
      // Line generator
      const line = d3.line<number>()
        .x((d, i) => xScale(new Date(times[i])))
        .y(d => yScale(d));
      
      // Add line paths
      selectedColumns.forEach(column => {
        g.append("path")
          .datum(data.time_domain.series[column])
          .attr("fill", "none")
          .attr("stroke", colorScale(column))
          .attr("stroke-width", 1.5)
          .attr("d", line);
      });
    }
    
    // Add legend
    const legend = g.append("g")
      .attr("font-family", "sans-serif")
      .attr("font-size", 10)
      .attr("text-anchor", "end")
      .selectAll("g")
      .data(selectedColumns)
      .enter().append("g")
      .attr("transform", (d, i) => `translate(0, ${i * 20})`);
    
    legend.append("rect")
      .attr("x", width - 19)
      .attr("width", 19)
      .attr("height", 19)
      .attr("fill", colorScale);
    
    legend.append("text")
      .attr("x", width - 24)
      .attr("y", 9.5)
      .attr("dy", "0.32em")
      .text(d => d);
  };

  const renderFrequencyChart = () => {
    if (!data || !data.frequency_domain || !svgRef.current) return;
    
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    
    const margin = { top: 20, right: 80, bottom: 30, left: 50 };
    const width = svgRef.current.clientWidth - margin.left - margin.right;
    const height = svgRef.current.clientHeight - margin.top - margin.bottom;
    
    const g = svg.append("g")
      .attr("transform", `translate(${margin.left}, ${margin.top})`);
    
    // Set up scales for each column
    selectedColumns.forEach((column, index) => {
      const frequencies = data.frequency_domain!.frequencies[column];
      const amplitudes = data.frequency_domain!.amplitudes[column];
      
      // Define chart position (stacked vertically)
      const chartHeight = height / selectedColumns.length;
      const chartTop = index * chartHeight;
      
      // X and Y scales
      const xScale = d3.scaleLinear()
        .domain([0, d3.max(frequencies) || 0])
        .range([0, width]);
      
      const yScale = d3.scaleLinear()
        .domain([0, d3.max(amplitudes) || 0])
        .range([chartHeight - 10, 0]);
      
      // X axis
      g.append("g")
        .attr("transform", `translate(0, ${chartTop + chartHeight - 10})`)
        .call(d3.axisBottom(xScale).ticks(5))
        .append("text")
        .attr("x", width / 2)
        .attr("y", 30)
        .attr("fill", "#000")
        .text("Frequency");
      
      // Y axis
      g.append("g")
        .attr("transform", `translate(0, ${chartTop})`)
        .call(d3.axisLeft(yScale).ticks(3))
        .append("text")
        .attr("transform", "rotate(-90)")
        .attr("y", -30)
        .attr("x", -chartHeight / 2)
        .attr("fill", "#000")
        .text("Amplitude");
      
      // Column label
      g.append("text")
        .attr("x", width - 20)
        .attr("y", chartTop + 15)
        .attr("text-anchor", "end")
        .attr("font-size", "12px")
        .attr("font-weight", "bold")
        .text(column);
      
      // Line for frequency spectrum
      const line = d3.line<number>()
        .x((d, i) => xScale(frequencies[i]))
        .y((d) => yScale(d) + chartTop);
      
      // Add line path
      g.append("path")
        .datum(amplitudes)
        .attr("fill", "none")
        .attr("stroke", d3.schemeCategory10[index % 10])
        .attr("stroke-width", 1.5)
        .attr("d", line);
    });
  };

  const getTimeParser = (scale: string) => {
    switch (scale) {
      case 'millisecond':
        return (d: string) => new Date(d);
      case 'second':
        return (d: string) => {
          const date = new Date(d);
          return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 
                         date.getHours(), date.getMinutes(), date.getSeconds(), 0);
        };
      case 'minute':
        return (d: string) => {
          const date = new Date(d);
          return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 
                         date.getHours(), date.getMinutes(), 0, 0);
        };
      case 'hour':
        return (d: string) => {
          const date = new Date(d);
          return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 
                         date.getHours(), 0, 0, 0);
        };
      case 'day':
        return (d: string) => {
          const date = new Date(d);
          return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 0, 0, 0, 0);
        };
      default:
        return (d: string) => new Date(d);
    }
  };

  const handleDomainChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setDomain(e.target.value as 'time' | 'frequency');
  };

  const handleTimeScaleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setTimeScale(e.target.value as 'auto' | 'millisecond' | 'second' | 'minute' | 'hour' | 'day');
  };

  const handleStackedChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setStacked(e.target.checked);
  };

  const handleColumnChange = (column: string) => {
    setSelectedColumns(prev => {
      if (prev.includes(column)) {
        return prev.filter(col => col !== column);
      } else {
        return [...prev, column];
      }
    });
  };

  const handleExportFormatChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setExportFormat(e.target.value as 'csv' | 'json');
  };

  const handleExport = async () => {
    try {
      if (exportFormat === 'csv') {
        // For CSV, we need to trigger a download
        window.open(`http://localhost:8000/api/export/${analysisId}?format=csv&domain=${domain}`, '_blank');
      } else {
        // For JSON, we can display the data or trigger a download
        const response = await axios.get(`http://localhost:8000/api/export/${analysisId}?format=json&domain=${domain}`);
        
        // Create a Blob with the JSON data
        const jsonData = JSON.stringify(response.data, null, 2);
        const blob = new Blob([jsonData], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        // Create a link and trigger download
        const link = document.createElement('a');
        link.href = url;
        link.download = `time_series_analysis_${analysisId}_${domain}.json`;
        document.body.appendChild(link);
        link.click();
        
        // Clean up
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Export failed');
    }
  };

  if (loading) {
    return <div className="loading">Loading data...</div>;
  }

  if (error) {
    return <div className="error">Error: {error}</div>;
  }

  if (!data) {
    return <div className="error">No data available</div>;
  }

  return (
    <div className="time-series-viewer">
      <h2>Time Series Analysis</h2>
      
      <div className="controls">
        <div className="control-group">
          <label htmlFor="domain-select">Analysis Domain:</label>
          <select 
            id="domain-select"
            value={domain}
            onChange={handleDomainChange}
          >
            <option value="time">Time Domain</option>
            <option value="frequency">Frequency Domain</option>
          </select>
        </div>
        
        {domain === 'time' && (
          <>
            <div className="control-group">
              <label htmlFor="scale-select">Time Scale:</label>
              <select
                id="scale-select"
                value={timeScale}
                onChange={handleTimeScaleChange}
              >
                <option value="auto">Auto</option>
                <option value="millisecond">Millisecond</option>
                <option value="second">Second</option>
                <option value="minute">Minute</option>
                <option value="hour">Hour</option>
                <option value="day">Day</option>
              </select>
            </div>
            
            <div className="control-group">
              <label>
                <input
                  type="checkbox"
                  checked={stacked}
                  onChange={handleStackedChange}
                />
                Stacked View
              </label>
            </div>
          </>
        )}
        
        <div className="control-group">
          <label htmlFor="export-format">Export Format:</label>
          <div className="export-controls">
            <select
              id="export-format"
              value={exportFormat}
              onChange={handleExportFormatChange}
            >
              <option value="csv">CSV</option>
              <option value="json">JSON</option>
            </select>
            <button 
              className="export-button"
              onClick={handleExport}
            >
              Export Data
            </button>
          </div>
        </div>
        
        <div className="control-group column-select">
          <label>Data Series:</label>
          <div className="checkbox-group">
            {data.value_columns.map(column => (
              <div key={column} className="checkbox-item">
                <input
                  type="checkbox"
                  id={`col-${column}`}
                  checked={selectedColumns.includes(column)}
                  onChange={() => handleColumnChange(column)}
                />
                <label htmlFor={`col-${column}`}>{column}</label>
              </div>
            ))}
          </div>
        </div>
      </div>
      
      <div className="chart-container">
        <svg ref={svgRef} width="100%" height="500"></svg>
      </div>
    </div>
  );
};

export default TimeSeriesViewer;
