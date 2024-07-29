from app import app
from flask import render_template, request, jsonify, redirect, url_for
from app.databaseHelper import execute_query
from app.realtimePrice import get_current_price, get_last_30_days_prices


# Define the home route
@app.route('/', methods=['GET'])
def home():
    return render_template('home.html')


# Define the portfolio route
@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    query = """
    select p.user_name, p.email, p.balance, p.total_value, s.symbol, s.stock_name, ps.quantity, s.price, s.id
    from portfolio p join portfolio_stocks ps on p.id = ps.portfolio_id
    join stocks s on ps.stock_id = s.id
    where p.id = 1
    """
    # Execute the query to obtain the result
    result = execute_query(query)
    balance = result[0]['balance'] if result else 0
    total_value = result[0]['total_value'] if result else 0
    user_name = result[0]['user_name'] if result else ''
    email = result[0]['email'] if result else ''

    stock_query = """
    select id, price, stock_name, symbol from stocks
    """
    stocks_can_buy = execute_query(stock_query)

    return render_template('portfolio.html', user_name=user_name, email=email,
                           balance=balance, total_value=total_value, stocks_can_sell=result,
                           stocks_can_buy=stocks_can_buy)


# Define the buy stock route
# url = /api/portfolio/<portfolio_id>/buy
@app.route('/api/portfolio/<int:portfolio_id>/buy', methods=['POST'])
def buy_stock(portfolio_id):
    data = request.form
    stock_id = data.get('stock_id')
    quantity = int(data.get('quantity'))

    print(f"buy stock_id: {stock_id}, quantity: {quantity}")

    try:

        # check if we have enough balance
        balance_query = """
        select balance from portfolio where id = %s
        """
        balance = execute_query(balance_query, (portfolio_id,))[0]['balance']

        # Get the stock price
        stock_query = """
                select price, stock_name from stocks where id = %s
                """
        stock_info = execute_query(stock_query, (stock_id,))
        stock_price = stock_info[0]['price']
        stock_name = stock_info[0]['stock_name']
        if balance < quantity * stock_price:
            return jsonify({'error': 'Not enough balance'}), 400

        # Update the transaction table
        transaction_query = """
        INSERT INTO transactions (portfolio_id, stock_id, transaction_type, quantity) VALUES (%s, %s, 'buy', %s)
        """
        execute_query(transaction_query, (portfolio_id, stock_id, quantity))

        # Update the portfolio_stock table
        portfolio_stock_query = """
        INSERT INTO portfolio_stocks (stock_name, portfolio_id, stock_id, quantity) VALUES (%s, %s, %s, %s)
        on duplicate key update quantity = quantity + values(quantity)
        """
        execute_query(portfolio_stock_query, (stock_name, portfolio_id, stock_id, quantity))

        # Update the portfolio table
        portfolio_query = """
        update portfolio set balance = balance - %s, total_value = total_value + %s where id = %s
        """
        execute_query(portfolio_query, (quantity * stock_price, quantity * stock_price, portfolio_id))

        return redirect(url_for('buy_status', status='success', message='Stock bought successfully'))

    except Exception as e:
        return redirect(url_for('buy_status', status='error', message=str(e)))


# Define the sell stock route
# url = /api/portfolio/<portfolio_id>/sell
@app.route('/api/portfolio/<int:portfolio_id>/sell', methods=['POST'])
def sell_stock(portfolio_id):
    data = request.form
    stock_id = data.get('stock_id')
    quantity = int(data.get('quantity'))

    print(f"sell stock_id: {stock_id}, quantity: {quantity}")

    try:

        # check if we have enough stock to sell
        portfolio_stocks_query = """
        select quantity from portfolio_stocks where portfolio_id = %s and stock_id = %s
        """
        stock_quantity = execute_query(portfolio_stocks_query, (portfolio_id, stock_id))[0]['quantity']

        print("stock_quantity in sell: ", stock_quantity)

        if stock_quantity < quantity:
            return jsonify({'error': 'Not enough stock to sell'}), 400

        # Update the transaction table
        transaction_query = """
        INSERT INTO transactions (portfolio_id, stock_id, transaction_type, quantity) VALUES (%s, %s, 'sell', %s)
        """
        execute_query(transaction_query, (portfolio_id, stock_id, quantity))

        # Get the stock price
        stock_query = """
        select price, stock_name from stocks where id = %s
        """
        stock_info = execute_query(stock_query, (stock_id,))
        stock_price = stock_info[0]['price']
        stock_name = stock_info[0]['stock_name']

        print(stock_info)

        # Update the portfolio_stock table
        portfolio_stock_query = """
        INSERT INTO portfolio_stocks (stock_name, portfolio_id, stock_id, quantity) VALUES (%s, %s, %s, %s)
        on duplicate key update quantity = quantity - values(quantity)
        """
        execute_query(portfolio_stock_query, (stock_name, portfolio_id, stock_id, quantity))

        # Update the portfolio table
        portfolio_query = """
        update portfolio set balance = balance + %s, total_value = total_value - %s where id = %s
        """
        execute_query(portfolio_query,
                      (quantity * stock_price, quantity * stock_price, portfolio_id))

        return redirect(url_for('sell_status', status='success', message='Stock sold successfully'))

    except Exception as e:
        return redirect(url_for('sell_status', status='error', message=str(e)))


# Define the buy status route
@app.route('/api/buy-status', methods=['GET'])
def buy_status():
    status = request.args.get('status', 'error')
    message = request.args.get('message', 'An unknown error occurred.')
    return render_template('buyStatus.html', status=status, message=message)


# Define the sell status route
@app.route('/api/sell-status', methods=['GET'])
def sell_status():
    status = request.args.get('status', 'error')
    message = request.args.get('message', 'An unknown error occurred.')
    return render_template('sellStatus.html', status=status, message=message)
