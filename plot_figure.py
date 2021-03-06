import plotly.express as px
import requests
import pandas as pd
from pandas import json_normalize
import plotly.graph_objects as go

#############################################
# cumulative production tab & pipeline tab
#############################################
def citywide_choropleth(df, mapbox_token, job_type, job_units, normalization):

    # get the geojson needed for the mapping 
    response = requests.get('https://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services/NYC_Census_Tracts_for_2010_US_Census/FeatureServer/0/query?where=1=1&outFields=*&outSR=4326&f=pgeojson')
    #response = requests.get('https://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services/NYC_Census_Tracts_for_2010_US_Census_Water_Included/FeatureServer/0/query?where=1=1&outFields=*&outSR=4326&f=pgeojson')

    geojson = response.json()

    geofeatures = json_normalize(geojson["features"])

    geofeatures['acreage'] = geofeatures['properties.Shape__Area'].astype(float) / 43560.

    merged = df.merge(geofeatures[['properties.BoroCT2010', 'acreage']], left_on='bct2010', right_on='properties.BoroCT2010', how='inner')

    # this step normalizes jobs/units to be by acre
    merged['units_per_acre'] = merged[job_units] / merged.acreage

    # if the normalization specifies then 
    if normalization == 'units_per_acre':

        params = {
            'max': merged[normalization].max(),
            'min': merged[normalization].min(),
            'job_type': job_type
        }

    else:
        # if the unormalized, then it should be raw count of units or number of jobs 
        params = {
            'max': merged[job_units].max(),
            'min': merged[job_units].min(),
            'job_type': job_type
        }

    if params['job_type'] == "'Demolition'":
        cs = 'Reds'
        rs = True
    elif params['job_type'] == "'New Building'":
        cs = 'Blues'
        rs = False
    else:
        cs = 'Bluered'
        rs = None

    fig = go.Figure(go.Choroplethmapbox(geojson=geojson, locations=merged.bct2010, z=merged[normalization],
                                    colorscale=cs, reversescale=rs, zmin=params['min'], zmax=params['max'],
                                    marker_opacity=1.0, marker_line_width=0, featureidkey="properties.BoroCT2010"))

    fig.update_layout(mapbox_accesstoken=mapbox_token, mapbox_style="carto-positron",
                    mapbox_zoom=9, mapbox_center = {"lat": 40.730610, "lon": -73.935242}, margin={"r":0,"t":0,"l":0,"b":0})

    return fig


def community_district_choropleth(agg_db, job_type, boro, mapbox_token):

    response = requests.get('https://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services/NYC_Community_Districts/FeatureServer/0/query?where=1=1&outFields=*&outSR=4326&f=pgeojson')
    
    geojson = response.json()

    # aggregate by community district 
    cd_choro = agg_db.groupby('cd')['num_net_units'].sum().reset_index()

    #fig_choro = px.choropleth_mapbox(cd_choro, geojson=geojson, locations='cd', color=cd_choro.num_net_units,
    #featureidkey="properties.BoroCD")
    # 
    if job_type == "'Demolition'":
        cs = 'Reds'
        rs = True
    elif job_type == "'New Building'":
        cs = 'Blues'
        rs = False
    else:
        cs = 'Bluered'
        rs = None

    fig_choro = go.Figure(go.Choroplethmapbox(geojson=geojson, locations=cd_choro.cd, z=cd_choro.num_net_units, #colorscale='Greens',
                                colorscale=cs, reversescale=rs, #zmin=params['min'], zmax=params['max'],
                                marker_opacity=1.0, marker_line_width=0, featureidkey="properties.BoroCD"))

    # lat long for different borough  
    center_dict = {
        1: (40.7831, -73.9712), 
        2: (40.8448, -73.8648), 
        3: (40.6782, -73.9442), 
        4: (40.7282, -73.7949), 
        5: (40.5795, -74.1502)
    }


    fig_choro.update_layout(
        mapbox_accesstoken=mapbox_token, 
        mapbox_style="carto-positron",
        mapbox_zoom=10, 
        mapbox_center = {"lat": center_dict[boro][0], "lon": center_dict[boro][1]}
    )

    fig_choro.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
 
    # the bar chart graphic
    fig_bar = px.bar(agg_db, x='cd', y='num_net_units', color='year', barmode='stack', 
        title='Number Units by Year and Community District')

    fig_bar.update_layout(xaxis={"type":"category"})

    # create a line chart for different number of units in community districts over years 
    fig_line = px.line(agg_db, x='year', y='num_net_units', color='cd', title='Number of Units Between 2010 and Now')

    return fig_choro, fig_bar, fig_line

##########################
# building size tab
##########################
def building_size_bar(df, job_type, percent_flag):

    # percentage or units count 
    if percent_flag == 'Percentage':

        hover_temp = '<br><b> %{text} </b><br>' + '<i>Percentage</i>: %{y:.1%}<extra></extra>'

    else:

        hover_temp = '<br><b> %{text} </b><br>' + '<i>Units Count</i>: %{y}<extra></extra>'


    # set the figure 
    fig = go.Figure()

    for uclass in df.units_class.unique():

        fig.add_trace(
            go.Bar(
                x=df.loc[df.units_class == uclass].year, 
                y=df.loc[df.units_class == uclass].net_residential_units, 
                name=uclass, 
                text=[uclass for i in range(10)],
                hovertemplate=hover_temp

            )
        )
    
    fig.update_layout(
        title=job_type + ' Completed Residential Units by Number of Units in Buildings', 
        #legend_traceorder=['1 to 2 unit buildings', '3 to 5', '6 to 10', '11 to 25', '26 to 100', '> 100'],
        # https://community.plotly.com/t/customizing-the-order-of-legends/12668 no ability to sort the at the moment
        barmode='stack', 
        xaxis_tickangle=-45
    )

    return fig


##########################
# affordable tab
##########################

def affordable_chart(df, df_char, percent_flag, char_flag):

    if percent_flag == 'Percentage':

        hover_temp = '<br><b> %{text} </b><br>' + '<i>Percentage</i>: %{y:.1%}<extra></extra>'

        n = 6

    else:

        hover_temp = '<br><b> %{text} </b><br>' + '<i>Units Count</i>: %{y}<extra></extra>'

        n = 5

    bar = go.Figure()

    bar.add_trace(
        go.Bar(
            x=df.boro, 
            y=df.other_units, 
            name='Other Units',
            text=['Other Units' for i in range(n)],
            hovertemplate=hover_temp
        )
    )

    bar.add_trace(
        go.Bar(
            x=df.boro,
            y=df.hny_units, 
            name='HNY Units',
            text=['HNY Units' for i in range(n)],
            hovertemplate=hover_temp
        )
    )

    bar.update_layout(title='Residential Units and HNY Units in 2015 or Later Projects', 
        barmode='stack', xaxis_tickangle=-45)

    # hny graphics starts here
    hny_bar = go.Figure()
    
    for col in df_char.columns[:-1]:

        hny_bar.add_trace(
            go.Bar(
                x=df_char.borough, 
                y=df_char[col], 
                name=col,
                text=[col.replace('_', ' ') for i in range(n)],
                hovertemplate=hover_temp
            )
        )

    hny_bar.update_layout(
        hoverlabel_align = 'right',
        title = "Set hover text with hovertemplate")

    hny_bar.update_layout(title='HNY Characteristics: Affordable Units by ' + char_flag, 
        barmode='stack', xaxis_tickangle=-45)

    return bar, hny_bar

##########################
# net effects tab
##########################

def net_effects_chart(df, mapbox_token, job_type, x_axis, boro):

    if x_axis == 'By Year':

        bar = go.Figure()

        for flag in df.units_flag.unique():

            bar.add_trace(
                go.Bar(x=df.loc[df.units_flag == flag].year, y=df.loc[df.units_flag == flag].total_classa_net, name=flag.replace('_', ' '),
                text=df.loc[df.units_flag == flag].total_classa_net, textposition='outside')
            )

        net_table = df.groupby('year').total_classa_net.sum().reset_index()

        bar.add_trace(
            go.Scatter(x=net_table.year, y=net_table.total_classa_net, mode='markers', name='net units outcome', textposition='top center')
        )

        bar.update_layout(title='Net Effects on Residential Units ' + job_type, 
            barmode='relative', xaxis_tickangle=-45)

        return bar
    
    else:

        bar = go.Figure()

        for flag in df.units_flag.unique():

            bar.add_trace(
                go.Bar(x=df.loc[df.units_flag == flag].total_classa_net, y=df.loc[df.units_flag == flag].cd, orientation='h', name=flag.replace('_', ' '))
            )

        net_table = df.groupby('cd').total_classa_net.sum().reset_index()

        #print(net_table)

        bar.add_trace(go.Scatter(x=net_table.total_classa_net, y=net_table.cd, mode='markers', name='net units outcome'))

        bar.update_layout(title='Net Effects on Residential Units ' + job_type, 
            barmode='relative', xaxis_tickangle=-45)
        
        # choropleth
        response = requests.get('https://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services/NYC_Community_Districts/FeatureServer/0/query?where=1=1&outFields=*&outSR=4326&f=pgeojson')
        
        geojson = response.json()

        # aggregate by community district 
        cd_choro = df.groupby('cd')['total_classa_net'].sum().reset_index()


        print(cd_choro)

        print(cd_choro.dtypes)

        #choro = go.Figure()

        fig_choro = go.Figure(go.Choroplethmapbox(geojson=geojson, locations=cd_choro.cd, z=cd_choro.total_classa_net,
                            colorscale='Greens',
                            marker_opacity=1.0, marker_line_width=0, featureidkey="properties.BoroCD"))

        # lat long for different borough  
        center_dict = {
            1: (40.7831, -73.9712), 
            2: (40.8448, -73.8648), 
            3: (40.6782, -73.9442), 
            4: (40.7282, -73.7949), 
            5: (40.5795, -74.1502)
        }


        fig_choro.update_layout(
            mapbox_accesstoken=mapbox_token, 
            mapbox_style="carto-positron",
            mapbox_zoom=10, 
            mapbox_center = {"lat": center_dict[boro][0], "lon": center_dict[boro][1]}
        )

        fig_choro.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

        return bar, fig_choro