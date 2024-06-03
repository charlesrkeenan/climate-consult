import plotly.graph_objects as go

def generate_figure(aqi_results, current_dt):
    # Create figure object
    figure = go.Figure()

    # Create the AQI line graph traces
    figure.add_trace(go.Scatter(
        name = "History",
        x=[dt for dt in aqi_results.keys() if dt <= current_dt.strftime(format='%Y-%m-%dT%H:%M:%SZ')],
        y=[aqi_results[dt] for dt in aqi_results.keys() if dt <= current_dt.strftime(format='%Y-%m-%dT%H:%M:%SZ')],
        mode='lines',
        line=dict(width=2, color='black')
    ))
    figure.add_trace(go.Scatter(
        name = "Forecast",
        x=[dt for dt in aqi_results.keys() if dt >= current_dt.strftime(format='%Y-%m-%dT%H:%M:%SZ')],
        y=[aqi_results[dt] for dt in aqi_results.keys() if dt >= current_dt.strftime(format='%Y-%m-%dT%H:%M:%SZ')],
        mode='lines',
        line=dict(dash='dot', width=2, color='black')
    ))

    # Add the AQI range shapes
    aqi_ranges = [
    {"range": [0, 50], "color": "green", "air pollution level": "Good"},
    {"range": [50, 100], "color": "yellow", "air pollution level": "Moderate"},
    {"range": [100, 150], "color": "orange", "air pollution level": "Unhealthy for Sensitive Groups"},
    {"range": [150, 200], "color": "red", "air pollution level": "Unhealthy"},
    {"range": [200, 300], "color": "purple", "air pollution level": "Very Unhealthy"},
    {"range": [300, 500], "color": "maroon", "air pollution level": "Hazardous"}
    ]

    # Add shapes for each AQI range
    for aqi_range in aqi_ranges:
        figure.add_hrect(
            showlegend=False,
            name=aqi_range["air pollution level"],
            layer= 'below',
            line_width = 0,
            y0 = aqi_range["range"][0],
            y1 = aqi_range["range"][1],
            fillcolor= aqi_range["color"],
            opacity= 0.66,
            label = dict(
                text = aqi_range["air pollution level"],
                textposition = "top left",
                yanchor = "top",
                xanchor = "left",

            )
        )

    # Add the "NOW" indicator
    figure.add_shape(
        type = "line",
        x0 = current_dt,
        x1 = current_dt,
        y0 = 0,
        y1 = 500,
        line = dict(
            color = "#2f2f2d",
            width = 3, 
        ), 
        label = dict(
            text = "NOW",
            textangle = 0,
            xanchor = "left",
            yanchor = "middle",
            padding = 5
        )
    )

    # Update X and Y axis
    figure.update_xaxes(
        zeroline = False,
        minor = dict(
            dtick = 86400000.0,
            ticks = "inside",
            ticklen = 5,
            tickcolor = "white",
        )
    )
    figure.update_yaxes(
        zeroline = False,
    )

    # Update figure layout
    figure.update_layout(
        title='😶‍🌫️ Air Quality History and Forecast',
        xaxis=dict(tickformat='%B %-e', type = "date"),
        yaxis = dict(
            tickmode = "array",
            tickvals = [0, 50, 100, 150, 200, 300, 500],
            tick0 = 0,
            tickcolor = "white"
        ),
        showlegend=False,
        font=dict(
                size=10,
                color="black"
        ),
        title_font=dict(
            size=14,
            color='black'
        ),
        hovermode = "x",
        plot_bgcolor = "white"
    )
    
    return figure