import xarray as xr
from titiler_patch.factory_patch import TilerFactory
from titiler.xarray.extensions import VariablesExtension
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse


# 3. Create FastAPI application
app = FastAPI(
    title="GFED5 Zarr Tile Server",
    description="TiTiler.xarray server for GFED5 dataset visualization",
    openapi_url="/api",
    docs_url="/api.html"
)

# 4. Create TilerFactory with VariablesExtension
# The default Reader will work with your zarr dataset
md = TilerFactory(
    router_prefix="/md",
    extensions=[
        VariablesExtension(),  # This adds variable selection capabilities
    ],
)

# 5. Include the router in your FastAPI app
app.include_router(md.router, prefix="/md", tags=["Multi Dimensional"])

# # 6. Add dataset info endpoint
# @app.get("/info")
# async def dataset_info():
#     """Get information about the GFED5 dataset"""
#     return {
#         "variables": list(ds.data_vars),
#         "dimensions": dict(ds.dims),
#         "coordinates": list(ds.coords),
#         "shape": {var: ds[var].shape for var in ds.data_vars},
#         "attrs": ds.attrs,
#         "data_vars_info": {
#             var: {
#                 "shape": ds[var].shape,
#                 "dims": ds[var].dims,
#                 "dtype": str(ds[var].dtype),
#                 "attrs": ds[var].attrs
#             } for var in ds.data_vars
#         }
#     }

# 7. Simple web viewer
@app.get("/", response_class=HTMLResponse)
async def viewer():
    """Interactive leaflet viewer for the GFED5 tiles"""
    
    # Get available variables
    variables = [
        "C", "C2H5OH", "C2H4", "C2H2", "C10H16", "C2H6", "burned_area", "basisregions",
        "BC", "C2H4O", "C2H6S", "C5H8", "C3H6", "C3H6O", "C3H8", "CH2O", "C7H8", "C8H10",
        "CH3COCHO", "C6H6", "CH3COOH", "CH4", "CO", "CO2", "DM", "CH3OH", "HCN", "H2",
        "grid_area", "HCOOH", "Higher_Alkanes", "Higher_Alkenes", "HOCH2CHO", "MEK",
        "N2O", "NH3", "NMOC_g", "NOx", "OC", "PM2p5", "SO2", "Toluene_lump", "TPC"
    ]
    times = [d+ '-01T01:00:00.000000000' for d in ['2002-01', '2002-02','2002-03', '2002-04', '2002-05', '2002-06', '2002-07','2002-08', '2002-09', '2002-10', '2002-11', '2002-12'] ]
    first_var = variables[0] if variables else "CO"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>GFED5 Zarr Viewer</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            #controls {{
                position: absolute;
                top: 10px;
                right: 10px;
                z-index: 1000;
                background: white;
                padding: 15px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.3);
                min-width: 200px;
            }}
            #controls label {{
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
            }}
            #controls select, #controls input {{
                width: 100%;
                margin-bottom: 10px;
                padding: 5px;
            }}
            #info {{
                position: absolute;
                bottom: 10px;
                left: 10px;
                z-index: 1000;
                background: rgba(255,255,255,0.9);
                padding: 10px;
                border-radius: 5px;
                font-family: monospace;
                font-size: 12px;
            }}
            #coordinates {{
                position: absolute;
                bottom: 10px;
                right: 10px;
                z-index: 1000;
                background: rgba(255,255,255,0.9);
                padding: 10px;
                border-radius: 5px;
                font-family: monospace;
                font-size: 12px;
                border: 2px solid #007cba;
                min-width: 200px;
            }}
            #coordinates h4 {{
                margin: 0 0 5px 0;
                color: #007cba;
            }}
            .coord-row {{
                margin: 2px 0;
            }}
            .coord-label {{
                font-weight: bold;
                color: #333;
            }}
            .coord-value {{
                color: #666;
            }}
            .click-instruction {{
                font-style: italic;
                color: #888;
                margin-top: 5px;
            }}
        </style>
    </head>
    <body>
        <div id="controls">
            <label> URL: </label>
            <input type="text" id="urlInput" placeholder="URL" value="https://gfed-test.s3.eu-north-1.amazonaws.com/GFED5_2002.zarr/">

            <label>Variable:</label>
            <select id="variableSelect"> ${{url_data}}
                {"".join(f'<option value="{var}">{var}</option>' for var in variables)}
            </select>

            <label>Time:</label>
            <select id="timeSelect">
                {"".join(f'<option value="{t}">{t}</option>' for t in times)}
            </select>
            
            <label>Colormap:</label>
            <select id="colormapSelect">
                <option value="inferno">Inferno</option>
                <option value="viridis">Viridis</option>
                <option value="plasma">Plasma</option>
                <option value="magma">Magma</option>
                <option value="cividis">Cividis</option>
                <option value="turbo">Turbo</option>
                <option value="hot">Hot</option>
                <option value="cool">Cool</option>
            </select>
            
            <label>Rescale (min,max):</label>
            <input type="text" id="rescaleInput" placeholder="auto" title="e.g., 0,100 or leave empty for auto">
            
            <label>Opacity:</label>
            <input type="range" id="opacitySlider" min="0" max="1" step="0.1" value="0.8">
            <span id="opacityValue">0.8</span>
            
            <button onclick="updateLayer()" style="width: 100%; padding: 8px; margin-top: 10px;">Update Layer</button>
        </div>
        
        <div id="coordinates">
            <h4>📍 Click Coordinates to get time series </h4>
            <div> Time series of <span id="currentVar">{first_var}</span>: </div>
            <div class="coord-row">
                <span class="coord-label">@ coordinates:</span>
                <span class="coord-value" id="clickDecimal">-</span>
            </div>
            <div id="timeSeriesResult">Click on the map to load time series.</div>
        </div>
        
        <div id="info">
            <div>Dataset: GFED5</div>
            <div>Variables: {len(variables)}</div>
        </div>
        
        <div id="map" style="width: 100%; height: 100vh;"></div>
        
        <script>
            // Initialize the map
            var map = L.map('map').setView([0, 0], 2);
            
            // Add base layer
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '© OpenStreetMap contributors'
            }}).addTo(map);
            
            // Current data layer
            var dataLayer = null;
            
            // Click marker
            var clickMarker = null;
            
            // Add click event listener to the map
            map.on('click', function(e) {{
                var lat = e.latlng.lat;
                var lng = e.latlng.lng;
                
                // Update coordinate display
                document.getElementById('clickDecimal').textContent = `${{lat.toFixed(6)}}, ${{lng.toFixed(6)}}`;
                
                // Remove existing marker
                if (clickMarker) {{
                    map.removeLayer(clickMarker);
                }}
                
                // Add new marker at clicked location
                clickMarker = L.marker([lat, lng], {{
                    icon: L.icon({{
                        iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-orange.png',
                        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                        iconSize: [25, 41],
                        iconAnchor: [12, 41],
                        popupAnchor: [1, -34],
                        shadowSize: [41, 41]
                    }})
                }}).addTo(map);
                
                // Add popup with coordinates
                clickMarker.bindPopup(`
                    <div>
                        <strong>Coordinates:</strong><br>
                        <strong>Lat:</strong> ${{lat.toFixed(6)}}<br>
                        <strong>Lng:</strong> ${{lng.toFixed(6)}}<br>
                    </div>
                `).openPopup();
                
                // Log to console for debugging
                console.log('Clicked coordinates:', {{lat: lat, lng: lng}});

                // Fetch and display time series
                const variable = document.getElementById("variableSelect").value;
                fetchTimeSeries(lat, lng, variable);
            }});
            
            // Update opacity display
            document.getElementById('opacitySlider').addEventListener('input', function() {{
                document.getElementById('opacityValue').textContent = this.value;
                if (dataLayer) {{
                    dataLayer.setOpacity(this.value);
                }}
            }});
            
            // Function to update the data layer
            function updateLayer() {{
                var url_data = document.getElementById('urlInput').value;
                var variable = document.getElementById('variableSelect').value;
                var time = document.getElementById('timeSelect').value;
                var colormap = document.getElementById('colormapSelect').value;
                var rescale = document.getElementById('rescaleInput').value;
                var opacity = document.getElementById('opacitySlider').value;
                
                // Update info
                document.getElementById('currentVar').textContent = variable;
                
                // Remove existing layer
                if (dataLayer) {{
                    map.removeLayer(dataLayer);
                }}
                
                // Build tile URL - using the dataset file path directly
                var tileUrl = `https://gfedashboard.onrender.com/md/tiles/WorldMercatorWGS84Quad/{{z}}/{{x}}/{{y}}.png?url=${{url_data}}&variable=${{variable}}&sel=time%3D${{time}}&colormap_name=${{colormap}}&nodata=0`;
                
                // Add rescale parameter if specified
                if (rescale && rescale.trim()) {{
                    tileUrl += `&rescale=${{rescale}}`;
                }}
                
                // Add new layer
                dataLayer = L.tileLayer(tileUrl, {{
                    attribution: 'GFED5 Data',
                    opacity: parseFloat(opacity)
                }}).addTo(map);
                
                console.log('Loading tiles from:', tileUrl);
            }}
            // Fetch and display time series data with Plotly
            async function fetchTimeSeries(lat, lon, variable) {{
                var url_data = document.getElementById('urlInput').value;
                var variable = document.getElementById('variableSelect').value;
                var coordinates = `${{lon.toFixed(6)}},${{lat.toFixed(6)}}`;

                try {{
                    var url = `https://gfedashboard.onrender.com/md/point/${{coordinates}}?url=${{url_data}}&variable=${{variable}}`;

                    var response = await fetch(url);
                    if (!response.ok) throw new Error(`HTTP error: ${{response.status}}`);
                    var data = await response.json();

                    var values = data.values;
                    var labels = data.band_names;

                    // Use Plotly to plot the time series
                    var plotDivId = "plotly-timeseries";
                    // Create a div if not exists
                    var tsDiv = document.getElementById("timeSeriesResult");
                    tsDiv.innerHTML = `<div id="${{plotDivId}}" style="width:700px;height:250px;"></div>`;

                    var trace = {{
                        x: labels,
                        y: values,
                        mode: 'lines+markers',
                        type: 'scatter',
                        line: {{ color: 'steelblue' }},
                        marker: {{ size: 6 }},
                        name: variable
                    }};
                    var layout = {{
                        title: `Time Series for ${{variable}}`,
                        xaxis: {{
                            title: 'Time',
                            tickangle: -45,
                            automargin: true
                        }},
                        yaxis: {{
                            title: variable,
                            automargin: true
                        }},
                        margin: {{ t: 40, l: 50, r: 20, b: 80 }},
                        plot_bgcolor: "#fff"
                    }};
                    Plotly.newPlot(plotDivId, [trace], layout, {{displayModeBar: false}});
                }} catch (err) {{
                    console.error("Time series fetch failed", err);
                    document.getElementById("timeSeriesResult").textContent = "Failed to fetch time series.";
                }}
            }}
            
            // Initial load
            updateLayer();
            
            // Auto-update on variable/colormap change
            document.getElementById('variableSelect').addEventListener('change', updateLayer);
            document.getElementById('timeSelect').addEventListener('change', updateLayer);
            document.getElementById('colormapSelect').addEventListener('change', updateLayer);
        </script>
    </body>
    </html>
    """
    return html_content

# 8. Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "dataset_loaded": True}

# 9. Root redirect
@app.get("/viewer")
async def viewer_redirect():
    return {"message": "Use GET / for the viewer interface"}

# 10. Run the server
if __name__ == "__main__":
    # print("=" * 50)
    # print("Starting GFED5 TiTiler.xarray server...")
    # print("=" * 50)
    # print("Available endpoints:")
    # print("- Interactive viewer: https://gfedashboard.onrender.com/")
    # print("- Dataset info: https://gfedashboard.onrender.com/info")
    # print("- API documentation: https://gfedashboard.onrender.com/api.html")
    # print("- Health check: https://gfedashboard.onrender.com/health")
    # print()
    # print("Tile URL format:")
    # print("https://gfedashboard.onrender.com/md/tiles/{z}/{x}/{y}.png?url=/mnt/c/Users/domin022/Dropbox/PhD/GFEDashboard/GFED5_combined_2002_2022.zarr&variable=YOUR_VARIABLE")
    # print()
    # print("Available variables in your dataset:")
    # for var in ds.data_vars:
    #     print(f"  - {var}")
    # print("=" * 50)
    
    # Start the server
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Example usage for direct tile access:
"""
Once the server is running, you can access tiles directly:

Basic tile URL:
https://gfedashboard.onrender.com/md/tiles/{z}/{x}/{y}.png?url=/mnt/c/Users/domin022/Dropbox/PhD/GFEDashboard/GFED5_combined_2002_2022.zarr&variable=your_variable_name

With additional parameters:
https://gfedashboard.onrender.com/md/tiles/{z}/{x}/{y}.png?url=/mnt/c/Users/domin022/Dropbox/PhD/GFEDashboard/GFED5_combined_2002_2022.zarr&variable=your_variable_name&colormap=viridis&rescale=0,100

Common parameters:
- variable: name of the variable to visualize
- colormap: color scheme (viridis, plasma, inferno, magma, etc.)
- rescale: min,max values for color scaling
- nodata: value to treat as transparent

New click coordinate features:
- Click anywhere on the map to get coordinates
- Coordinates are displayed in both decimal degrees and DMS format
- A red marker appears at the clicked location
- Popup shows detailed coordinate information
- Coordinates are logged to browser console for debugging
"""