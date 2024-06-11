from flask import Flask, render_template, redirect, url_for, request
import datetime
import psycopg2

app = Flask(__name__)

# Database connection configuration
DB_HOST = "localhost"
DB_NAME = "bincom_test"
DB_USER = "olalekan"
DB_PASSWORD = "bincom2425"


# Function to connect to the database
def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return conn


# HOME PAGE
@app.route('/', methods=['GET'])
def home():
    date = datetime.datetime.now().year
    return render_template('index.html', date=date)


# Redirect routes
@app.route('/page1')
def page1():
    polling_unit_id = request.args.get('polling_unit_id')
    if polling_unit_id:
        return redirect(url_for('show_polling_unit_result', polling_unit_id=polling_unit_id))
    else:
        return redirect(url_for('show_polling_unit_result', polling_unit_id=0))


@app.route('/page2')
def page2():
    return redirect(url_for('show_lga_result'))


@app.route('/page3')
def page3():
    return redirect(url_for('add_polling_unit'))


# QUESTION 1
@app.route('/polling_unit/<int:polling_unit_id>', methods=['GET'])
def show_polling_unit_result(polling_unit_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Query to fetch the polling unit result
    query = """
        SELECT
            p.polling_unit_id,
            p.polling_unit_name,
            w.ward_name,
            lg.lga_name,
            s.state_name,
            r.party_abbreviation,
            r.party_score
        FROM
            announced_pu_results r
            JOIN polling_unit p ON r.polling_unit_uniqueid = p.uniqueid
            JOIN ward w ON p.ward_id = w.uniqueid
            JOIN lga lg ON p.lga_id = lg.lga_id
            JOIN state s ON p.state_id = s.state_id
        WHERE
            p.polling_unit_id = %s
            AND s.state_id = 25  # Filter for Delta State (state_id: 25)
        ORDER BY
            r.party_score DESC;
    """
    cur.execute(query, (polling_unit_id,))
    result = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('polling_unit_result.html', result=result)


# QUESTION 2
@app.route('/lga_result', methods=['GET', 'POST'])
def show_lga_result():
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch list of LGAs
    cur.execute("SELECT lga_id, lga_name FROM lga WHERE state_id = 25 ORDER BY lga_name")
    lgas = cur.fetchall()

    if request.method == 'POST':
        lga_id = request.form['lga_id']

        # Query to fetch the summed result for the selected LGA
        query = """
            SELECT
                r.party_abbreviation,
                SUM(r.party_score) AS total_score
            FROM
                announced_pu_results r
                JOIN polling_unit p ON r.polling_unit_uniqueid = p.uniqueid
                JOIN lga lg ON p.lga_id = lg.lga_id
            WHERE
                lg.lga_id = %s
            GROUP BY
                r.party_abbreviation
            ORDER BY
                total_score DESC;
        """
        cur.execute(query, (lga_id,))
        result = cur.fetchall()
    else:
        result = None

    cur.close()
    conn.close()

    return render_template('lga_result.html', lgas=lgas, result=result)


# QUESTION 3
@app.route('/add_polling_unit', methods=['GET', 'POST'])
def add_polling_unit():
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        polling_unit_name = request.form['polling_unit_name']
        ward_id = request.form['ward_id']
        lga_id = request.form['lga_id']
        state_id = 25  # Delta State
        parties = request.form.getlist('party')
        scores = request.form.getlist('score')

        # Insert the new polling unit
        insert_query = """
            INSERT INTO polling_unit (polling_unit_name, ward_id, lga_id, state_id)
            VALUES (%s, %s, %s, %s)
            RETURNING uniqueid;
        """
        cur.execute(insert_query, (polling_unit_name, ward_id, lga_id, state_id))
        new_uniqueid = cur.fetchone()[0]

        # Insert the results for each party
        for party, score in zip(parties, scores):
            insert_result_query = """
                INSERT INTO announced_pu_results (polling_unit_uniqueid, party_abbreviation, party_score)
                VALUES (%s, %s, %s);
            """
            cur.execute(insert_result_query, (new_uniqueid, party, score))

        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for('add_polling_unit', success=True))

    # Fetch list of wards and LGAs
    cur.execute("SELECT uniqueid, ward_name FROM ward WHERE state_id = 25 ORDER BY ward_name")
    wards = cur.fetchall()
    cur.execute("SELECT lga_id, lga_name FROM lga WHERE state_id = 25 ORDER BY lga_name")
    lgas = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('add_polling_unit.html', wards=wards, lgas=lgas)


if __name__ == '__main__':
    app.run(debug=True)
