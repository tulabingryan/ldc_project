import sqlite3 as lite
import numpy as np
import pandas as pd


def read_db(db_name='./ldc_all.db', start=None, end=None, duration=60):
        # read database
        if db_name=='./ldc_agg.db':
            db_reader = lite.connect('./ldc_agg.db', isolation_level=None)
        else:
            db_reader = lite.connect('./ldc_all.db', isolation_level=None)

        db_reader.execute('pragma journal_mode=wal;')


        try:
            cur = db_reader.cursor()
            if start==None or end==None:
                with db_reader:
                    # Get the last timestamp recorded
                    cur.execute('SELECT unixtime FROM data ORDER BY unixtime DESC LIMIT 1') 
                    end = np.array(cur.fetchall()).flatten()[0]
                    start = end - duration
                    
            else:
                pass
    
            # get the last set of records for a specified duration
            with db_reader:
                sql_cmd = "SELECT unixtime, parameter, value FROM data WHERE unixtime BETWEEN " + str(start) + " AND " + str(end) + " ORDER BY unixtime ASC"
                cur.execute(sql_cmd) 
                data = np.array(cur.fetchall())
                df_data = pd.DataFrame(data, columns=['unixtime', 'parameter', 'value'])
                
            return df_data

        except Exception as e:
            print("Error in get_data:", e)
            return pd.DataFrame([])



