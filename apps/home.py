
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

import datetime
import pandas as pd
import numpy as np
import scipy.stats

from utilities import *
import config
from app import app
from apps import functions

# source data for actuarial calculations
# https://www.ssa.gov/oact/STATS/table4c6.html#fn2
# https://www.longevityillustrator.org


def serve_layout():

    return [

        html.Div([

            html.Div([

                html.Br(),

                dbc.Row(
                    [
                        dbc.Col(
                            html.H1("Retirement Planning in Easy Mode",
                                    className='display-4 app-header')
                        )
                    ],
                ),

                html.Br(),

                html.Div('''Planning your finances can be complicated. Here are five questions that
        that can help you build a rough, but fast, roadmap for your future.''', className='text-note'),

                html.Br(),

                html.Br(),

                dbc.Row(
                    [

                        dbc.Col(width=1),

                        dbc.Col(
                            html.Div('How Old Are You Now?', className='input-questions', style={'width': '75%', 'margin': 'auto'}), width=2),

                        dbc.Col(
                            html.Div('At What Age Do You Want to Retire?', className='input-questions'), width=2),

                        dbc.Col(
                            html.Div('How Much Have You Currently Saved?', className='input-questions'), width=2),

                        dbc.Col(
                            html.Div('How Much Do You Save a Year?', className='input-questions'), width=2),

                        dbc.Col(
                            html.Div('How Much Will You Spend Per Year in Retirement?', className='input-questions'), width=2),

                        dbc.Col(width=1),


                    ],
                    align="center",
                    no_gutters=True,
                ),

                dbc.Row(
                    [

                        dbc.Col(width=1),

                        dbc.Col([
                            dcc.Input(id='my_age_input', value='35',
                                      className='input-box'),
                        ], width=2),

                        dbc.Col([
                            dcc.Input(id='retirement_age_input',
                                      value='50', className='input-box'),
                        ], width=2),

                        dbc.Col([
                            dcc.Input(id='my_wealth_input', value='$600,000',
                                      className='input-box'),
                        ], width=2),

                        dbc.Col([
                            dcc.Input(id='my_save_input', value='$45,000',
                                      className='input-box'),
                        ], width=2),

                        dbc.Col([
                            dcc.Input(id='my_spend_input', value='$70,000',
                                      className='input-box'),
                        ], width=2),

                        dbc.Col(width=1),


                    ],
                    align="center",
                    no_gutters=True,
                ),

                html.Br(),
                html.Br(),

                html.Div([
                    dbc.Button("GO", id='start_input', style={'height': '75px', 'width': '150px', 'font-size': '3rem',
                                                              'text-align': 'center', 'background-color': '#26BE81', 'border': '5px solid #267B83',
                                                              'margin-bottom': '30px'})],
                         style={'text-align': 'center'}),

                html.Br(),
                html.Br(),
                html.Br(),



                html.Div(id='output'),
            ], className='body')

        ], style={'padding-left': '5%', 'padding-right': '5%'})

    ]


layout = serve_layout

mortality_df = pd.read_csv('mortality_table.csv')
mortality_df.set_index('current_age', inplace=True)
mortality_df['forward_survival_prob_1y'] = 1 - ((mortality_df['forward_death_prob_1y_male'] +
                                                 mortality_df['forward_death_prob_1y_female']) / 2)


# calculate account trajectory
@app.callback(dash.dependencies.Output('output', 'children'),

              [dash.dependencies.Input('start_input', 'n_clicks')],

              [dash.dependencies.State('my_age_input', 'value'),
               dash.dependencies.State('retirement_age_input', 'value'),
               dash.dependencies.State('my_wealth_input', 'value'),
               dash.dependencies.State('my_save_input', 'value'),
               dash.dependencies.State('my_spend_input', 'value')
               ])
def display_page(n_clicks,
                 user_age,
                 user_retirement_age,
                 user_wealth,
                 user_save,
                 user_spend):

    if n_clicks is None:
        return html.Div()

    else:

        # derive extra parameters for modelling wealth trajectory
        user_age = int(user_age)
        user_retirement_age = int(user_retirement_age)
        user_wealth = int(user_wealth.replace(',','').replace('$',''))
        user_save = int(user_save.replace(',','').replace('$',''))
        user_spend = int(user_spend.replace(',','').replace('$',''))

        num_simulations = 10000

        years_to_retire = user_retirement_age - user_age
        # because we want to include the current age
        years_to_retire_plus_one = years_to_retire + 1
        current_year = datetime.datetime.now().year

        # expected age at death based on mortality tables
        this_mortality_df = mortality_df.copy()
        expected_age_at_death = this_mortality_df.loc[
            user_age, 'expected_years_till_death_male']
        expected_age_at_death += this_mortality_df.loc[
            user_age, 'expected_years_till_death_female']
        expected_age_at_death /= 2
        expected_age_at_death = int(expected_age_at_death) + user_age

        # calculate the cumulative survival probabilities
        # (what age is the user expected to live to with 25%, 5%, 1% probability conditional
        # on their current age)

        # first, subset the dataset to drop ages that are less than the users expected age at death
        # (this is going to be the 50% survivial probability)
        this_mortality_df = this_mortality_df[user_age:]
        this_mortality_df['cum_survival_prob'] = this_mortality_df[
            'forward_survival_prob_1y'].cumprod()

        age_list = this_mortality_df.index.tolist()
        cum_survival_prob_list = this_mortality_df[
            'cum_survival_prob'].tolist()

        age_at_25_pct_survival_prob = functions.calc_age_for_survival_prob(
            0.25, age_list, cum_survival_prob_list)
        age_at_10_pct_survival_prob = functions.calc_age_for_survival_prob(
            0.10, age_list, cum_survival_prob_list)
        age_at_5_pct_survival_prob = functions.calc_age_for_survival_prob(
            0.05, age_list, cum_survival_prob_list)
        age_at_1_pct_survival_prob = functions.calc_age_for_survival_prob(
            0.01, age_list, cum_survival_prob_list)

        years_to_1_pct_survival_prob = age_at_1_pct_survival_prob - user_age
        years_in_retirement = age_at_1_pct_survival_prob - user_retirement_age + 1
        num_periods = age_at_1_pct_survival_prob - user_age + 1

        # init a dataframe with ages and calendar years in the rows
        # the ages range from the current user age to the age that the user has a 1% probability of reaching
        # (for example, a 40 year old today might have a 1% chance of living to 100 so let's have the
        # chart x-axis show values from age 39 to age 100, inclusive)
        df = pd.DataFrame(
            {'age': list(range(user_age, age_at_1_pct_survival_prob + 1))})
        df['year'] = list(range(current_year, current_year +
                                years_to_1_pct_survival_prob + 1))
        assert df.shape[0] == num_periods, 'error'

        # simulate market returns based on a random walk
        equity_return_sim1 = functions.random_walk_simulations(mean=0.06,
                                                               stdev=0.14,
                                                               periods=num_periods,
                                                               num_simulations=num_simulations)

        bond_return_sim1 = np.full_like(equity_return_sim1, fill_value=0.01)
        bond_return_sim1[:, 0] = 0.0

        # get historical annual returns to use in sampling
        years, sp500, ust_3m, ust, bbb = functions.get_historical_annual_returns()
        num_historical_samples = len(years)

        # simulate market returns based on continuous historical sampling
        _, equity_return_sim2, bond_return_sim2 = functions.build_continuous_sampled_returns(num_periods_per_simulation=num_periods,
                                                                                             num_simulations=num_simulations,
                                                                                             year_list=years,
                                                                                             sp500_list=sp500,
                                                                                             ust_list=ust)

        # simulate market returns based on discontinuous historical sampling
        _, equity_return_sim3, bond_return_sim3 = functions.build_discontinuous_sampled_returns(num_periods_per_simulation=num_periods,
                                                                                                sub_sample_length=5,
                                                                                                num_simulations=num_simulations,
                                                                                                year_list=years,
                                                                                                sp500_list=sp500,
                                                                                                ust_list=ust)

        equity_returns = np.concatenate(
            [equity_return_sim1, equity_return_sim2, equity_return_sim2], axis=0)
        bond_returns = np.concatenate(
            [bond_return_sim1, bond_return_sim2, bond_return_sim2], axis=0)

        print(equity_returns[0])

        # calculate asset allocation between equity and bonds in each period
        allocations = functions.calc_asset_allocations(user_age=user_age,
                                                       retirement_age=user_retirement_age,
                                                       final_age=age_at_1_pct_survival_prob,
                                                       percent_at_retirement=0.6,
                                                       glide_length=10)

        contributions = functions.calc_contributions(user_age=user_age,
                                                     retirement_age=user_retirement_age,
                                                     final_age=age_at_1_pct_survival_prob,
                                                     user_save=user_save,
                                                     user_spend=user_spend)

        total_user_save = contributions[:user_retirement_age-user_age].sum()
        total_user_save = functions.convert_dollar_number_to_text(total_user_save)

        # make an array of allocations for every simulation
        allocations = np.array(
            [allocations for i in range(num_simulations * 3)])
        contributions = np.array(
            [contributions for i in range(num_simulations * 3)])

        # calc wealth during savings phase
        # init an [num_simulations x 1]-sized array with the starting wealth
        starting_wealth_array = np.full(shape=equity_returns.shape[0],
                                        fill_value=user_wealth)

        # calculate the growth of wealth given market returns and contributions
        # during the savings phase
        wealths = functions.calc_wealth_trajectory(starting_wealth=starting_wealth_array,
                                                   equity_returns=equity_returns,
                                                   bond_returns=bond_returns,
                                                   allocations=allocations,
                                                   contributions=contributions)

        # get the final wealth values (as array) at the end of the last year of the savings phase
        # (the wealth at the start of retiremente)
        wealth_at_retirement = wealths[:, years_to_retire_plus_one]

        # calculate the different wealth trajectories
        # (eg the median path, 25th percentile path, etc)
        trajectories = functions.wealth_distributions(wealths)
        median_trajectory = trajectories['median']

        df['median_wealth'] = median_trajectory

        # calculate wealth distribution statistics at retirement
        retirement_wealths = {}
        retirement_wealths_text = {}
        idx_at_retirement = user_retirement_age - user_age

        # get the retirement wealth distribution at retirement age
        for i in [75,50,25,5, 1]:
            retirement_wealths[i] =trajectories[i][idx_at_retirement]
            retirement_wealths_text[i] = functions.convert_dollar_number_to_text(retirement_wealths[i])


        # make a chart with wealth over time

        # the bars that represent wealth during the savings phase should be green
        # and the bars during the retirement phase are blue
        # bar_colors = ['#26BE81'] * (years_to_retire)
        bar_colors = ['#26BE81'] * (years_to_retire)
        bar_colors = bar_colors + ['green']
        # bar_colors = bar_colors + ['#2663be'] * (years_in_retirement + 1)
        bar_colors = bar_colors + ['#f8615a'] * (years_in_retirement + 1)

        # make chart
        data = [
            {'x': df['age'],
             'y': df['median_wealth'],
             'type': 'bar',
             'marker': {'color': bar_colors}},
        ]

        chart_lines = [

            # vertical line at expected age at death (50% survival probability)
            {
                'x0': expected_age_at_death,
                'y0': 0,
                'x1': expected_age_at_death,
                'y1': 1,
                'yref': 'paper',
                'type': 'line',
                'line': {'color': 'orange', 'width': 5, 'dash': 'dot'}
            },

            {
                'x0': age_at_25_pct_survival_prob,
                'y0': 0,
                'x1': age_at_25_pct_survival_prob,
                'y1': 1,
                'yref': 'paper',
                'type': 'line',
                'line': {'color': 'orange', 'width': 4, 'dash': 'dot'}
            },

            {
                'x0': age_at_5_pct_survival_prob,
                'y0': 0,
                'x1': age_at_5_pct_survival_prob,
                'y1': 1,
                'yref': 'paper',
                'type': 'line',
                'line': {'color': 'orange', 'width': 3, 'dash': 'dot'}
            },

            {
                'x0': age_at_1_pct_survival_prob,
                'y0': 0,
                'x1': age_at_1_pct_survival_prob,
                'y1': 1,
                'yref': 'paper',
                'type': 'line',
                'line': {'color': 'orange', 'width': 2, 'dash': 'dot'}
            },

        ]

        chart_annotations = [
            {'x': expected_age_at_death,
             'y': -0.2,
             'yref': 'paper',
             'text': '50%'.format(expected_age_at_death),
             'showarrow': False,
             'font': {'color': 'orange', 'family': 'avenir', 'size': 12}},

            {'x': age_at_10_pct_survival_prob,
             'y': -0.3,
             'yref': 'paper',
             'text': 'Probabilities of Living To These Ages',
             'showarrow': False,
             'font': {'color': 'orange', 'family': 'avenir', 'size': 12}},


            {'x': age_at_25_pct_survival_prob,
             'y': -0.2,
             'yref': 'paper',
             'text': '25%',
             'showarrow': False,
             'font': {'color': 'orange', 'family': 'avenir', 'size': 12}},

            {'x': age_at_5_pct_survival_prob,
             'y': -0.2,
             'yref': 'paper',
             'text': '5%',
             'showarrow': False,
             'font': {'color': 'orange', 'family': 'avenir', 'size': 12}},

            {'x': age_at_1_pct_survival_prob,
             'y': -0.2,
             'yref': 'paper',
             'text': '1%',
             'showarrow': False,
             'font': {'color': 'orange', 'family': 'avenir', 'size': 12}}

        ]

        layout = {'title': 'Your Expected Wealth Over Time',
                  'annotations': chart_annotations,
                  'height': 300,
                  'margin': {'t': 30},
                  'shapes': chart_lines,
                  }

        figure = {'data': data,
                  'layout': layout}

        mortality_x = np.arange(expected_age_at_death, 105, .01)
        mortality_y = scipy.stats.norm.pdf(
            mortality_x, expected_age_at_death, 15)

        return html.Div([

            html.Hr(),

            # first result section
            dbc.Row(
                [
                    dbc.Col(

                        html.Div([

                            html.H1("You're in Excellent Shape!", className='display-6',
                                    style={'text-align': 'center', 'color': '#26BE81', }),

                            html.H4("You are on track for financial security for the rest of your life", className='display-6',
                                    style={'text-align': 'center', 'color': '#grey', })

                        ]), width=5),

                    dbc.Col(
                        dcc.Graph(id='chart', figure=figure), width=7),


                ], align="center", no_gutters=True,
            ),

            html.Br(),
            html.Br(),
            html.Br(),
            html.Br(),
            html.Br(),
            html.Br(),

            # second result section
            html.Div([

                html.Br(),
                html.Br(),

                dbc.Row([
                    dbc.Col(

                        html.Div([

                            html.H1("In {}, at your target retirement age of {}:".format(current_year + years_to_retire,
                                                                                         user_retirement_age), className='display-6',
                                    style={'text-align': 'center', 'color': 'white', }),

                        ]), width=12),


                ], align="center", no_gutters=True),

                dbc.Row([

                    dbc.Col(
                        html.Div([
                            html.Img(src='money.png', style={'height':'150px'}),
                            html.Br(),
                            html.Br(),
                            html.H4('''You'll have contributed an additional {} to savings over the next {} years'''.format(total_user_save,
                                user_retirement_age-user_age-1))
                        ])
                        , width=6, style={'padding-left': '10%', 'padding-right': '10%'}),

                    dbc.Col(
                        html.Div([
                            html.Img(src='stock-market.png', style={'height':'150px'}),
                            html.Br(),
                            html.Br(),
                            html.H4('''And we assumed your investments glide into a 60/40 split between stocks 
                                and bonds by the time you retire''') 
                        ])
                        , width=6, style={'padding-left': '10%', 'padding-right': '10%'})
                ], style={'padding-top': '50px'}),

                html.Br(),
                html.Br(),
                html.Br(),


                html.H3("We don't actually know what the market will do, so we've mapped out a few scenarios for \
                 how your savings might grow until retirement", style={'margin-left': '15%', 'margin-right': '15%'}),

                html.Br(),
                html.Br(),
                html.Br(),


                dbc.Row([
                    dbc.Col(

                        html.Div([

                            html.H1("", className='display-6',
                                    style={'text-align': 'center', 'color': 'white', }),

                        ]), width=6),

                    dbc.Col(

                        html.Div([

                            html.H3("In an optimistic scenario (75th percentile), you have {}".format(retirement_wealths_text[75]), className='display-6',
                                    style={'text-align': 'center', 'color': 'white', }),

                        ]), width=6),


                ], align="center", no_gutters=True),

                html.Br(),

                      dbc.Row([
                    dbc.Col(

                        html.Div([

                            html.H1("", className='display-6',
                                    style={'text-align': 'center', 'color': 'white', }),

                        ]), width=6),

                    dbc.Col(

                        html.Div([

                          html.H3("In the baseline scenario (50th percentile), you have {}".format(retirement_wealths_text[50]), className='display-6',
                                    style={'text-align': 'center', 'color': 'white', }),

                        ]), width=6),


                ], align="center", no_gutters=True),

                html.Br(),

                dbc.Row([
                    dbc.Col(

                        html.Div([

                            html.H1("", className='display-6',
                                    style={'text-align': 'center', 'color': 'white', }),

                        ]), width=6),

                    dbc.Col(

                        html.Div([

                            html.H3("In a possible scenario (25th percentile), you have {}".format(retirement_wealths_text[25]), className='display-6',
                                    style={'text-align': 'center', 'color': 'white', }),

                        ]), width=6),


                ], align="center", no_gutters=True),


                html.Br(),

                dbc.Row([
                    dbc.Col(

                        html.Div([

                            html.H1("", className='display-6',
                                    style={'text-align': 'center', 'color': 'white', }),

                        ]), width=6),

                    dbc.Col(

                        html.Div([

                            html.H3("In a pessimistic scenario (5th percentile), you have {}".format(retirement_wealths_text[5]), className='display-6',
                                    style={'text-align': 'center', 'color': 'white', }),

                        ]), width=6),


                ], align="center", no_gutters=True),

            ], className='green-background')


        ])
