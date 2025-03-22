from flask import Flask, render_template, redirect, url_for, request, jsonify
import sqlite3
import yfinance as yf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
import plotly.graph_objects as go
import json
import plotly



app = Flask(__name__)

def get_current_value(isin):
    try:
        ticker = yf.Ticker(isin)
        info = ticker.info
        if 'regularMarketPrice' in info and info['regularMarketPrice'] is not None:
            return info['regularMarketPrice']
        else:
            print(f"Advertencia: No se encontró precio para {isin}")
            return 0  # Puedes cambiar esto a otro valor si lo prefieres
    except Exception as e:
        print(f"Error al obtener el precio de {isin}: {e}")
        return 0  # Evita que falle el programa

def create_graph(ticker, ax):
    data = yf.download(ticker, period="1mo")
    sns.set(style="whitegrid")

    data['Close'].plot(ax=ax, color='#000000', linewidth=2.5, linestyle='-')
    ax.set_facecolor('#B0B0B0')
    ax.set_title('')
    ax.set_xlabel('')
    ax.set_ylabel('')
    ax.tick_params(axis='x', colors='none')
    ax.tick_params(axis='y', colors='none')

    ax.xaxis.set_major_locator(plt.MaxNLocator(10))
    ax.yaxis.set_major_locator(plt.MaxNLocator(10))
    ax.grid(color='#FFFFFF', linestyle='-', linewidth=0.5)
def init_db():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS investments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                isin TEXT NOT NULL,
                asset_name TEXT NOT NULL,
                purchase_value REAL NOT NULL,
                amount REAL NOT NULL,
                current_value REAL,
                total_money REAL,
                profit_loss_percentage REAL
            )
        ''')
        conn.commit()

        # Añadir activos iniciales si la tabla está vacía
        cursor.execute('SELECT COUNT(*) FROM investments')
        if cursor.fetchone()[0] == 0:
            investments = [
                ("0P000125T6.F", "GVC GAESCO 300 PLACES WORLDWIDE, FI CLASE A", 12.7608, 1950),
                ("0P00000DQZ.F", "GVC GAESCO BOLSALIDER, FI CLASE A", 9.3687, 3900),
                ("0P00001QND.F", "GVC GAESCO JAPÓN, FI", 11.7407, 500),
                ("0P0001B7DE.F", "GVC GAESCO RENTA FIJA FLEXIBLE, FI CLASE A", 10.4163, 35000),
                ("0P0001R4YK.F", "GVC GAESCO RENTA FIJA HORIZONTE 2027, FI", 100.0741, 40000),
                ("0P00000DRB.F", "GVC GAESCO CONSTANTFONS, FI", 9.1297, 10000),
                ("BTC-EUR", "Bitcoin", 97542.52, 272.38),
                ("B2M-USD", "Bit2Me Token", 0.0165, 21),
                ("0P0001L8YS.F", "Baskepensiones Bolsa Euro EPSV", 4.5678, 5000)
            ]

            for investment in investments:
                isin = investment[0]
                asset_name = investment[1]
                purchase_value = investment[2]
                amount = investment[3]
                
                current_value = get_current_value(isin)
                profit_loss_percentage = ((current_value - purchase_value) / purchase_value) * 100
                total_money = amount + (amount * profit_loss_percentage / 100)
                
                cursor.execute('''
                    INSERT INTO investments (isin, asset_name, purchase_value, amount, current_value, total_money, profit_loss_percentage)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (isin, asset_name, purchase_value, amount, current_value, total_money, profit_loss_percentage))

            conn.commit()

init_db()
@app.route('/')
def index():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM investments')
        investments = cursor.fetchall()
        
        total_quantity = sum(float(investment[4]) for investment in investments)
        total_money = sum(float(investment[6]) for investment in investments)
        total_purchase_value = sum(float(investment[3]) for investment in investments)
    
    return render_template('index.html', investments=investments, total_quantity=total_quantity, total_money=total_money, total_purchase_value=total_purchase_value)

@app.route('/update-assets', methods=['GET'])
def update_assets():
    try:
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, isin, purchase_value, amount FROM investments')
            investments = cursor.fetchall()
            for investment in investments:
                id = investment[0]
                isin = investment[1]
                purchase_value = investment[2]
                amount = investment[3]
                current_value = get_current_value(isin)
                profit_loss_percentage = ((current_value - purchase_value) / purchase_value) * 100
                total_money = amount + (amount * profit_loss_percentage / 100)
                cursor.execute('''
                    UPDATE investments
                    SET current_value = ?, total_money = ?, profit_loss_percentage = ?
                    WHERE id = ?
                ''', (current_value, total_money, profit_loss_percentage, id))
            conn.commit()
        return jsonify(success=True)
    except Exception as e:
        print(f"Error al actualizar los activos: {e}")
        return jsonify(success=False)
@app.route('/add-asset-window')
def add_asset_window():
    return render_template('add_asset.html')

@app.route('/add-asset', methods=['POST'])
def add_asset():
    try:
        data = request.get_json()
        isin = data['isin']
        asset_name = data['asset_name']
        purchase_value = float(data['purchase_value'])
        amount = float(data['amount'])
        
        current_value = get_current_value(isin)
        profit_loss_percentage = ((current_value - purchase_value) / purchase_value) * 100
        total_money = amount + (amount * profit_loss_percentage / 100)
        
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO investments (isin, asset_name, purchase_value, amount, current_value, total_money, profit_loss_percentage)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (isin, asset_name, purchase_value, amount, current_value, total_money, profit_loss_percentage))
            conn.commit()
        return jsonify(success=True)
    except Exception as e:
        print(f"Error al agregar el activo: {e}")
        return jsonify(success=False, error=str(e))
@app.route('/edit-asset', methods=['POST'])
def edit_asset():
    try:
        data = request.get_json()
        isin = data['isin']
        purchase_value = float(data['purchase_value'])
        amount = float(data['amount'])
        
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT isin FROM investments WHERE isin = ?', (isin,))
            result = cursor.fetchone()
            if result:
                current_value = get_current_value(isin)
                profit_loss_percentage = ((current_value - purchase_value) / purchase_value) * 100
                total_money = amount + (amount * profit_loss_percentage / 100)
                
                cursor.execute('''
                    UPDATE investments
                    SET purchase_value = ?, amount = ?, current_value = ?, total_money = ?, profit_loss_percentage = ?
                    WHERE isin = ?
                ''', (purchase_value, amount, current_value, total_money, profit_loss_percentage, isin))
                conn.commit()
                return jsonify(success=True)
            else:
                print(f"Activo no encontrado: {isin}")
                return jsonify(success=False, error="Activo no encontrado")
    except Exception as e:
        print(f"Error al editar el activo: {e}")
        return jsonify(success=False, error=str(e))
@app.route('/edit-asset-window')
def edit_asset_window():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM investments')
        investments = cursor.fetchall()
    return render_template('edit_asset.html', investments=investments)

@app.route('/graphs')
def graphs():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT isin, asset_name FROM investments')
        investments = cursor.fetchall()

    images = []
    for investment in investments:
        ticker = investment[0]
        fig, ax = plt.subplots(figsize=(6, 4))
        create_graph(ticker, ax)
        img = io.BytesIO()
        plt.savefig(img, format='png', transparent=True, bbox_inches='tight', pad_inches=0)
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode()
        images.append({'url': plot_url, 'name': investment[1]})

    return render_template('graphs.html', images=images)
@app.route('/tables')
def tables():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM investments')
        investments = cursor.fetchall()
        # Filtrar según la columna investment_type (índice 8)
        dca = [inv for inv in investments if inv[8] == "DCA"]
        renta_fija = [inv for inv in investments if inv[8] == "Renta Fija"]
        renta_variable = [inv for inv in investments if inv[8] == "Renta Variable"]
        cryptomonedas = [inv for inv in investments if inv[8] == "Cryptomonedas"]
        acciones = [inv for inv in investments if inv[8] == "Acciones"]
        epsv = [inv for inv in investments if inv[8] == "EPSV"]
    return render_template('tables.html', dca=dca, renta_fija=renta_fija, renta_variable=renta_variable, cryptomonedas=cryptomonedas, acciones=acciones, epsv=epsv)

@app.route('/bank')
def bank():
    banks = [
        ("Kutxabank Nomina", 12295.94, 0, ""),
        ("Kutxabank Conjunta", 991.74, 0, ""),
        ("Trade Republic", 2050, 1.71, ""),
        ("Revolut", 300, 1.51, ""),
        ("Bit2Me", 800, 0, ""),
        ("My Investor", 0, 0, "")
    ]

    total_inversion = sum(bank[1] for bank in banks)
    total_resultado = sum(bank[1] + (bank[1] * bank[2] / 100) for bank in banks if bank[3] == "")
    
    banks.append(("TOTALES", total_inversion, "", total_resultado))

    return render_template('bank.html', banks=banks)
@app.route('/investment-categories')
def investment_categories():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT asset_name, total_money FROM investments')
        data = cursor.fetchall()

    data.sort(key=lambda x: x[1], reverse=True)  # Ordenamos de mayor a menor
    labels = [row[0] for row in data]
    sizes = [row[1] for row in data]
    total_money_sum = sum(sizes)
    percentages = [(size / total_money_sum) * 100 for size in sizes]

    colors = sns.color_palette("husl", len(labels))
    color_hex = [f'#{int(c[0]*255):02x}{int(c[1]*255):02x}{int(c[2]*255):02x}' for c in colors]

    # Gráfico interactivo con efecto hover individual en cada barra
    fig = go.Figure()
    for label, percentage, color in zip(labels, percentages, color_hex):
        fig.add_trace(go.Bar(
            x=[label],
            y=[percentage],
            text=f"{percentage:.1f}%",
            textposition='outside',
            textfont=dict(
                size=16,  # Tamaño de la fuente
                color='#00FF00'  # Color de los porcentajes
            ),
            marker=dict(color=color, line=dict(width=2, color="white")),
            hoverinfo='text',
            hovertext=f"<b>{label}</b>: {percentage:.2f}%",
        ))

    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showticklabels=False),
        yaxis=dict(tickfont=dict(color="#00FF00")),
        hovermode='x',
        margin=dict(l=40, r=40, t=20, b=20),
    )

    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    color_data = list(zip(color_hex, labels, sizes, percentages))

    return render_template('investment_categories.html', graph_json=graph_json, data=color_data, total_money_sum=total_money_sum)
@app.route('/pie-chart')
def pie_chart():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM investments')
        investments = cursor.fetchall()
    
    # Segmentación según la página tables.html:
    dca = investments[:3]
    # Se renombra "Renta Fija & Variable" a "Renta Fija"
    renta_fija = investments[3:6]
    # Se crea la nueva tabla "Renta Variable" (inicialmente vacía o con activos si los hubiese)
    renta_variable = []  
    cryptomonedas = investments[6:8]
    acciones = []  # Se mantiene vacía
    epsv = investments[8:9]
    
    total_dca = sum(inv[6] for inv in dca)
    total_renta_fija = sum(inv[6] for inv in renta_fija)
    total_renta_variable = sum(inv[6] for inv in renta_variable)
    total_crypto = sum(inv[6] for inv in cryptomonedas)
    total_acciones = sum(inv[6] for inv in acciones)
    total_epsv = sum(inv[6] for inv in epsv)
    overall_total = total_dca + total_renta_fija + total_renta_variable + total_crypto + total_acciones + total_epsv

    # Calcular porcentajes
    perc_dca = (total_dca / overall_total) * 100 if overall_total > 0 else 0
    perc_renta_fija = (total_renta_fija / overall_total) * 100 if overall_total > 0 else 0
    perc_renta_variable = (total_renta_variable / overall_total) * 100 if overall_total > 0 else 0
    perc_crypto = (total_crypto / overall_total) * 100 if overall_total > 0 else 0
    perc_acciones = (total_acciones / overall_total) * 100 if overall_total > 0 else 0
    perc_epsv = (total_epsv / overall_total) * 100 if overall_total > 0 else 0

    pie_labels = ["DCA", "Renta Fija", "Renta Variable", "Cryptomonedas", "Acciones", "EPSV"]
    pie_values = [perc_dca, perc_renta_fija, perc_renta_variable, perc_crypto, perc_acciones, perc_epsv]

    # Usamos una paleta premium personalizada:
    custom_colors = ["#FF6B6B", "#FFD93D", "#F9C74F", "#6BCB77", "#4D96FF", "#BC6FF1"]

    # Gráfica de pastel
    fig_pie = go.Figure(data=[go.Pie(
        labels=pie_labels,
        values=pie_values,
        marker=dict(colors=custom_colors),
        textinfo='label+percent',
        insidetextorientation='radial',
        textfont=dict(color="#00FF00")
    )])
    fig_pie.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=40, r=40, t=20, b=20)
    )
    
    # Gráfica de barras (usando los mismos segmentos)
    fig_bar = go.Figure()
    for label, percentage, color in zip(pie_labels, pie_values, custom_colors):
        fig_bar.add_trace(go.Bar(
            x=[label],
            y=[percentage],
            text=f"{percentage:.1f}%",
            textposition='outside',
            textfont=dict(color="#00FF00"),
            marker=dict(color=color, line=dict(width=2, color="white"))
        ))
    fig_bar.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showticklabels=False),
        yaxis=dict(ticksuffix="%", tickfont=dict(color="#00FF00")),
        margin=dict(l=40, r=40, t=20, b=20)
    )
    
    graph_pie_json = json.dumps(fig_pie, cls=plotly.utils.PlotlyJSONEncoder)
    graph_bar_json = json.dumps(fig_bar, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Preparar los datos para la tabla: cada tupla (color, etiqueta, total, porcentaje)
    data_list = list(zip(custom_colors, pie_labels,
                           [total_dca, total_renta_fija, total_renta_variable, total_crypto, total_acciones, total_epsv],
                           [perc_dca, perc_renta_fija, perc_renta_variable, perc_crypto, perc_acciones, perc_epsv]))
    
    return render_template('pie_chart.html', graph_bar_json=graph_bar_json, graph_pie_json=graph_pie_json, data=data_list, overall_total=overall_total)

if __name__ == '__main__':
    app.run(debug=True)
    