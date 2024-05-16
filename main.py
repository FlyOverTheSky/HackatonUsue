import sqlite3
import sys
from os import getcwd, getenv

import requests
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

sys.path.append(getcwd())
load_dotenv()
app = FastAPI()

API_TOKEN = getenv("API_TOKEN")
apiUrl = f"https://api.twelvedata.com/time_series?"

periods = {
    'short': 'procent_short_time',
    'medium': 'procent_medium_time',
    'long': 'procent_long_time'
}
risks = {
    'low': [0, 35],
    'medium': [36, 70],
    'high': [70, 100]
}

result = []
count_act = 0
total_price_act = 0


class User(BaseModel):
    id: int
    time_period: str
    risk_level: str


@app.get("/get_recomendation/")
async def root(user: User):
    global result, count_act, total_price_act
    result = []
    count_act = 0
    total_price_act = 0

    companies, avg_balance = db_worker(user)
    response = market_request(companies)

    for number in range(len(companies)):
        cur_company, cur_count, cur_price, total_price, avg_balance = get_prices(
            response,
            avg_balance,
            companies,
            number
        )
        if cur_count == 0:
            continue
        result.append(
            {
                "company_name": cur_company,
                "count_to_buy": cur_count,
                "act_price": cur_price,
                "total_price": total_price
            }
        )
    result.append(
        {
            "total_act_price": total_price_act,
            "count_act": count_act
        }
    )
    return result


def market_request(companies):
    current_apiurl = apiUrl
    current_apiurl += "symbol="
    for company in companies:
        current_apiurl += company[0] + ','
    current_apiurl += f"&interval=1day&apikey={API_TOKEN}"
    data = requests.get(current_apiurl).json()
    return data


def get_prices(response, avg_balance, companies, i):
    global count_act, total_price_act
    avg_price = avg_balance / (len(companies) - i)
    cur_company = companies[i][0]
    price_path = response[cur_company]['values'][0]
    cur_price = (float(price_path['open']) + float(price_path['close'])) / 2
    cur_count = avg_price // cur_price
    count_act += cur_count
    total_price = cur_count * cur_price
    total_price_act += total_price
    avg_balance -= total_price

    return cur_company, cur_count, cur_price, total_price, avg_balance


def db_connect(base):
    connection = sqlite3.connect(base)
    cursor = connection.cursor()
    return connection, cursor


def db_disconnect(connection):
    connection.close()

def db_worker(user):
    connection, cursor = db_connect('bank_accounts.db')
    cursor.execute(f"""
        SELECT wallet_id
        FROM users
        WHERE id = {user.id}
        """)
    wallet_id = cursor.fetchall()[0][0]
    cursor.execute(f"""
            SELECT average_balance
            FROM wallet
            WHERE id = {wallet_id}
            """)
    avg_balance = cursor.fetchall()[0][0]
    db_disconnect(connection)
    connection, cursor = db_connect('risk_management.db')
    cursor.execute(f"""
        SELECT name
        FROM Metrics
        WHERE {periods[user.time_period]} > {risks[user.risk_level][0]} AND {periods[user.time_period]} < {risks[user.risk_level][1]}
        ORDER BY {periods[user.time_period]} DESC
        """)
    companies = cursor.fetchall()
    db_disconnect(connection)

    return companies, avg_balance
