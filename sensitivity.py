import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import geopandas as gpd
import numpy as np

#Import analytical table
@st.cache
def get_analytical():
    analytical = pd.read_csv('data/EU_PDO_cat_variety.csv', na_values = ['', 'na', 'nan'])
    analytical['Main_vine_varieties'] = analytical['Main_vine_varieties'].str.split('/')
    analytical['Other_vine_varieties'] = analytical['Other_vine_varieties'].str.split('/')
    analytical = analytical[['PDOid', 'PDOnam', 'Category_of_wine_product', 'Main_vine_varieties']]
    analytical.sort_values('PDOnam', inplace = True)
    
    return(analytical)

@st.cache(allow_output_mutation=True)
def get_sensitivity():
    tbl_sens = gpd.read_file('data/pdo_sensitivity.gpkg')
    tbl_sens['catI'] = tbl_sens['catI'].astype(str)
    return(tbl_sens)

@st.cache
def get_shp():
    shp = gpd.read_file('data/sensitivity_groupings.gpkg')
    return(shp)

def get_nam(PDOid):
    return(analytical.loc[analytical['PDOid'] == PDOid, 'PDOnam'].unique()[0])

analytical = get_analytical()
shp = get_shp()
tbl_sens = get_sensitivity()
world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))

with st.sidebar:
    pdo_selected = st.selectbox('Choose PDO', options = analytical['PDOid'].unique(),
                                format_func = get_nam)

#Select PDO
selected_nam = get_nam(pdo_selected)
selected_data = analytical.loc[analytical['PDOid'] == pdo_selected]
selected_catI = shp.loc[shp['PDOid'] == pdo_selected, 'catI'].unique()[0]
selected_sensitivity = tbl_sens.loc[tbl_sens['PDOid'] == pdo_selected]

st.markdown('## Overview of selected PDO')
col1, col2 = st.columns(2)
col1.markdown(f'**Name: {selected_nam}**')
col2.markdown(f'**Climate class: {selected_catI}**')
col1, col2 = st.columns(2)
col1.markdown(f'**ID: {pdo_selected}**')
st.dataframe(selected_data[['Category_of_wine_product', 'Main_vine_varieties']])

with st.sidebar:
    #Select Wine Category
    category_options = np.sort(selected_data['Category_of_wine_product']).tolist()
    if 'Wine' in category_options:
        index = category_options.index('Wine')
    else:
        index = 0
    category_selected = st.selectbox('Choose category', options = category_options, index = index)

    #Select Variety
    variety_options = []
    for i in selected_data.loc[selected_data['Category_of_wine_product'] == category_selected, 'Main_vine_varieties']:
        variety_options += i
    variety_options = sorted(set(variety_options))
    variety_selected = st.selectbox('Choose variety', options = variety_options)

#Create map with PDO groups
pdo_group = shp.loc[(shp['Category_of_wine_product'] == category_selected) & 
                    (shp['catI'] == selected_catI) &
                    (shp['Main_vine_varieties'] == variety_selected)]
pdo_sel = tbl_sens.loc[tbl_sens['PDOid'] == pdo_selected]
pdo_class = tbl_sens.loc[tbl_sens['catI'] == selected_catI]

st.markdown('## PDO grouping')
st.caption('The PDO regions that fall into the same group as the selected PDO are shown below as yellow points. PDOs are grouped based on **Category of wine product**, **Variety** and **Climate class**. This means that all PDOs within the same group share the following characteristics: A) They produce the selected wine type using the selected variety and B) they fall into the same climate class. These PDOs are used to determine the climatic range for the selected variety. The grey points indicate PDOs that fall within the same climate class, but are not used to determine the climate range for the selected variety, because they do not authorize it for production of the selected wine category.')
st.caption(f'Selected variety: **{variety_selected}**')

fig, ax = plt.subplots()
world.to_crs(4326).plot(ax = ax, color = 'lightgrey', edgecolor = 'white', zorder = 0, lw = .5)
pdo_class.to_crs(4326).plot(ax = ax, markersize = 20, 
                            color = 'grey', alpha = .5, linewidth = 0.7)
pdo_group.to_crs(4326).plot(ax = ax, marker = 'o', markersize = 20, 
                            edgecolor = 'black', color = 'yellow', linewidth = 0.7)
pdo_sel.to_crs(4326).plot(ax = ax, marker = 'o', markersize = 20,
                          edgecolor = 'red', linewidth = 1, facecolor = "none")
ax.set_facecolor('lightblue')
ax.set_ylim(25, 55)
ax.set_xlim(-20, 30)
ax.set_xticks([])
ax.set_yticks([])
st.pyplot(fig)
st.caption(f'Group size: {len(pdo_group)} PDOs')

with st.expander('Detailed Group Info'):
    st.dataframe(pdo_group.drop('geometry', axis = 1))

st.markdown('## Climatic niche of authorized varieties')
st.caption("The suitable climate range for each variety is estimated using the minimum and maximum values of the bioclimatic indices from all PDOs of the same group (red points in the map above). The climate range for the authorized varieties in the selected PDO is shown as a blue bar in the figure below. The climatic niche for the selected PDO is then determined by combining the ranges of all authorized varieties and is indicated by the grey, dashed lines. This range is compared to the upper and lower limits extracted from the area under vines within the selected PDO using Corine (indicated via the secondary x-axis on top of the plot). The more restrictive value from the two approaches is used as upper and lower limit. Finally, the upper and lower limits are compared to the average index value within the selected PDO (red line) to determine the sensitivity.")
#Plot climatic range for single varieties
df_variety_range = shp.loc[(shp['PDOid'] == pdo_selected) &
                           (shp['Category_of_wine_product'] == category_selected)]

col1, col2 = st.columns([.3, 1])
idx_range = col1.radio('Select index to plot:', ('HI', 'DI', 'CNI'),
                       format_func = lambda x: {'HI': 'Huglin', 'DI': 'Dryness', 'CNI': 'Cool Night'}[x])

range_index = df_variety_range.groupby('Main_vine_varieties', as_index = False).agg({f'{idx_range}_mean_min': 'min', 
                                                                                     f'{idx_range}_mean_max': 'max'})
range_index['Index'] = idx_range
range_index.rename(columns = {f'{idx_range}_mean_min': 'min', f'{idx_range}_mean_max': 'max'}, inplace = True)

range_index['xlen'] = range_index['max'] - range_index['min']
range_index['xmean'] = (range_index['max'] + range_index['min']) /2
range_index.sort_values(['Index', 'xmean'], inplace = True)

idx_ranges = [(xmin, xlen) for xmin, xlen in zip(range_index['min'], range_index['xlen'])]

with col2:
    y_start = 0
    y_idx = []
    fig, ax = plt.subplots()
    for i in range(len(idx_ranges)):
        rmin, rlen = idx_ranges[i]
        
        # if rlen == 0.0:
        #     rlen = .1
            
        ax.broken_barh([(rmin, rlen)], (y_start, .5))
        y_idx.append(y_start+0.25)
        y_start += 1
        
    ax.axvline(x = range_index['min'].min(), color = 'grey', ls = '--', lw = .5)
    ax.axvline(x = range_index['max'].max(), color = 'grey', ls = '--', lw = .5)
    ax.axvline(x = df_variety_range[f'{idx_range}_mean'].mean(), color = 'red', lw = .5)
    #ax.axvline(x = df_variety_range[f'{idx_range}_max'].mean(), color = 'grey', lw = .5)
    ax.set_yticks(y_idx) 
    ax.set_yticklabels(range_index['Main_vine_varieties'].tolist(), fontsize = 9)
    
    ax2 = ax.twiny()
    ax2.set_xlim(ax.get_xlim())
    
    cmin = df_variety_range[f'{idx_range}_min'].mean()
    cmax = df_variety_range[f'{idx_range}_max'].mean()
    cmin = cmin + 0.1 if cmin == cmax else cmin
    ax2.set_xticks([cmin, cmax])
    ax2.set_xticklabels(['Corine lower', 'Corine upper'])
    ax2.get_xaxis().get_major_ticks()[0].set_pad(15)
    
    st.pyplot(fig)

st.caption('Note: There are some cases, where a selected variety is only cultivated in a single PDO to produce the selected wine category. In these cases the plot above is empty, as there is no range for this variety to display. Similarly, for some PDOs the lower and upper limits from Corine are very similar, because the viticultural area is so small.')

st.markdown('## Sensitivity')
st.caption(f'The sensitivity of the selected PDO is **{selected_sensitivity["Sensitivity"].round(2).values[0]}**. The map below shows a comparison of the selected PDO against the other PDOs from the same climate class. The color indicates the sensitivity. The selected PDO is highlighted with a red border.')

fig, ax = plt.subplots()
world.to_crs(4326).plot(ax = ax, color = 'lightgrey', edgecolor = 'white', zorder = 0, lw = .5)
pdo_class.to_crs(4326).plot(ax = ax, marker = 'o', 
                            edgecolor = 'black', linewidth = 0.7,
                            column = 'Sensitivity', cmap = 'viridis',
                            legend = True, legend_kwds={'shrink': 0.5},
                            vmin = 0, vmax = 1, markersize = 20)
pdo_sel.to_crs(4326).plot(ax = ax, marker = 'o', markersize = 20,
                          edgecolor = 'red', linewidth = 1, facecolor = "none")
ax.set_facecolor('lightblue')
ax.set_ylim(25, 55)
ax.set_xlim(-20, 30)
ax.set_xticks([])
ax.set_yticks([])
st.pyplot(fig)

st.caption(f'Group size: {len(pdo_class)} PDOs')

with st.expander('Detailed info on all PDOs in this climate class'):
    st.dataframe(pdo_class.drop('geometry', axis = 1))