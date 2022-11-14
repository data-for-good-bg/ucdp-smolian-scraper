import plotly.express as px
from settings import MAIN_PATH
import numpy as np
import os

def create_heatmap(data_frame, variable):

    heatmap_df = data_frame[['селище','година','месец',variable]].groupby(['селище','година','месец']).mean().reset_index()
    heatmap_df = heatmap_df.sort_values(['година','месец'])
    heatmap_df['дата'] = heatmap_df['година'].apply(lambda x:str(x)) \
                     +'-'+ heatmap_df['месец'].apply(lambda x:str(x) if len(str(x)) == 2 else f'0{x}')

    list_towns = sorted(heatmap_df['селище'].unique())
    list_date = [str(i) for i in heatmap_df['дата'].unique()]

    heatmap_df.set_index(['селище', 'дата'], inplace=True)

    z = []
    for town in list_towns:
        town_list = []
        for _date in list_date:
            try:
                town_list.append(heatmap_df[variable][town, _date])
            except KeyError:
                town_list.append(np.nan)
        z.append(town_list)


    fig_heatmap = px.imshow(z, x=list_date, y=list_towns, color_continuous_scale='YlGnBu', aspect="auto")
    fig_heatmap.update_xaxes(side="top")
    fig_heatmap.update_layout(title = f'Карта {variable.upper()}(средна стойност) по селище/година-месец'
                          ,template = 'presentation'
                          ,font_size = 15
                          ,height = 1800
                          ,width = 900
                          ,font=dict(family="Courier New, monospace"
                                     ,size=11
                                     ,color="black")
                          )

    fig_name = f'htmap_{variable[:2]}.png'
    fig_heatmap.write_image(os.path.join(f"{MAIN_PATH}/exports/images",fig_name)
                            ,engine='auto', format='png', scale = 3)

    # return fig_heatmap
