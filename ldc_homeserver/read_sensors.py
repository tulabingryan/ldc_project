import serial
import serial.tools.list_ports
import time, datetime
import pandas as pd
import numpy as np
import sqlite3 as lite

def get_ports(report=False):
    ports = serial.tools.list_ports.comports()
    dict_ports = {}
    for port, desc, hwid in sorted(ports):
        try:
            hardware_id = hwid.split(':')[1]
            dict_ports[hardware_id] = port

        except Exception as e:
            # print("Error get_ports:", e)
            pass
    if report:
        print(dict_ports)
    return dict_ports


def connect_serial(port, baudrate=115200):
    ser = serial.Serial(
        port=port,
        baudrate=baudrate,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=0.5
    )
    if ser.isOpen():
        print("Port {} is open.".format(port))
    return ser

def write_db(df_data, db_name):
    # write a dataframe to the database
    try:
        db_writer = lite.connect(db_name, isolation_level=None)
        db_writer.execute('pragma journal_mode=wal;')
        df_data.to_sql('data', db_writer, schema=None, if_exists='append', index=False, chunksize=None, dtype=None)
        #db_writer.execute('CREATE INDEX unixtime IF NOT EXISTS ON data (unixtime);')
        return
    except Exception as e:
        print("Error write_db:", e)

def check_for_duplicates(db_name, report=False):
    ''' This function checks the records of an sql database for duplicates'''
    try:
        con = lite.connect(db_name)
        with con:
            cur = con.cursor()        
            cur.execute('SELECT * FROM data GROUP BY * HAVING COUNT(*)> 1')
            data = np.array(cur.fetchall())
        if report:
            print('Database record with duplicates:' + str(len(data)))
        return len(data)
    except Exception as e:
        print("Error check_for_duplicates:{}".format(e))

def delete_duplicates(db_name):
    """ This function saves an array of data to an SQL database"""
    # print('Deleting duplicates...')
    try:        
        con = lite.connect(db_name)
        with con:
            cur = con.cursor()
            cur.execute('DELETE FROM data WHERE ROWID NOT IN (SELECT min(ROWID) FROM data GROUP BY *)')
            data = cur.fetchall()

    except Exception as e:
        print("Error delete_duplicates:{}".format(e))


def clean_database(db_name):
    ''' This function cleans up the database from duplicated data record'''
    try:
        n_duplicates = check_for_duplicates(db_name=db_name)
        while n_duplicates > 0 :
            delete_duplicates(db_name)
            n_duplicates = check_for_duplicates(db_name=db_name)
    except Exception as e:
        print("Error clean_database:{}".format(e))

def get_data(ser, report=False, save=False):
    past_dt = None
    dict_hist = {}
    df_location = pd.read_csv('sensors_location.csv').set_index('node_id')
    while True:
        try:
            now = datetime.datetime.now()
            dt = now.strftime('%Y-%m-%d %H:%M')
            
            b = ser.read(18)
            
            if b:
                if((b[0] & 0xFF) == 0xAA):
                    dict_data = dict(
                        date_time = dt,
                        dest_group_id = b[7] & 0xFF,
                        dest_node_id = b[8] & 0xFF,
                        source_group_id = b[9] & 0xFF,
                        source_node_id = b[10] & 0xFF,
                        temperature = (b[12] & 0xFF) + (b[13] & 0xFF) / 100,
                        humidity = (b[14] & 0xFF) + (b[15] & 0xFF) / 100,
                        light = (((b[16] & 0xFF) << 8) + (b[17] & 0xFF)) * 16
                        )
                    dict_hist.update({dict_data['source_node_id']:{
                        'date_time':dict_data['date_time'],
                        'unixtime':now.strftime('%s'),
                        'location':df_location.loc[dict_data['source_node_id'],'location'],
                        'temperature':dict_data['temperature'],
                        'humidity':dict_data['humidity'],
                        'light':dict_data['light'],

                        }})
                    df_hist = pd.DataFrame.from_dict(dict_hist,orient='index')
                    df_hist['source_node_id'] = df_hist.index
                    
                    print(df_hist)
                    
                    if save:
                        df_data = pd.DataFrame.from_dict(dict_data,orient='index').T
                        write_db(df_data=df_data, db_name='sensors.db')
                        ### save including the location
                        df_data2 = df_data
                        df_data2['location'] = df_location.loc[dict_data['source_node_id'],'location']
                        write_db(df_data=df_data2, db_name='sensors2.db')
                        ### save to database in melted format
                        df_data2['unixtime'] = now.strftime('%s')
                        df_agg = pd.melt(df_data2[['source_node_id', 'unixtime', 'location', 
                            'temperature', 'humidity', 'light']].astype(str), id_vars=["unixtime"], 
                            var_name="parameter", value_name="value")
                        write_db(df_data=df_agg, db_name='measurements.db')
                        ### save as csv file to be sent by email
                        #df_hist.to_csv('/home/pi/ldc_project/history/S1_{}.csv'.format(now.strftime('%Y_%m_%d')), index=False)
                        ### save csv file melted format
                        filename = '/home/pi/ldc_project/history/M1_{}.csv'.format(now.strftime('%Y_%m_%d'))
                        with open(filename, 'a') as f:
                            df_agg.to_csv(f, mode='a', header=f.tell()==0, index=False)

                    if report: 
                        print(dict_data)

                else:
                    pass
            else:
                time.sleep(1)
        except Exception as e:
            print("Error get_data", e)
        except KeyboardInterrupt:
            break




def main():
    dict_ports = get_ports(report=False)
    ser = connect_serial(port=dict_ports['PID=0483'])
    get_data(ser, report=True, save=True)

if __name__ == '__main__':
    main()
