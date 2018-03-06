import os
from datetime import datetime, timedelta

import pandas as pd
import requests
import simplejson
from bokeh.embed import components
from bokeh.plotting import figure
from flask import Flask, render_template, request

with open('codes.txt', 'r') as f:
    codes = set(f.read().split())

app = Flask(__name__)

def get_stock_info(ticker, today=datetime.now()):
    '''
    Get stock prices for last 30 days from QUANDL API
    QUANDL_API_KEY key must be set in environment.
    For Docker, this can be done by docker run -e [your key here]
    For Heroku deployment, this can be done with heroku config:set QUANDL_API_KEY=[your key here]
    '''
    dates = ','.join((today-timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1,31))
    r = requests.get('https://www.quandl.com/api/v3/datatables/WIKI/PRICES.json',
                     params={'ticker': ticker, 'date': dates,
                             'api_key': os.environ.get('QUANDL_API_KEY')})
    if r.status_code==200:
        raw = simplejson.loads(r.text)
        data = pd.DataFrame(raw['datatable']['data'])[[1,2,3,4,5,9,10,11,12]]
        data.columns = ['date','open','high','low','close','adj_open','adj_high','adj_low','adj_close']
        data.set_index('date', inplace=True)
        data.index = pd.to_datetime(data.index)
        return data
    else:
      return 'Failed with status code {}'.format(r.status_code)

def create_plot(data, values, ticker, width=800, height=500):
    '''
    '''
    legends = {'open': 'Opening price',
               'high': 'High price',
               'low': 'Low price',
               'close': 'Closing price',
               'adj_open': 'Adjusted opening price',
               'adj_high': 'Adjusted high price',
               'adj_low': 'Adjusted low price',
               'adj_close': 'Adjusted closing price'}
    #Hex codes for primary seaborn color palette (I personally like them)
    colors = ['#1F77B4','#FF7F0E','#2CA02C','#D62728','#9467BD',
              '#8C564B','#E377C2','#7F7F7F','#BCBD22','#17BECF']
    p = figure(width=width, height=height, x_axis_type='datetime')
    if len(values) > 10:
        values = values[:10]
    for i, value in enumerate(values):
        p.line(data.index, data[value], legend=legends[value], line_color=colors[i])
    p.title.text = 'Stock prices for {} over last 30 days'.format(ticker)
    p.legend.location = 'bottom_right'
    p.grid.grid_line_alpha = 0
    p.xaxis.axis_label = 'Date'
    p.yaxis.axis_label = 'Price'
    p.ygrid.band_fill_color = 'gray'
    p.ygrid.band_fill_alpha = 0.05
    return p

@app.route('/', methods=['GET','POST'])
def index():
    if request.method == 'POST':
        # Validate all input
        ticker, values, err_msg = None, None, None
        if 'ticker' in request.form and request.form['ticker'].upper() in codes:
            ticker = request.form['ticker'].upper()
        if 'values' in request.form:
            values = [v.lower() for v in request.form.getlist('values')]
            values = [v for v in values if v in ['open', 'close', 'high', 'low']]
            if values and 'adjusted' in request.form:
                for i, value in enumerate(values):
                    values[i] = 'adj_' + value

        if ticker and values:
            # Return plot if inputs are valid
            data = get_stock_info(ticker)
            p = create_plot(data, values, ticker)
            script, div = components(p)
            return render_template('index.html',
                                   plot_div=div.strip(),
                                   plot_script=script.strip())
        else:
            # Return error message if inputs are not valid
            if ticker:
                err_msg = 'Uh-oh. I did not recognize that ticker symbol. Please try again with a valid input.'
            elif values:
                err_msg = 'Please select at least one value you would like to plot.'
            else:
                err_msg = 'Input error. Try again with valid ticker symbol and parameters.'
            return render_template('index.html', error_message=err_msg)

    else:
        return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
