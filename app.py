import os
import json

import requests
from bs4 import BeautifulSoup as bs
import pandas as pd

import twstock

from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)

from linebot.exceptions import (
    InvalidSignatureError
)

from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

app = Flask(__name__)

# LINE Chatbot token
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

def getStockPrice(stockno):
    stock = twstock.realtime.get(stockno)['realtime']
    stockpricestr = ''
    stockpricestr += '開盤價'+ '{:.2f}'.format(float(stock['open'])) + '\n'
    stockpricestr += '最高價'+ '{:.2f}'.format(float(stock['high'])) + '\n'
    stockpricestr += '最低價'+ '{:.2f}'.format(float(stock['low'])) + '\n'
    stockpricestr += '收盤價'+ '{:.2f}'.format(float(stock['latest_trade_price']))
    return stockpricestr

def getRevenue(stockno):
    url = f"http://jsjustweb.jihsun.com.tw/z/zc/zch/zch_{stockno}.djhtm"
    res = requests.get(url)
    soup = bs(res.text, 'lxml')
    tb = soup.select('table')[2]
    df = pd.read_html(tb.prettify(), header = 5)

    stockrevenue = ''
    stockrevenue += '年月 ' + str(df[0].iloc[0, 0]) + '%\n'
    stockrevenue += '營收 ' + str(df[0].iloc[0, 1]) + '仟元\n'
    stockrevenue += '月增率 ' + str(df[0].iloc[0, 2]) + '%\n'
    stockrevenue += '去年同期 ' + str(df[0].iloc[0, 3]) + '仟元\n'
    stockrevenue += '年增率 ' + str(df[0].iloc[0, 4]) + '%\n'
    stockrevenue += '累計營收 ' + str(df[0].iloc[0, 5]) + '仟元\n'
    stockrevenue += '累計營收年增率 ' + str(df[0].iloc[0, 6]) + '%\n'
    return stockrevenue

def getCredittransaction(stockno):
    url = f'https://goodinfo.tw/StockInfo/ShowBearishChart.asp?STOCK_ID={stockno}&CHT_CAT=DATE'
    headers = {
        'referer': 'https://goodinfo.tw/',
        'user-agent': 'Mozilla/5.0 (Windows NT 6.1; ) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.122 Safari/537.36'
    }
    res = requests.get(url, headers = headers)
    res.encoding = 'utf8'
    soup = bs(res.text, 'lxml')
    cells = soup.select('.solid_1_padding_4_2_tbl td')
    strtext = ''
    strtext += '融資增減 ' + cells[23].text + '\n'
    strtext += '融資使用率 ' + cells[25].text + '\n'
    strtext += '融券增減 ' + cells[39].text + '\n'
    strtext += '融券使用率 ' + cells[41].text + '\n'
    return strtext

def getStockDayTrade(stockno):
    url = f'https://goodinfo.tw/StockInfo/DayTrading.asp?STOCK_ID={stockno}'
    headers = {
        'referer': 'https://goodinfo.tw/',
        'user-agent': 'Mozilla/5.0 (Windows NT 6.1; ) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.122 Safari/537.36'
    }
    res = requests.get(url, headers = headers)
    res.encoding = 'utf8'
    soup = bs(res.text, 'lxml')
    cells = soup.select('#divDayTradingDetail td')
    strtext = ''
    strtext += '成交張數當沖 ' + cells[25].text + ' ％\n'
    strtext += '當沖總損益(萬元) ' + cells[30].text + '\n'
    strtext += '當沖均損益(元/張) ' + cells[31].text + '\n'
    return strtext

def getOperatingProfit(stockno, year, season):
    url = f'https://mops.twse.com.tw/mops/web/ajax_t163sb06?step=1&firstin=1&&TYPEK=sii&year={year}&season={season}'
    res = requests.get(url)
    soup = bs(res.text, 'lxml')
    tb = soup.select('.hasBorder')[0]
    dfsii = pd.read_html(tb.prettify(), header = 0)[0]

    url = f'https://mops.twse.com.tw/mops/web/ajax_t163sb06?step=1&firstin=1&&TYPEK=otc&year={year}&season={season}'
    res = requests.get(url)
    soup = bs(res.text, 'lxml')
    tb = soup.select('.hasBorder')[0]
    dfotc = pd.read_html(tb.prettify(), header = 0)[0]

    df = pd.concat([dfsii, dfotc], ignore_index = True)
    df['公司代號'] = df['公司代號'].astype(str)
    strtext = ''
    if len(df[df['公司代號'] == stockno]) > 0:
        index = df[df['公司代號'] == stockno].index[0]
        strtext += '營業收入 (百萬元) ' + str(df.iloc[index, 2]) + '\n'
        strtext += '毛利率(%) (營業毛利) / (營業收入) ' + str(df.iloc[index, 3]) + '\n'
        strtext += '營業利益率(%) (營業利益)/ (營業收入) ' + str(df.iloc[index, 4]) + '\n'
        strtext += '稅前純益率(%) (稅前純益)/ (營業收入) ' + str(df.iloc[index, 5]) + '\n'
        strtext += '稅後純益率(%) (稅後純益)/ (營業收入) ' + str(df.iloc[index, 6]) + '\n'
    else:
        strtext += f'此檔{stockno}股票尚未公告{year}/{season}的營益分析資料，請重新查詢!!'
    return strtext

def Help():
    strtext = '''
    請輸入以下指令查詢：\n
    股計查詢：@/[股票代碼]
    ex： @2330\n
    營收/[股票代碼]
    ex： 營收/2330\n
    資券/[股票代碼]
    ex： 資券/2330\n
    現股當沖/[股票代碼]
    ex： 現股當沖/2330\n
    營益分析/[股票代碼]/[年度]/[季別]
    ex： 營益分析/2330/109/1\n
    '''
    return strtext 


@app.route("/", methods=['GET'])
def hello():
    return 'hello heroku'

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_input = event.message.text
    if user_input == '?' or user_input == 'h':
        helptext = Help()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=helptext))
    elif user_input[0:1] == '@':
        stockno = user_input[1:].strip()
        stocktext = getStockPrice(stockno)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=stocktext))
    elif '營收/' in user_input:
        stockno = user_input.split('/')[1]
        stocktext = getRevenue(stockno)
        line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=stocktext))
    elif '資券/' in user_input:
        stockno = user_input.split('/')[1]
        stocktext = getCredittransaction(stockno)
        line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=stocktext))
    elif '現股當沖/' in user_input:
        stockno = user_input.split('/')[1]
        stocktext = getStockDayTrade(stockno)
        line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=stocktext))                
    elif '營益分析/' in user_input:
        stockno = user_input.split('/')[1]
        year = user_input.split('/')[2]
        season = user_input.split('/')[3]
        print(stockno, year, season)
        stocktext = getOperatingProfit(stockno, year, season)
        line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=stocktext)) 
    else:
        errortext = '輸入指令錯誤，請重新輸入!!!\n' + Help()
        line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=errortext)) 

if __name__ == "__main__":
    app.run()
